"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./clauseflow.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _add_column_if_missing(engine, table_name: str, column_name: str, column_type: str, default: str = ""):
    """Add a column to an existing table if it doesn't exist (SQLite migration helper)."""
    from sqlalchemy import text, inspect
    inspector = inspect(engine)
    existing = [col["name"] for col in inspector.get_columns(table_name)]
    if column_name not in existing:
        default_clause = f" DEFAULT {default}" if default else ""
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}{default_clause}"))
        print(f"  Migration: added {table_name}.{column_name}")


def init_db():
    """Initialize database tables and run migrations for new columns."""
    Base.metadata.create_all(bind=engine)

    # Migrate existing databases: add new columns if missing
    from sqlalchemy import inspect
    inspector = inspect(engine)
    if "clauses" in inspector.get_table_names():
        _add_column_if_missing(engine, "clauses", "erp_snapshot_text", "TEXT")
        _add_column_if_missing(engine, "clauses", "source_reference", "VARCHAR(1000)")
        # is_external_reference may exist as VARCHAR(10) from old schema — handle both
        existing = [col["name"] for col in inspector.get_columns("clauses")]
        if "is_external_reference" not in existing:
            _add_column_if_missing(engine, "clauses", "is_external_reference", "BOOLEAN", "0")
