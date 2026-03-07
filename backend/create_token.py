import sys
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import create_access_token
from datetime import timedelta

db = SessionLocal()
admin = db.query(User).first()
if admin:
    token = create_access_token({"sub": str(admin.id)}, timedelta(days=3650))
    print(f"TOKEN={token}")
else:
    print("NO_USERS")
