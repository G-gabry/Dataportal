import os
from sqlalchemy import text
from app.core.database import SessionLocal, engine, Base

# Import all models so they are registered with Base
from app.models.user import User
from app.models.source import Source
from app.models.url import DiscoveredURL
from app.models.item import Item
from app.models.scrape_job import ScrapeJob
from app.models.ai_log import AILog

def init_db():
    print("Creating all missing database tables...")
    # This will safely create the new scrape_jobs table and any Enum types
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")

if __name__ == "__main__":
    init_db()
