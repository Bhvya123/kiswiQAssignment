from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Replace these with your MySQL credentials
USER = "root"
PASSWORD = "Meticulous%4013"
DATABASE = "gb"
DATABASE_URL = f"mysql://{USER}:{PASSWORD}@localhost/{DATABASE}"
# DATABASE_URL = os.getenv("DATABASE_URL", "mysql://user:password@localhost/yourdatabase")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
