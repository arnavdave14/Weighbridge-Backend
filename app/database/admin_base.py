from sqlalchemy.orm import DeclarativeBase

class AdminBase(DeclarativeBase):
    """
    Dedicated base for Administration / SaaS features.
    These tables will only be created on the remote PostgreSQL instance,
    ensuring they NEVER pollute the local offline-first SQLite database.
    """
    pass
