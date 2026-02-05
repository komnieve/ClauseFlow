"""
V3 Migration: Customer-Scoped Reference Library

Creates new tables:
  - customers
  - reference_documents
  - reference_requirements
  - clause_reference_links

Modifies:
  - documents: adds customer_id column
"""

import sqlite3
import sys

DB_PATH = "clauseflow.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("V3 Migration: Customer-Scoped Reference Library")
    print("=" * 50)

    # 1. customers table
    print("Creating 'customers' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. reference_documents table
    print("Creating 'reference_documents' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reference_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            filename VARCHAR(255) NOT NULL,
            original_text TEXT NOT NULL,
            total_lines INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(20) DEFAULT 'uploading',
            error_message TEXT,
            doc_identifier VARCHAR(255),
            version VARCHAR(100),
            title VARCHAR(500),
            parent_id INTEGER REFERENCES reference_documents(id),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. reference_requirements table
    print("Creating 'reference_requirements' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reference_requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_document_id INTEGER NOT NULL REFERENCES reference_documents(id),
            requirement_number VARCHAR(100),
            title VARCHAR(500),
            text TEXT,
            start_line INTEGER,
            end_line INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 4. clause_reference_links table
    print("Creating 'clause_reference_links' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clause_reference_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clause_id INTEGER NOT NULL REFERENCES clauses(id),
            reference_requirement_id INTEGER REFERENCES reference_requirements(id),
            reference_document_id INTEGER REFERENCES reference_documents(id),
            detected_spec_identifier VARCHAR(255),
            detected_version VARCHAR(100),
            match_status VARCHAR(20) DEFAULT 'unresolved',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 5. Add customer_id to documents table (if not already present)
    cursor.execute("PRAGMA table_info(documents)")
    columns = [row[1] for row in cursor.fetchall()]
    if "customer_id" not in columns:
        print("Adding 'customer_id' column to 'documents' table...")
        cursor.execute("ALTER TABLE documents ADD COLUMN customer_id INTEGER REFERENCES customers(id)")
    else:
        print("'customer_id' column already exists in 'documents' table.")

    conn.commit()
    conn.close()

    print()
    print("V3 migration complete!")
    print("Existing documents will have customer_id=NULL (backward compatible).")


if __name__ == "__main__":
    migrate()
