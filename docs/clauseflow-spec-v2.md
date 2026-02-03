# ClauseFlow V2 Specification

## Product Specification Document
**Version:** 2.0 (Based on Kyle Interview - Feb 2, 2026)
**Status:** Ready for Development

---

## Executive Summary

ClauseFlow helps aerospace manufacturing contracts teams process purchase orders by automatically extracting clauses, mapping them to line items, and verifying against the ERP clause library. The core value: replace sticky-note tracking with a clear, reliable system that ensures nothing gets missed.

---

## Problem Statement

### The User
Contracts administrators at aerospace wire harness manufacturers (tier 2/3 suppliers to primes like Boeing, Lockheed, Raytheon).

### The Pain
- **Volume**: 15+ POs per week with varying complexity
- **Current State**: Tracking clause-to-line mappings with sticky notes and checkboxes
- **Mental Load**: Must hold all state in head while parsing 30-60 page documents
- **Risk**: Easy to miss clauses (especially external references) or assign to wrong lines
- **Time**: Manual verification is slow and error-prone

### What Gets Missed Most Often
1. **Wrong line assignments** - Clauses assigned to incorrect lines
2. **External document references** - Clauses buried in referenced documents

---

## Core Concepts

### PO Structure
Purchase orders contain two types of clause assignments:

1. **PO-Wide Clauses**: Apply to ALL line items
   - Often grouped in a "Terms & Conditions" section
   - May appear at beginning OR end of document (varies by customer)
   - Master T&C documents can expand into 20+ individual sub-clauses

2. **Line-Specific Clauses**: Apply to specific line items only
   - Explicitly stated in the PO (not interpreted)
   - Format varies: table format or comma-separated lists
   - Listed by clause code under each line item section

### ERP Clause Library
The company maintains a master clause library in their ERP with:
- **Clause ID/Code** (e.g., "QA-SOURCE-001", "FAR 52.xxx")
- **Full clause text**
- **Source document reference** (where the clause originated)
- **Revision number** (when applicable)
- **Date** (when applicable)

### Matching Logic
ERP matching is nuanced - not all clauses have the same metadata:

| Scenario | Match On |
|----------|----------|
| Full metadata | ID + Revision + Date + Text |
| No rev/date (e.g., prime contract) | ID + Text only |
| New clause | No match - needs to be added |

### External References
POs may reference external documents in several ways:
- URL to customer portal (may require authentication)
- Document number only (must be looked up)
- Full text included inline

**V1 Approach**: Flag external references; manual lookup. ~50% of revenue comes from customers requiring authenticated portals.

---

## V1 Scope

### In Scope
1. **Clause Extraction**: Parse PO and identify all discrete clauses
2. **PO-Wide vs Line-Specific Classification**: Categorize each clause
3. **Line-to-Clause Mapping**: Track which clauses apply to which lines
4. **ERP Verification**: Check if clause exists in ERP; flag mismatches
5. **Structured Output**: Clear report for ERP entry

### Out of Scope (Future)
- External URL fetching (flag only)
- Flow-down designation (happens downstream after clauses entered)
- Multi-user collaboration (one person owns each PO)
- Direct ERP write-back (export only)

---

## Required Outputs

### Output 1: PO-Wide Clauses
List of all clauses that apply to the entire PO (all lines):

```
PO-WIDE CLAUSES
===============
1. FAR 52.204-21 - Basic Safeguarding of Covered Contractor Info
   ERP Status: MATCH (Rev 2, 2024-01-15)

2. DFARS 252.225-7001 - Buy American Act
   ERP Status: MATCH (Rev 1, 2023-06-01)

3. Prime Contract FA8615-23-C-0042 Terms
   ERP Status: MATCH (Text verified, no rev/date)

4. Customer T&C Document 13F [EXTERNAL REFERENCE]
   ERP Status: PENDING - External document, manual verification required
   Sub-clauses identified: 23
```

### Output 2: Line-Specific Clauses (Grouped by Clause)
Clauses grouped by code, showing which lines each applies to:

```
LINE-SPECIFIC CLAUSES
=====================
C003 - Source Inspection Required
  Applies to: Lines 1, 3, 4, 5
  ERP Status: MATCH (Rev 3, 2024-08-20)

C007 - First Article Inspection (FAI)
  Applies to: Lines 1, 3
  ERP Status: MATCH (Rev 2, 2024-02-10)

C012 - ITAR Controlled
  Applies to: Lines 2, 6
  ERP Status: MISMATCH - ERP has Rev 1, PO shows Rev 2
  Action: Update ERP or verify with customer

C019 - Special Packaging Requirements
  Applies to: Lines 1, 2, 3, 4, 5, 6
  ERP Status: NOT FOUND - New clause, needs to be added
```

