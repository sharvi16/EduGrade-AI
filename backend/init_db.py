from database import SessionLocal, engine, Base
from models import User, School, UserRole
import bcrypt
from datetime import datetime

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # 1. ENSURE Super Admin exists and password is reset to admin123
        admin_email = "admin@edugrade.ai"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                email=admin_email,
                password_hash=bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                name="Super Admin",
                role=UserRole.SUPER_ADMIN
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"Admin account {admin_email} created.")
        else:
            admin.password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.commit()
            print(f"Admin password for {admin_email} has been FORCE RESET.")

        # 2. Add sample data if the DB is fresh (no schools yet)
        if not db.query(School).first():
            # Add a sample school
            school = School(name="Greenwood High")
            db.add(school)
            db.commit()
            db.refresh(school)
            
            # Add a principal for that school
            principal = User(
                email="principal@greenwood.com",
                password_hash=bcrypt.hashpw("prin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                name="Principal Verma",
                role=UserRole.PRINCIPAL,
                school_id=school.id
            )
            db.add(principal)
            
            # Add a teacher representing current demo
            teacher = User(
                email="teacher@school.com",
                password_hash=bcrypt.hashpw("teach123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
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
                password_hash=bcrypt.hashpw("study123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                name="Rahul Mehta",
                role=UserRole.STUDENT,
                school_id=school.id,
                teacher_id=teacher.id
            )
            db.add(student)
            
            db.commit()
            print("Database seeded with sample data.")
        else:
            print("Database already has data. Skipping sample seeding.")
            
    except Exception as e:
        print(f"Error during init_db: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
