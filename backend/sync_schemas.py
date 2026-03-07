import sys
import os
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.item_schema import ItemSchema
from app.models.enums import ItemType

def sync_schemas():
    db = SessionLocal()
    try:
        # Define schemas for all 4 types
        schemas = [
            {
                "item_type": ItemType.SCHOLARSHIP,
                "fields": {
                    "name": {"type": "string", "description": "Display name for list view"},
                    "scholarship_name": {"type": "string", "description": "Official full name"},
                    "summary": {"type": "text", "description": "Brief description"},
                    "url": {"type": "string", "description": "Main opportunity URL"},
                    "country": {"type": "string", "description": "Host country"},
                    "host_institution": {"type": "string"},
                    "host_organization": {"type": "string"},
                    "eligible_countries": {"type": "array"},
                    "eligible_degrees": {"type": "array"},
                    "eligible_fields": {"type": "array"},
                    "funding_type": {"type": "string", "options": ["fully_funded", "partial", "unknown"]},
                    "amount": {"type": "string"},
                    "benefits": {"type": "array"},
                    "application_deadline": {"type": "string"},
                    "start_date": {"type": "string"},
                    "duration": {"type": "string"},
                    "link": {"type": "string", "description": "Direct application link"},
                    "required_documents": {"type": "array"},
                    "additional_info": {"type": "text", "description": "A well-designed, comprehensive paragraph containing ALL remaining important details, text, and context found on the page about this item that was not captured in the other fields."}
                }
            },
            {
                "item_type": ItemType.PROGRAM,
                "fields": {
                    "name": {"type": "string"},
                    "program_name": {"type": "string"},
                    "summary": {"type": "text"},
                    "url": {"type": "string"},
                    "country": {"type": "string"},
                    "host_institution": {"type": "string"},
                    "degree_type": {"type": "string"},
                    "fields_of_study": {"type": "array"},
                    "duration": {"type": "string"},
                    "language_of_instruction": {"type": "string"},
                    "tuition_fee": {"type": "string"},
                    "scholarship_available": {"type": "boolean"},
                    "application_deadline": {"type": "string"},
                    "start_date": {"type": "string"},
                    "link": {"type": "string"},
                    "requirements": {"type": "array"},
                    "additional_info": {"type": "text", "description": "A well-designed, comprehensive paragraph containing ALL remaining important details, text, and context found on the page about this item that was not captured in the other fields."}
                }
            },
            {
                "item_type": ItemType.CONFERENCE,
                "fields": {
                    "name": {"type": "string"},
                    "conference_name": {"type": "string"},
                    "summary": {"type": "text"},
                    "url": {"type": "string"},
                    "country": {"type": "string"},
                    "venue": {"type": "string"},
                    "organizer": {"type": "string"},
                    "event_date": {"type": "string"},
                    "submission_deadline": {"type": "string"},
                    "registration_deadline": {"type": "string"},
                    "topics": {"type": "array"},
                    "attendance_type": {"type": "string", "options": ["in-person", "virtual", "hybrid"]},
                    "registration_fee": {"type": "string"},
                    "travel_grant_available": {"type": "boolean"},
                    "link": {"type": "string"},
                    "additional_info": {"type": "text", "description": "A well-designed, comprehensive paragraph containing ALL remaining important details, text, and context found on the page about this item that was not captured in the other fields."}
                }
            },
            {
                "item_type": ItemType.EXCHANGE,
                "fields": {
                    "name": {"type": "string"},
                    "summary": {"type": "text"},
                    "url": {"type": "string"},
                    "country": {"type": "string"},
                    "host_institution": {"type": "string"},
                    "partner_countries": {"type": "array"},
                    "eligible_nationalities": {"type": "array"},
                    "level_of_study": {"type": "array"},
                    "duration": {"type": "string"},
                    "funding_available": {"type": "boolean"},
                    "stipend_amount": {"type": "string"},
                    "application_deadline": {"type": "string"},
                    "start_date": {"type": "string"},
                    "mobility_type": {"type": "string"},
                    "link": {"type": "string"},
                    "requirements": {"type": "array"},
                    "additional_info": {"type": "text", "description": "A well-designed, comprehensive paragraph containing ALL remaining important details, text, and context found on the page about this item that was not captured in the other fields."}
                }
            }
        ]

        for s_data in schemas:
            item_type = s_data["item_type"]
            fields = s_data["fields"]
            
            # Check if schema exists
            schema = db.query(ItemSchema).filter(ItemSchema.item_type == item_type).first()
            if schema:
                print(f"Updating existing schema for {item_type}...")
                schema.schema_json = {"fields": fields}
                # RESET PROMPTS to None so VM defaults take over
                schema.extraction_prompt = None
                schema.classification_prompt = None
                schema.version += 1
            else:
                print(f"Creating new schema for {item_type}...")
                schema = ItemSchema(
                    item_type=item_type,
                    schema_json={"fields": fields},
                    extraction_prompt=None,
                    classification_prompt=None,
                    is_active=True,
                    version=1
                )
                db.add(schema)
        
        db.commit()
        print("Successfully synced all item schemas.")
    except Exception as e:
        db.rollback()
        print(f"Error syncing schemas: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    # Add parent dir to path so we can import 'app'
    sys.path.append(os.getcwd())
    sync_schemas()
