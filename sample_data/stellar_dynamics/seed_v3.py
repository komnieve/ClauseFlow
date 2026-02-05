#!/usr/bin/env python3
"""
Seed script for Stellar Dynamics Corporation V3 sample data.

Creates a customer, uploads 3 reference spec documents, uploads a PO,
and waits for all processing to complete. Prints a summary of results.

Usage:
    python sample_data/stellar_dynamics/seed_v3.py           # seed
    python sample_data/stellar_dynamics/seed_v3.py --delete   # delete all seeded data
"""

import argparse
import os
import sys
import time

import requests

BASE_URL = os.environ.get("CLAUSEFLOW_API_URL", "http://localhost:9847")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Reference documents to upload: (filename, doc_identifier, version)
REF_DOCS = [
    ("SDC-Q-100_RevC_Source_Inspection.txt", "SDC-Q-100", "Rev C"),
    ("SDC-Q-250_RevA_Wiring_Standards.txt", "SDC-Q-250", "Rev A"),
    ("SDC-M-030_v4.1_Material_Specs.txt", "SDC-M-030", "v4.1"),
]

PO_FILENAME = "sample_po_stellar_dynamics.txt"
CUSTOMER_NAME = "Stellar Dynamics Corporation"

POLL_INTERVAL = 2  # seconds
POLL_TIMEOUT = 120  # seconds


def api_url(path: str) -> str:
    return f"{BASE_URL}{path}"


def create_customer() -> int:
    """Create the Stellar Dynamics customer. Returns customer_id."""
    print(f"\n[1/4] Creating customer: {CUSTOMER_NAME}")
    resp = requests.post(api_url("/api/customers"), json={"name": CUSTOMER_NAME})
    if resp.status_code == 409:
        # Customer already exists — find it
        print("  Customer already exists, looking up...")
        list_resp = requests.get(api_url("/api/customers"))
        list_resp.raise_for_status()
        for c in list_resp.json():
            if c["name"] == CUSTOMER_NAME:
                print(f"  Found existing customer id={c['id']}")
                return c["id"]
        raise RuntimeError("Customer exists (409) but not found in list")
    resp.raise_for_status()
    customer = resp.json()
    print(f"  Created customer id={customer['id']}")
    return customer["id"]


def upload_reference_docs(customer_id: int) -> list[dict]:
    """Upload the 3 reference spec documents. Returns list of ref doc records."""
    print(f"\n[2/4] Uploading {len(REF_DOCS)} reference documents...")
    ref_docs = []
    for filename, doc_id, version in REF_DOCS:
        filepath = os.path.join(SCRIPT_DIR, filename)
        with open(filepath, "rb") as f:
            resp = requests.post(
                api_url(f"/api/customers/{customer_id}/reference-docs/upload"),
                files={"file": (filename, f, "text/plain")},
                data={"doc_identifier": doc_id, "version": version},
            )
        resp.raise_for_status()
        doc = resp.json()
        ref_docs.append(doc)
        print(f"  Uploaded {doc_id} {version} — id={doc['id']}, status={doc['status']}")
    return ref_docs


def poll_reference_docs(customer_id: int, ref_docs: list[dict]) -> list[dict]:
    """Poll until all reference documents reach terminal status."""
    print(f"\n[3/4] Waiting for reference document processing...")
    pending_ids = {d["id"] for d in ref_docs}
    results = {}
    start = time.time()

    while pending_ids and (time.time() - start) < POLL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        for doc_id in list(pending_ids):
            resp = requests.get(api_url(f"/api/reference-docs/{doc_id}"))
            resp.raise_for_status()
            doc = resp.json()
            status = doc["status"]
            if status in ("ready", "error"):
                pending_ids.discard(doc_id)
                results[doc_id] = doc
                req_count = doc.get("requirement_count", len(doc.get("requirements", [])))
                if status == "ready":
                    print(f"  {doc['doc_identifier']} {doc['version']}: READY — {req_count} requirements extracted")
                else:
                    print(f"  {doc['doc_identifier']}: ERROR — {doc.get('error_message', 'unknown')}")
            else:
                elapsed = int(time.time() - start)
                print(f"  {doc.get('doc_identifier', doc_id)}: {status} ({elapsed}s elapsed)")

    if pending_ids:
        print(f"  WARNING: Timed out waiting for ref docs: {pending_ids}")

    return list(results.values())


