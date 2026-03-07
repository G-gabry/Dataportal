from app.core.database import SessionLocal
from app.models.item import Item
from app.models.enums import ItemType
import json

def migrate_items():
    db = SessionLocal()
    try:
        items = db.query(Item).all()
        print(f"Checking {len(items)} items for migration...")
        count = 0
        for item in items:
            data = item.data or {}
            changed = False
            
            # Common renames
            mappings = {
                "title": ["name", "scholarship_name", "program_name", "conference_name"],
                "host_country": ["country"],
                "description": ["summary"],
                "source_url": ["url"],
                "application_link": ["link"]
            }
            
            for old_key, new_keys in mappings.items():
                if old_key in data:
                    val = data.pop(old_key)
                    for nk in new_keys:
                        if nk not in data or not data[nk]:
                            data[nk] = val
                    changed = True
            
            if changed:
                item.data = data
                count += 1
        
        db.commit()
        print(f"Successfully migrated {count} items.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_items()
