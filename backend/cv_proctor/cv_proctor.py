import cv2
import requests
import time
import uuid

# Configuration
API_URL = "http://127.0.0.1:8001/log-violation"
SESSION_ID = f"session_{uuid.uuid4().hex[:8]}"
STUDENT_ID = "student_demo"

# Haarcascade setup
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# State variables
warnings = 0
is_terminated = False
message = "Proctoring Active - Keep eyes on screen"
message_color = (0, 255, 0) # Green
last_violation_time = time.time()
violation_cooldown = 3.0 # Wait 3 seconds before logging another violation

def log_violation():
    global warnings, is_terminated, message, message_color, last_violation_time
    
    current_time = time.time()
    if current_time - last_violation_time < violation_cooldown:
        return # Skip if we just logged one
        
    last_violation_time = current_time
    
    try:
        response = requests.post(API_URL, json={
            "session_id": SESSION_ID,
            "student_id": STUDENT_ID
        })
        
        data = response.json()
        warnings = data.get("warnings_count", warnings)
        
        if data.get("action") == "warning":
            message = data.get("message", f"WARNING {warnings}/3")
            message_color = (0, 165, 255) # Orange
        elif data.get("action") == "terminate":
            is_terminated = True
            message = "TEST TERMINATED: Maximum warnings exceeded."
            message_color = (0, 0, 255) # Red
            
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to API: {e}")

# Initialize Webcam
cap = cv2.VideoCapture(0)

print(f"Starting Session: {SESSION_ID}")
print("Press 'q' to quit.")

# Frame-based tracking
frames_looking_away = 0
LOOK_AWAY_THRESHOLD = 30 # roughly 1 second at 30fps

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break
        
    if is_terminated:
        # Gray out screen and show termination message
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        cv2.putText(frame, message, (10, int(frame.shape[0] / 2)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, message_color, 2)
        cv2.putText(frame, "Press 'q' to exit", (10, int(frame.shape[0] / 2) + 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.imshow("Smart Proctoring", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        continue

    # Normal processing loop
    # Convert to grayscale for haarcascade
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(100, 100) # Ensure it's detecting a full head, not a random artifact
    )
    
    is_looking_at_screen = False
    
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
        
        # Now check for eyes WITHIN the detected face box
        roi_gray = gray[y:y+h, x:x+w]
        roi_color = frame[y:y+h, x:x+w]
        eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=10, minSize=(20, 20))
        
        for (ex, ey, ew, eh) in eyes:
            cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 2)
            
        # OpenCV Haar Cascades struggle with lighting and angles. 
        # If we detect at least 1 eye looking forward, we assume they are looking at the screen
        if len(eyes) >= 1:
            is_looking_at_screen = True
            
    if not is_looking_at_screen:
        frames_looking_away += 1
        
        # A 1-second threshold (at 30fps) gives the user time to blink or adjust 
        # without instantly triggering a violation
        if frames_looking_away >= 30: 
            log_violation()
            # Reset counter so we don't spam requests every single frame
            frames_looking_away = 0 
    else:
        # Looking forward
        frames_looking_away = max(0, frames_looking_away - 2) # Recover faster than accumulate
        
    # Draw logic
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
        
    # Overlay UI
    cv2.putText(frame, message, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, message_color, 2)
    
    if frames_looking_away > (LOOK_AWAY_THRESHOLD / 2):
       cv2.putText(frame, "Looking Away...", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    cv2.imshow("Smart Proctoring", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
