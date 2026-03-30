"""
Migration script — existing tables mein naye columns add karo.
Run: python migrate_columns.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import engine
from sqlalchemy import text, inspect

def add_column_if_missing(conn, table, column, col_type, default=None):
    inspector = inspect(conn) # Use the same connection!
    existing = [c["name"] for c in inspector.get_columns(table)]
    if column not in existing:
        default_clause = f" DEFAULT {default}" if default is not None else ""
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}"))
        print(f"  ✅ Added {table}.{column}")
    else:
        print(f"  ⏩ {table}.{column} already exists")

def main():
    print("🔄 Running column migrations...\n")
    with engine.begin() as conn: # Use begin() to auto-commit and hold lock safely
        # ── InboxMessage table ──
        print("📋 inbox_messages:")
        add_column_if_missing(conn, "inbox_messages", "is_starred", "BOOLEAN", "false")
        add_column_if_missing(conn, "inbox_messages", "quoted_message_id", "INTEGER", "NULL")
        add_column_if_missing(conn, "inbox_messages", "whatsapp_status", "VARCHAR(20)", "'sent'")

        # ── BusinessSettings table ──
        print("\n📋 business_settings:")
        add_column_if_missing(conn, "business_settings", "welcome_media_url", "VARCHAR(500)", "NULL")
        add_column_if_missing(conn, "business_settings", "welcome_media_type", "VARCHAR(20)", "NULL")
        add_column_if_missing(conn, "business_settings", "welcome_enabled", "BOOLEAN", "true")

    # ── New tables (InteractiveMenu) — create_all handles these ──
    from app.core.database import Base
    from app.models.user import InteractiveMenu  # noqa — import so create_all knows
    Base.metadata.create_all(bind=engine)
    print("\n📋 New tables (interactive_menus): ✅ created if missing")

    print("\n🎉 Migration complete!")

if __name__ == "__main__":
    main()