def upload_po(customer_id: int) -> dict:
    """Upload the sample PO. Returns document record."""
    print(f"\n[4/4] Uploading sample PO: {PO_FILENAME}")
    filepath = os.path.join(SCRIPT_DIR, PO_FILENAME)
    with open(filepath, "rb") as f:
        resp = requests.post(
            api_url("/api/documents/upload"),
            files={"file": (PO_FILENAME, f, "text/plain")},
            data={"customer_id": str(customer_id)},
        )
    resp.raise_for_status()
    doc = resp.json()
    print(f"  Uploaded PO — document_id={doc['document_id']}, status={doc['status']}")
    return doc


def poll_document(document_id: int) -> dict:
    """Poll until the PO document reaches terminal status."""
    print(f"\n  Waiting for PO processing...")
    start = time.time()

    while (time.time() - start) < POLL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        resp = requests.get(api_url(f"/api/documents/{document_id}"))
        resp.raise_for_status()
        doc = resp.json()
        status = doc["status"]
        if status in ("ready", "error"):
            return doc
        elapsed = int(time.time() - start)
        print(f"    Status: {status} ({elapsed}s elapsed)")

    print(f"  WARNING: Timed out waiting for document {document_id}")
    resp = requests.get(api_url(f"/api/documents/{document_id}"))
    resp.raise_for_status()
    return resp.json()


def print_summary(customer_id: int, ref_results: list[dict], po_doc: dict):
    """Print a summary of the seed results."""
    print("\n" + "=" * 60)
    print("  SEED COMPLETE — SUMMARY")
    print("=" * 60)

    print(f"\n  Customer: {CUSTOMER_NAME} (id={customer_id})")

    # Reference docs
    total_reqs = 0
    for doc in ref_results:
        req_count = doc.get("requirement_count", len(doc.get("requirements", [])))
        total_reqs += req_count
    print(f"  Reference Documents: {len(ref_results)} processed")
    print(f"  Total Requirements Extracted: {total_reqs}")

    # PO results
    doc_id = po_doc.get("id") or po_doc.get("document_id")
    clauses = po_doc.get("clauses", [])
    print(f"\n  PO Document: id={doc_id}, status={po_doc['status']}")
    print(f"  Clauses Extracted: {len(clauses)}")

    # Count sections
    sections = po_doc.get("sections", [])
    if sections:
        print(f"  Sections Identified: {len(sections)}")

    # Count line items
    line_items = po_doc.get("line_items", [])
    if line_items:
        print(f"  Line Items: {len(line_items)}")

    # Reference matching results
    try:
        refs_resp = requests.get(api_url(f"/api/documents/{doc_id}/references"))
        refs_resp.raise_for_status()
        all_refs = refs_resp.json()

        matched = [r for r in all_refs if r.get("match_status") == "matched"]
        unresolved = [r for r in all_refs if r.get("match_status") == "unresolved"]
        partial = [r for r in all_refs if r.get("match_status") == "partial"]

        print(f"\n  Reference Matching Results:")
        print(f"    Matched:    {len(matched)}")
        print(f"    Unresolved: {len(unresolved)}")
        if partial:
            print(f"    Partial:    {len(partial)}")

        if matched:
            print(f"\n  Matched References:")
            for r in matched:
                spec = r.get("detected_spec_identifier", "?")
                ver = r.get("detected_version", "")
                print(f"    - {spec} {ver}")

        if unresolved:
            print(f"\n  Unresolved References (not in library):")
            for r in unresolved:
                spec = r.get("detected_spec_identifier", "?")
                ver = r.get("detected_version", "")
                print(f"    - {spec} {ver}")

    except Exception as e:
        print(f"\n  Could not fetch reference links: {e}")

    print("\n" + "=" * 60)
    print("  Open the frontend to verify:")
    print("    - Customer badge shows 'Stellar Dynamics Corporation'")
    print("    - Reference Library shows 3 specs with requirements")
    print("    - ClauseCard shows green/red spec badges")
    print("    - DocumentOverview shows reference summary")
    print("=" * 60 + "\n")


