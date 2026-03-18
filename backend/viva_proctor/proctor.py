"""
viva_proctor/proctor.py
=======================
CV-based proctoring engine for the Viva examination phase.

Key design decisions:
  - We rely on multiple Haar cascades (frontal default, alt2, and profile).
  - Also checks multiple rotations (0, 90, 270) because some webcams send
    rotated frames which inherently break Haar cascades.
  - "no_face" is a highly reliable proxy for "looking away" in this context.
  - A violation fires after _FRAMES_AWAY_LIMIT consecutive frames.
"""

import base64
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Tuple

import cv2
import numpy as np

# ── Haar cascades ────────────────────────────────────────────────
_face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
_face_alt_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml")
_profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")

# ── Detection parameters ─────────────────────────────────────────
# Relaxed minNeighbors so we have better recall on webcam feeds
_FACE_SCALE        = 1.1
_FACE_NEIGHBORS    = 1        # Extremely lenient, will find faces almost anywhere to prevent false warnings
_FACE_MIN_SIZE     = (30, 30)

# ── Violation thresholds ─────────────────────────────────────────
# Both "no_eyes" and "no_face" increment away counter.
_FRAMES_AWAY_LIMIT  = 2    # consecutive frames before 1 warning
_MAX_WARNINGS       = 3    # terminate after 3 violations
_VIOLATION_COOLDOWN = 5.0  # seconds between consecutive violations


# ────────────────────────────────────────────────────────────────
def check_frame_base64(b64_image: str) -> Tuple[bool, str]:
    """
    Decode a base64 JPEG/PNG frame and run face detection.
    Returns (is_looking_at_screen, reason_code)
    """
    try:
        if "," in b64_image:
            b64_image = b64_image.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_image)
        arr   = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception as e:
        return True, "decode_error"

    if frame is None:
        return True, "invalid_frame"

    # Convert to grayscale directly
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Test original, 90 deg clockwise, and 90 deg counter-clockwise
    # This solves the issue where specific webcams/phones send rotated frames.
    images_to_check = [
        gray,
        cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE),
        cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE)
    ]

    for img in images_to_check:
        # 1. Try Frontal Face Default
        faces = _face_cascade.detectMultiScale(img, scaleFactor=1.1, minNeighbors=3, minSize=(40, 40))
        if len(faces) > 0:
            return True, "looking"
            
        # 2. Try Frontal Face Alt2
        faces_alt = _face_alt_cascade.detectMultiScale(img, scaleFactor=1.1, minNeighbors=3, minSize=(40, 40))
        if len(faces_alt) > 0:
            return True, "looking"
            
        # 3. Try Profile Face
        faces_prof = _profile_cascade.detectMultiScale(img, scaleFactor=1.1, minNeighbors=3, minSize=(40, 40))
        if len(faces_prof) > 0:
            return True, "looking"

    # No face found at all in any rotation → turned head away or left camera
    return False, "no_face"


# ── Per-session state ────────────────────────────────────────────
@dataclass
class ProctorSession:
    session_id:       str
    exam_id:          str
    student_id:       str
    warnings:         int   = 0
    terminated:       bool  = False
    frames_away:      int   = 0   # consecutive "no_eyes" frames
    last_violation_t: float = field(default_factory=time.time)
    created_at:       float = field(default_factory=time.time)

    def process_frame(self, is_looking: bool, reason: str) -> dict:
        """
        Feed one detection result into the session state machine.
        Returns a status dict to send back to the frontend.

        "no_face" counts toward violations.
        Only decode errors are ignored.
        """
        if self.terminated:
            return self._status("terminated", "Viva already terminated.")

        # If uncertain (decode errors) → treat as looking
        if reason in ("decode_error", "invalid_frame"):
            self.frames_away = max(0, self.frames_away - 1)  # gentle recovery
            return self._status("ok", "Looking at screen.")

        if is_looking:
            # Confirmed looking — recover faster than we accumulate
            self.frames_away = max(0, self.frames_away - 2)
            return self._status("ok", "Looking at screen.")

        # Confirmed NOT looking (no_face)
        self.frames_away += 1

        if self.frames_away < _FRAMES_AWAY_LIMIT:
            # Warn in UI but no violation yet
            remaining = _FRAMES_AWAY_LIMIT - self.frames_away
            return self._status(
                "away",
                f"Please keep your eyes on the screen! ({remaining} frames until warning)",
            )

        # Enough sustained look-away — check cooldown before registering
        now = time.time()
        if now - self.last_violation_t < _VIOLATION_COOLDOWN:
            return self._status("away", "Please keep your eyes on the screen!")

        # Register violation
        self.frames_away      = 0
        self.last_violation_t = now
        self.warnings        += 1

        if self.warnings >= _MAX_WARNINGS:
            self.terminated = True
            return self._status(
                "terminated",
                "Viva terminated: you looked away from the screen 3 times. Score set to 0.",
            )

        return self._status(
            "warning",
            f"Warning {self.warnings}/{_MAX_WARNINGS}: Please keep your eyes on the screen!",
        )

    def _status(self, action: str, message: str) -> dict:
        return {
            "action":      action,
            "warnings":    self.warnings,
            "terminated":  self.terminated,
            "message":     message,
            "frames_away": self.frames_away,
        }


# ── In-memory session store ──────────────────────────────────────
session_store: Dict[str, ProctorSession] = {}


def create_session(exam_id: str, student_id: str) -> ProctorSession:
    sid  = f"viva_{exam_id[:8]}_{uuid.uuid4().hex[:8]}"
    sess = ProctorSession(session_id=sid, exam_id=exam_id, student_id=student_id)
    session_store[sid] = sess
    return sess


def get_session(session_id: str) -> "ProctorSession | None":
    return session_store.get(session_id)


def delete_session(session_id: str) -> bool:
    if session_id in session_store:
        del session_store[session_id]
        return True
    return False
