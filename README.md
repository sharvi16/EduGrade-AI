# EduGrade-AI

Integrated grading and proctoring platform for automated exam evaluation and monitoring.

## Features
- **Automated Grading**: OCR-based assignment and medical form processing.
- **AI Proctoring**: Real-time face detection, eye tracking, and behavior monitoring.
- **Teacher Portal**: Comprehensive dashboard for managing exams and viewing results.
- **Student Dashboard**: Interface for taking exams and viewing grades.

## Project Structure
- `/frontend`: React-based student and teacher interface (Vite, TypeScript, Tailwind CSS).
- `/backend`: Python-based API and AI processing engine (FastAPI, Groq SDK, OpenCV).

## Getting Started

### Backend Setup
1. Navigate to the backend directory: `cd backend`
2. Create and activate a virtual environment: `python -m venv venv`
3. Install dependencies: `pip install -r requirements.txt`
4. Configure your `.env` file based on `.env.example`.
5. Start the server: `python api.py`

### Frontend Setup
1. Navigate to the frontend directory: `cd frontend`
2. Install dependencies: `npm install`
3. Start the development server: `npm run dev`

## Tech Stack
- **Frontend**: React, TypeScript, Vite, Lucide React, Tailwind CSS.
- **Backend**: FastAPI, OpenCV, Groq Meta-Llama, EasyOCR.
- **Database**: SQL-based (configured in backend).
