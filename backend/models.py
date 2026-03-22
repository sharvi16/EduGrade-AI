from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime, JSON
from sqlalchemy.orm import relationship
from database import Base
import enum
from datetime import datetime

class UserRole(enum.Enum):
    SUPER_ADMIN = "super_admin"
    PRINCIPAL = "principal"
    TEACHER = "teacher"
    STUDENT = "student"

class School(Base):
    __tablename__ = "schools"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    users = relationship("User", back_populates="school")
    exams = relationship("Exam", back_populates="school")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    name = Column(String)
    role = Column(Enum(UserRole))
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    school = relationship("School", back_populates="users")

class Exam(Base):
    __tablename__ = "exams"
    exam_id = Column(String, primary_key=True, index=True)
    title = Column(String)
    subject = Column(String)
    total_marks = Column(Integer)
    questions = Column(String)
    answer_key = Column(String)
    rubrics = Column(String)
    school_id = Column(Integer, ForeignKey("schools.id"))
    teacher_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    school = relationship("School", back_populates="exams")
    submissions = relationship("Submission", back_populates="exam")

class Submission(Base):
    __tablename__ = "submissions"
    submission_id = Column(String, primary_key=True, index=True)
    exam_id = Column(String, ForeignKey("exams.exam_id"))
    student_name = Column(String)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    written = Column(JSON)
    viva = Column(JSON)
    
    exam = relationship("Exam", back_populates="submissions")
