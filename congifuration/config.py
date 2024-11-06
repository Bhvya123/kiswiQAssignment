from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Load MySQL credentials from environment variables
USER = os.getenv("DATABASE_USER", "root")
PASSWORD = os.getenv("DATABASE_PASSWORD", "Meticulous%4013")
HOST = os.getenv("DATABASE_HOST", "localhost")
PORT = os.getenv("DATABASE_PORT", "3306")
DATABASE = os.getenv("DATABASE_NAME", "gb")

# Update the database URL to use the HOST and PORT from Docker environment variables
DATABASE_URL = f"mysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
