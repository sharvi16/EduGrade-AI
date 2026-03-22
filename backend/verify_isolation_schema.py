from sqlalchemy import create_engine, MetaData, Table, select
engine = create_engine("sqlite:///c:/panvel hackathon/backend/edugrade_v4.db")
with engine.connect() as conn:
    metadata = MetaData()
    metadata.reflect(bind=engine)
    exams = metadata.tables.get('exams')
    users = metadata.tables.get('users')
    if exams is not None:
        print(f"Exams columns: {[c.name for c in exams.columns]}")
    if users is not None:
        print(f"Users columns: {[c.name for c in users.columns]}")
