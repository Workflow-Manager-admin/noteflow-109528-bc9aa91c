"""Initialize the Noteflow database (development/setup)."""

import os
from sqlalchemy import create_engine
from models import Base

DB_URL = os.environ.get("NOTEFLOW_DATABASE_URL", "sqlite:///test.db")

# PUBLIC_INTERFACE
def init_db():
    """Create all required tables for the notes app."""
    engine = create_engine(DB_URL)
    Base.metadata.create_all(bind=engine)
    print("Database initialized. Tables created.")

if __name__ == "__main__":
    init_db()
