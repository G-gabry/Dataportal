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
    
    # Run migrations for existing sources table
    print("Applying schema migrations...")
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE sources ADD COLUMN sitemap_url VARCHAR(500)"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE sources ADD COLUMN dfs_depth INTEGER DEFAULT 1"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE sources ADD COLUMN max_urls_per_run INTEGER"))
        except Exception:
            pass

    print("Database tables initialized successfully.")

if __name__ == "__main__":
    init_db()
