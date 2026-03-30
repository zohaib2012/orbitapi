# create_admin.py

import sys
sys.path.append('.')

from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password

db = SessionLocal()

ADMIN_EMAIL = "admin@rajacloud.com"
ADMIN_PASSWORD = "RajaCloud@Admin2024"
BUSINESS_NAME = "Raja Cloud"

try:

    existing = db.query(User).filter(User.email == ADMIN_EMAIL).first()

    if existing:
        print(f"✅ User already exists: {ADMIN_EMAIL}")

    else:
        admin = User(
            business_name=BUSINESS_NAME,
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            phone="0000000000",
            is_active=True,
            is_verified=True,
            plan="enterprise",
            whatsapp_connected=False,
            whatsapp_phone_id=None,
            whatsapp_token=None
        )

        db.add(admin)
        db.commit()

        print("✅ Admin account successfully create ho gaya!")

    print("\n──────── ADMIN LOGIN DETAILS ────────")
    print(f"Email:    {ADMIN_EMAIL}")
    print(f"Password: {ADMIN_PASSWORD}")
    print("Admin Panel:")
    print("http://127.0.0.1:5500/whatschat-frontend/admin.html")

except Exception as e:
    print("❌ Error a gaya:")
    print(e)

finally:
    db.close()