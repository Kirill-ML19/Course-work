import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv

load_dotenv()
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError('DATABASE_URL environment variable is not set')
engine = create_engine(
    database_url,
    echo = False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)