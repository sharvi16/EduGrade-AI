# viva_proctor — CV-based proctoring integrated with the viva exam flow
from .proctor import check_frame_base64, ProctorSession, session_store

__all__ = ["check_frame_base64", "ProctorSession", "session_store"]