### Output 3: Verification Summary
Quick status for completeness check:

```
VERIFICATION SUMMARY
====================
Total Clauses: 47
  - PO-Wide: 12
  - Line-Specific: 35

ERP Status:
  - Matched: 39
  - Mismatched: 3 (require update or verification)
  - New: 2 (need to be added to ERP)
  - External: 3 (manual verification required)

Line Coverage:
  - All 9 lines have clause assignments verified
```

---

## Data Model

### Document
```typescript
interface Document {
  id: string;
  filename: string;
  uploadedAt: timestamp;
  rawText: string;
  status: 'processing' | 'ready' | 'in_review' | 'completed';

  // PO Metadata
  poNumber: string | null;
  customerName: string | null;
  primeContract: string | null;
  totalLineItems: number;
}
```

### LineItem
```typescript
interface LineItem {
  id: string;
  documentId: string;
  lineNumber: number;           // 1, 2, 3...
  partNumber: string | null;
  description: string | null;
  quantity: string | null;
  qualityLevel: string | null;  // "Flight Critical", "Mission Essential"
}
```

### Clause
```typescript
interface Clause {
  id: string;
  documentId: string;

  // Extraction data
  clauseCode: string | null;      // "C003", "FAR 52.xxx", etc.
  clauseTitle: string | null;
  text: string;
  sourceReference: string | null; // "Document 13F", URL, etc.

  // Classification
  scopeType: 'po_wide' | 'line_specific';
  applicableLines: number[];      // [1,3,5] or [] for po_wide

  // ERP Verification
  erpMatchStatus: 'matched' | 'mismatched' | 'not_found' | 'external_pending';
  erpClauseId: string | null;
  erpRevision: string | null;
  erpDate: string | null;
  mismatchDetails: string | null; // "Rev mismatch: ERP=1, PO=2"

  // External reference handling
  isExternalReference: boolean;
  externalUrl: string | null;

  // Review tracking
  reviewStatus: 'unreviewed' | 'reviewed' | 'flagged';
  notes: string | null;
}
```

### ERPClause (from ERP system)
```typescript
interface ERPClause {
  id: string;
  clauseCode: string;
  text: string;
  revision: string | null;
  effectiveDate: string | null;
  sourceDocument: string | null;
}
```

---

## User Flow

### Step 1: Upload PO
```
User uploads PDF
    ↓
System extracts text
    ↓
System identifies line items
    ↓
System extracts and classifies clauses (PO-wide vs line-specific)
    ↓
System checks each clause against ERP
    ↓
User sees: "Found 47 clauses (12 PO-wide, 35 line-specific across 9 lines)"
```

### Step 2: Review PO-Wide Clauses
```
User sees list of PO-wide clauses
    ↓
For each clause:
  - See clause text and code
  - See ERP match status (matched/mismatched/new/external)
  - Can mark as reviewed or flag for follow-up
  - Can add notes
    ↓
Progress tracked: "8 of 12 PO-wide clauses reviewed"
```

### Step 3: Review Line-Specific Clauses
```
User sees clauses grouped by clause code
    ↓
For each clause:
  - See which lines it applies to
  - Verify line assignments are correct
  - See ERP match status
  - Mark as reviewed
    ↓
Can also view by line: "Line 3: 7 clauses apply"
```

### Step 4: Export
```
User exports structured output
    ↓
Formats: JSON (for programmatic use), CSV (for spreadsheet)
    ↓
Output organized as: PO-wide list + Line-specific grouped by clause
```

---

## UI Requirements

### Primary Views

1. **Document List** (Home)
   - Upload new PO
   - List of POs with status and progress
   - Click to continue review

2. **PO-Wide Review**
   - List of PO-wide clauses
   - ERP status indicators (green=match, yellow=mismatch, red=new, gray=external)
   - Progress bar
   - Mark reviewed / Flag / Add notes

3. **Line-Specific Review**
   - Grouped by clause code (primary view)
   - Each clause shows applicable lines
   - Toggle to "View by Line" (see all clauses for a specific line)
   - ERP status indicators
   - Mark reviewed / Flag / Add notes

4. **Summary/Export**
   - Verification summary (counts by status)
   - Export buttons (JSON, CSV)
   - Items needing attention highlighted

### Keyboard Shortcuts
- **Enter**: Mark current clause as reviewed, advance to next
- **Arrow keys**: Navigate between clauses
- **F**: Flag current clause

### UX Requirements (from Kyle interview)