def find_customer() -> int | None:
    """Find the Stellar Dynamics customer. Returns customer_id or None."""
    resp = requests.get(api_url("/api/customers"))
    resp.raise_for_status()
    for c in resp.json():
        if c["name"] == CUSTOMER_NAME:
            return c["id"]
    return None


def delete_seed_data():
    """Delete all Stellar Dynamics seeded data (PO documents, ref docs, customer)."""
    print("=" * 60)
    print("  Deleting Stellar Dynamics Corporation seed data")
    print("=" * 60)

    customer_id = find_customer()
    if not customer_id:
        print("\n  Customer not found — nothing to delete.")
        return

    print(f"\n  Found customer id={customer_id}")

    # Delete PO documents linked to this customer
    resp = requests.get(api_url("/api/documents"), params={"customer_id": customer_id})
    resp.raise_for_status()
    docs = resp.json()
    for doc in docs:
        doc_id = doc["id"]
        del_resp = requests.delete(api_url(f"/api/documents/{doc_id}"))
        if del_resp.ok:
            print(f"  Deleted document: {doc['filename']} (id={doc_id})")
        else:
            print(f"  Failed to delete document id={doc_id}: {del_resp.status_code}")

    # Delete customer (cascades to ref docs)
    resp = requests.delete(api_url(f"/api/customers/{customer_id}"))
    if resp.ok:
        print(f"  Deleted customer: {CUSTOMER_NAME} (id={customer_id})")
    else:
        print(f"  Failed to delete customer: {resp.status_code}")

    print("\n  Done. All Stellar Dynamics seed data removed.")


def seed():
    """Run the full seed pipeline."""
    print("=" * 60)
    print("  Stellar Dynamics Corporation — V3 Sample Data Seed")
    print("=" * 60)
    print(f"  API: {BASE_URL}")

    # Step 1: Create customer
    customer_id = create_customer()

    # Step 2: Upload reference documents
    ref_docs = upload_reference_docs(customer_id)

    # Step 3: Wait for reference docs to process
    ref_results = poll_reference_docs(customer_id, ref_docs)

    # Check for errors
    errors = [d for d in ref_results if d.get("status") == "error"]
    if errors:
        print(f"\n  WARNING: {len(errors)} reference doc(s) failed processing")
        for d in errors:
            print(f"    {d.get('doc_identifier', d['id'])}: {d.get('error_message')}")

    # Step 4: Upload PO
    po_upload = upload_po(customer_id)
    doc_id = po_upload.get("document_id")

    # Step 5: Wait for PO to process
    po_doc = poll_document(doc_id)

    if po_doc["status"] == "error":
        print(f"\n  ERROR: PO processing failed — {po_doc.get('error_message')}")
        sys.exit(1)

    # Print summary
    print_summary(customer_id, ref_results, po_doc)


def main():
    parser = argparse.ArgumentParser(description="Seed or delete Stellar Dynamics V3 sample data")
    parser.add_argument("--delete", action="store_true", help="Delete all seeded data instead of creating it")
    args = parser.parse_args()

    # Verify API is reachable
    try:
        resp = requests.get(api_url("/api/documents"), timeout=5)
        resp.raise_for_status()
    except requests.ConnectionError:
        print(f"ERROR: Cannot reach API at {BASE_URL}")
        print("Make sure the backend is running:")
        print("  cd backend && source venv/bin/activate && uvicorn main:app --port 9847")
        sys.exit(1)

    if args.delete:
        delete_seed_data()
    else:
        seed()


if __name__ == "__main__":
    main()
