from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Replace these with your MySQL credentials
USER = "root"
PASSWORD = "Meticulous%4013"
DATABASE = "gb"
DATABASE_URL = f"mysql://{USER}:{PASSWORD}@localhost/{DATABASE}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
