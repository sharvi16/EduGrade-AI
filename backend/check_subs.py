from sqlalchemy import create_engine, MetaData, Table, select
engine = create_engine("sqlite:///c:/panvel hackathon/backend/edugrade_v3.db")
with engine.connect() as conn:
    metadata = MetaData()
    metadata.reflect(bind=engine)
    subs = metadata.tables.get('submissions')
    if subs is not None:
        result = conn.execute(select(subs)).fetchall()
        for row in result:
             print(f"Row: {row}")
    else:
        print("Table 'submissions' not found.")
