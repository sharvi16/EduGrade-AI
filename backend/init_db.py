from database import SessionLocal, engine, Base
from models import User, School, UserRole
from passlib.context import CryptContext
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Check if Super Admin exists, create if not
    admin_email = "admin@edugrade.ai"
    if not db.query(User).filter(User.email == admin_email).first():
        super_admin = User(
            email=admin_email,
            password_hash=pwd_context.hash("admin123"),
            name="Super Admin",
            role=UserRole.SUPER_ADMIN
        )
        db.add(super_admin)
        db.commit()
        print(f"Admin account {admin_email} created successfully.")
    else:
        print(f"Admin account {admin_email} already exists.")
        
        # Add a sample school
        school = School(name="Greenwood High")
        db.add(school)
        db.commit()
        db.refresh(school)
        
        # Add a principal for that school
        principal = User(
            email="principal@greenwood.com",
            password_hash=pwd_context.hash("prin123"),
            name="Principal Verma",
            role=UserRole.PRINCIPAL,
            school_id=school.id
        )
        db.add(principal)
        
        # Add a teacher representing current demo
        teacher = User(
            email="teacher@school.com",
            password_hash=pwd_context.hash("teach123"),
            name="Prof. Sharma",
            role=UserRole.TEACHER,
            school_id=school.id
        )
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
        
        # Add a student representing current demo
        student = User(
            email="student@school.com",
            password_hash=pwd_context.hash("study123"),
            name="Rahul Mehta",
            role=UserRole.STUDENT,
            school_id=school.id,
            teacher_id=teacher.id
        )
        db.add(student)
        
        db.commit()
        print("Database initialized with seed data.")
    else:
        print("Database already initialized.")
    db.close()

if __name__ == "__main__":
    init_db()
