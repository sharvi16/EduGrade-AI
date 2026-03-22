from sqlalchemy import create_engine, MetaData, Table, select
engine = create_engine("sqlite:///c:/panvel hackathon/backend/edugrade_v2.db")
with engine.connect() as conn:
    metadata = MetaData()
    metadata.reflect(bind=engine)
    exams = metadata.tables.get('exams')
    if exams is not None:
        result = conn.execute(select(exams)).fetchall()
        print(f"Exams: {result}")
    else:
        print("Table 'exams' not found.")
