from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import Base
from app.models import *

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

DB_URL = "postgresql://whatchat_user:WhatChat%402024@localhost/whatchat_db"

def run_migrations_offline():
    context.configure(url=DB_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = create_engine(DB_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
