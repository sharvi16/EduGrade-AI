import requests
import json

BASE_URL = "http://localhost:8000"

print("1. Creating Exam...")
exam_data = {
    "title": "API Test Exam",
    "subject": "Testing",
    "total_marks": 50,
    "rubric_text": "Correctness."
}
exam = requests.post(f"{BASE_URL}/exams", data=exam_data).json()
exam_id = exam["exam_id"]
print(f"Created Exam: {exam_id}")

print("2. Grading Answer (Student 1: John Doe)...")
grade1 = requests.post(f"{BASE_URL}/grade/text", json={
    "exam_id": exam_id,
    "student_name": "John Doe",
    "student_answer": "This is a test answer for the API."
}).json()
print("Graded John Doe:", grade1.get("marks_obtained"))

print("3. Fetching Submissions...")
subs = requests.get(f"{BASE_URL}/exams/{exam_id}/submissions").json()
print(f"Found {len(subs)} submissions.")
print(json.dumps(subs, indent=2))
