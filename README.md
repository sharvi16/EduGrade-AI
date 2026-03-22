# EduGrade-AI

Integrated grading and proctoring platform for automated exam evaluation and monitoring, now featuring a full-scale hierarchical institution management system.

## Hierarchical Management
- **Super Admin Hub**: Manage global school infrastructure and deploy Principals.
- **Principal Dashboard**: Oversee faculty (Teachers) and school-wide academic data.
- **Teacher Portal**: Manage student enrollments, exam creation, and automated grading.
- **Student Dashboard**: Secure environment for taking exams with real-time AI proctoring.

## Features
- **Automated Grading**: OCR-based assignment and exam processing using Groq-powered AI.
- **AI Proctoring**: Real-time face detection, eye tracking, and behavior monitoring.
- **Hierarchical Isolation**: Strict data isolation ensuring Teachers only see their classes and students only see their exams.
- **Premium UI/UX**: World-class, elevated design featuring glassmorphism, vibrant gradients, and professional typography.

## Project Structure
- `/frontend`: React-based multi-role interface (Vite, TypeScript, Tailwind CSS, Lucide Icons).
- `/backend`: Python-based API and AI processing engine (FastAPI, Groq SDK, SQLAlchemy, SQLite).

## Getting Started

### Backend Setup
1. Navigate to the backend directory: `cd backend`
2. Create and activate a virtual environment: `python -m venv venv`
3. Install dependencies: `pip install -r requirements.txt`
4. Configure your `.env` file (ensure `JWT_SECRET_KEY` and `GROQ_API_KEY` are set).
5. Initialize the database: `python init_db.py`
6. Start the server: `python api.py`

### Frontend Setup
1. Navigate to the frontend directory: `cd frontend`
2. Install dependencies: `npm install`
3. Start the development server: `npm run dev`

## Tech Stack
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Shadcn UI, Lucide React.
- **Backend**: FastAPI, SQLAlchemy (ORM), Bcrypt (Security), JWT (Authentication).
- **AI/ML**: Groq SDK (Llama 3), OpenCV (Proctoring), EasyOCR.
- **Database**: SQLite (Production-ready with relational migrations).
