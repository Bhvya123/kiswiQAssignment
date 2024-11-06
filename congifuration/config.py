from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv() 

# Define the path to the SQL file
SQL_FILE_PATH = os.path.join(os.path.dirname(__file__), 'gb.sql')

# Load MySQL credentials from environment variables
USER = "root"
PASSWORD = "Meticulous%4013"
HOST = "mysql-container"
PORT = "3306"
DATABASE = "gb"

# Update the database URL to use the HOST and PORT from Docker environment variables
DATABASE_URL = f"mysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
