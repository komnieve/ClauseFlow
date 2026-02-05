"""
V2 Migration Script — ALTER TABLE statements for preserving existing data.

For a clean install, just delete clauseflow.db and restart the server.
This script is for anyone who wants to preserve existing V1 data.

Usage:
    cd backend
    python migrate_v2.py
"""

import sqlite3
import sys


def migrate(db_path: str = "clauseflow.db"):
    """Apply V2 schema changes to an existing database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Migrating {db_path} to V2 schema...")

    # --- New tables ---

    print("  Creating 'sections' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id),
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            section_type VARCHAR(30) NOT NULL,
            section_title VARCHAR(500),
            section_number VARCHAR(50),
            line_item_number INTEGER,
            order_index INTEGER NOT NULL,
            text TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    print("  Creating 'line_items' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS line_items (
            id INTEGER PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id),
            section_id INTEGER REFERENCES sections(id),
            line_number INTEGER,
            part_number VARCHAR(255),
            description TEXT,
            quantity VARCHAR(100),
            quality_level VARCHAR(100),
            start_line INTEGER,
            end_line INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- New columns on clauses ---

    # Check which columns already exist
    cursor.execute("PRAGMA table_info(clauses)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    new_clause_columns = [
        ("section_id", "INTEGER REFERENCES sections(id)"),
        ("scope_type", "VARCHAR(20)"),
        ("applicable_lines", "VARCHAR(500)"),
        ("erp_match_status", "VARCHAR(50)"),
        ("erp_clause_id", "VARCHAR(100)"),
        ("erp_revision", "VARCHAR(50)"),
        ("erp_date", "VARCHAR(50)"),
        ("mismatch_details", "TEXT"),
        ("is_external_reference", "VARCHAR(10)"),
        ("external_url", "VARCHAR(1000)"),
    ]

    for col_name, col_type in new_clause_columns:
        if col_name not in existing_columns:
            print(f"  Adding column 'clauses.{col_name}'...")
            cursor.execute(f"ALTER TABLE clauses ADD COLUMN {col_name} {col_type}")
        else:
            print(f"  Column 'clauses.{col_name}' already exists, skipping.")

    conn.commit()
    conn.close()

    print("Migration complete!")
    print("\nNote: Existing documents won't have sections or V2 scope data.")
    print("Re-upload documents to get the full V2 two-pass extraction.")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "clauseflow.db"
    migrate(db_path)
