#!/usr/bin/env python3
"""Test script for clause extraction."""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.preprocessor import add_line_numbers
from services.clause_extractor import (
    extract_clauses_from_document,
    validate_references,
    extract_clause_texts,
)
from models.clause import ChunkType
from config import settings


def main():
    # Load the sample PO
    sample_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "sample_data",
        "sample_po_acme_aerospace.txt"
    )

    print(f"Loading sample PO from: {sample_path}")

    with open(sample_path, "r") as f:
        raw_text = f.read()

    print(f"Document loaded: {len(raw_text)} characters")

    # Step 1: Add line numbers
    print("\n" + "=" * 60)
    print("STEP 1: Adding line numbers")
    print("=" * 60)

    doc = add_line_numbers(raw_text)
    print(f"Total lines: {doc.total_lines}")
    print(f"\nFirst 10 lines (numbered):")
    for line in doc.numbered_text.split('\n')[:10]:
        print(f"  {line}")

    # Step 2: Extract clauses using LLM
    print("\n" + "=" * 60)
    print("STEP 2: Extracting clauses using OpenAI")
    print("=" * 60)

    print(f"Using model: {settings.openai_model}")
    print("Calling OpenAI API (this may take a moment)...")

    try:
        result = extract_clauses_from_document(doc)
        print(f"\nExtracted {len(result.clauses)} clause references")
    except Exception as e:
        print(f"ERROR during extraction: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Step 3: Validate references
    print("\n" + "=" * 60)
    print("STEP 3: Validating references")
    print("=" * 60)

    valid_refs, warnings = validate_references(result.clauses, doc.total_lines)

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings[:10]:  # Show first 10 warnings
            print(f"  - {w}")
        if len(warnings) > 10:
            print(f"  ... and {len(warnings) - 10} more warnings")
    else:
        print("No validation warnings")

    print(f"\nValid references: {len(valid_refs)}")

    # Step 4: Extract actual text
    print("\n" + "=" * 60)
    print("STEP 4: Extracting clause texts")
    print("=" * 60)

    extracted_clauses = extract_clause_texts(doc, valid_refs)

    # Show summary by chunk type
    by_type = {}
    for clause in extracted_clauses:
        ct = clause.chunk_type.value
        if ct not in by_type:
            by_type[ct] = []
        by_type[ct].append(clause)

    print("\nClauses by type:")
    for chunk_type, clauses in sorted(by_type.items()):
        print(f"\n  {chunk_type.upper()} ({len(clauses)}):")
        for c in clauses[:5]:  # Show first 5 of each type
            num = c.clause_number or "(no number)"
            title = c.clause_title or "(no title)"
            lines = f"lines {c.start_line}-{c.end_line}"
            print(f"    - {num}: {title} [{lines}]")
        if len(clauses) > 5:
            print(f"    ... and {len(clauses) - 5} more")

    # Show a sample extracted clause
    print("\n" + "=" * 60)
    print("SAMPLE EXTRACTED CLAUSE")
    print("=" * 60)

    # Find a good sample clause (actual clause type, not too long)
    sample_clauses = [c for c in extracted_clauses if c.chunk_type == ChunkType.CLAUSE]
    if sample_clauses:
        sample = sample_clauses[0]
        print(f"\nClause: {sample.clause_number} - {sample.clause_title}")
        print(f"Lines: {sample.start_line} - {sample.end_line}")
        print(f"Type: {sample.chunk_type.value}")
        print(f"\nText:\n{'-' * 40}")
        # Show first 500 chars
        text_preview = sample.text[:500]
        if len(sample.text) > 500:
            text_preview += "..."
        print(text_preview)

    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Total clauses extracted: {len(extracted_clauses)}")

    # Save output to JSON file
    import json
    output_path = os.path.join(os.path.dirname(__file__), "..", "sample_data", "extraction_output.json")

    output_data = {
        "document": "sample_po_acme_aerospace.txt",
        "total_lines": doc.total_lines,
        "total_clauses": len(extracted_clauses),
        "warnings": warnings,
        "clauses": [
            {
                "start_line": c.start_line,
                "end_line": c.end_line,
                "clause_number": c.clause_number,
                "clause_title": c.clause_title,
                "chunk_type": c.chunk_type.value,
                "text": c.text
            }
            for c in extracted_clauses
        ]
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