**1. Attention Dashboard**
On document load, show summary of what needs attention:
- "3 mismatches need resolution"
- "2 new clauses to add to ERP"
- "3 external references to verify"

**2. Visual Diff for Mismatches**
When a clause revision mismatches, show side-by-side comparison:
- ERP text (left) vs PO text (right)
- Differences highlighted
- Very useful for deciding how to resolve

**3. Gated Workflow**
```
Review Phase → Gate → Final Output
```
- User cannot proceed to final output until ALL clauses are addressed
- "Addressed" means: reviewed, flagged with reason, or explicitly skipped
- Prevents incomplete processing

**4. Completion Flow**
```
All clauses addressed
    ↓
Brief confirmation: "All 47 clauses reviewed!"
    ↓
Show final clean output (grouped for ERP entry)
```

**5. Final Output View**
Only shows AFTER all clauses addressed:
- Clean list of PO-wide clauses
- Line-specific clauses grouped by clause code
- Each shows applicable lines
- Designed for direct ERP entry workflow

---

## ERP Integration

### Interface
```python
class ERPAdapter:
    def find_clause(self, clause_code: str) -> ERPClause | None:
        """Find clause by code/ID."""
        pass

    def verify_match(self, po_clause: Clause, erp_clause: ERPClause) -> MatchResult:
        """
        Compare PO clause against ERP clause.
        Returns: matched, mismatched (with details), or partial_match

        Match logic:
        1. If ERP has rev+date: verify all match
        2. If ERP has no rev/date: verify text matches
        """
        pass

    def list_all_clauses(self) -> list[ERPClause]:
        """For pre-loading/caching."""
        pass
```

### V1 Implementation
For V1, ERP adapter will be a mock/JSON file that can be swapped for real integration later.

---

## LLM Prompts

### Clause Extraction Prompt
```
You are analyzing a purchase order document from an aerospace manufacturer.

Your job is to:
1. Identify all discrete clauses in the document
2. Classify each as PO-wide or line-specific
3. Extract the clause code/ID if present
4. For line-specific clauses, identify which line numbers they apply to

Document structure notes:
- PO-wide clauses may be at the beginning OR end of the document
- Line items are numbered (Line 001, Line 002, etc.)
- Line-specific clauses are explicitly tied to line numbers in the document
- External document references should be flagged (URLs, document numbers)

For each clause, return:
{
  "clause_code": "C003" or null,
  "clause_title": "Source Inspection" or null,
  "text": "Full clause text...",
  "scope_type": "po_wide" | "line_specific",
  "applicable_lines": [1, 3, 5] or [],
  "is_external_reference": true | false,
  "external_url": "https://..." or null,
  "source_reference": "Document 13F" or null
}

Important:
- Line assignments are EXPLICIT in the document - do not interpret/guess
- Preserve exact clause text - do not summarize
- Master T&C documents may contain many sub-clauses - extract each separately
- When in doubt, ask for clarification rather than guess

Document text:
---
{document_text}
---
```

---

## Success Metrics

### V1 Success Criteria
- [ ] Can upload a real customer PO and see it parsed into clauses
- [ ] Correctly separates PO-wide from line-specific clauses
- [ ] Line-specific clauses correctly show which lines they apply to
- [ ] Can verify clauses against mock ERP library
- [ ] Output is clear enough to work from for ERP entry
- [ ] Keyboard shortcut (Enter) marks reviewed and advances

### User Success
- Faster PO processing (measurable time reduction)
- Higher confidence nothing was missed
- Clear output replaces sticky-note tracking

---

## Open Items for Future Versions

1. **External Document Fetching**: Automatically retrieve publicly available docs
2. **Authenticated Portal Access**: Integration with customer portals (Boeing, etc.)
3. **Flow-Down Tracking**: After clause entry, track where clauses need to flow
4. **ERP Write-Back**: Direct integration to create/update ERP clauses
5. **Clause Diff/Compare**: Highlight differences when revision mismatches occur
6. **Historical Patterns**: "This customer usually includes these clauses..."

---

## Appendix: Interview Notes

**Source**: Kyle interview, Feb 2, 2026

**Key Quotes**:
- "Instead of having to manually go back through and verify which clauses apply to which lines... often I'm doing little check boxes on a sticky note"
- "The biggest win is speed up the ingestion of POs and accuracy"
- "I need an output where it's easy and simplistic to see this applies from here to here"

**Checklist Items Kyle Uses Today**:
- Customer name
- General ledger account
- Rev numbers
- Delivery date
- RFQ notes section
- FAI or source applies (yes/no)
- DPAS rating (yes/no)
- Line numbering system

---

*End of Specification*
