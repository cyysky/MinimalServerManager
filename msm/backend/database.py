import sqlite3
from pathlib import Path
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base

# Database configuration
DB_PATH = Path(__file__).parent.parent / "data" / "app.db"

def init_db(database_url: str = None):
    """Initialize the database with required schema"""
    if database_url is None:
        database_url = f"sqlite:///{DB_PATH}"
    
    os.makedirs(DB_PATH.parent, exist_ok=True)

    try:
        # Create engine
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Test connection
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            print(f"Database initialized successfully at {DB_PATH}")
        finally:
            db.close()
            
        return engine
        
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        raise

def get_database_url():
    """Get database URL from environment or default"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Check for environment variables
    db_type = os.getenv('DB_TYPE', 'sqlite')
    
    if db_type == 'sqlite':
        db_path = os.getenv('DB_PATH', str(DB_PATH))
        return f"sqlite:///{db_path}"
    elif db_type == 'postgresql':
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'msm')
        username = os.getenv('DB_USER', 'postgres')
        password = os.getenv('DB_PASSWORD', '')
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

if __name__ == "__main__":
    init_db()