# ClauseFlow: Contract Clause Parsing & Tracking Tool

## Product Specification Document
**Version:** 0.1 (Alpha)
**Date:** January 20, 2025
**Status:** Draft for Claude Code Implementation

---

## Executive Summary

ClauseFlow is a tool designed for aerospace manufacturing contracts teams to systematically work through complex purchase orders and contracts, breaking them into discrete clauses and tracking review progress. The core problem it solves: contracts administrators currently must hold all state in their heads while parsing 40-50+ page documents with 100+ clauses, trying to remember what they've reviewed, what applies where, and what needs action.

---

## Problem Statement

### The User
Contracts administrators at aerospace manufacturing companies (specifically wire harness manufacturers serving as tier 2/3 suppliers to primes like Boeing, Lockheed, Raytheon).

### The Pain
When a purchase order or contract arrives from a prime contractor:

1. The document is long (often 30-60 pages) and dense
2. It contains dozens to hundreds of discrete clauses with obligations
3. Each clause may apply to different scopes:
   - The entire PO
   - Specific line items only
   - Needs to "flow down" to the company's own suppliers
   - Administrative/boilerplate (no action needed)
4. The contracts administrator must:
   - Read through the entire document
   - Identify each clause that creates an obligation
   - Categorize where each clause applies
   - Enter relevant clauses into the ERP system
   - Track which clauses they've already processed
5. **Currently, all of this state is held in the user's head**—there's no tool that helps them track progress through a complex document

### The Aerospace-Specific Wrinkle: Flow-Down
In federal contracting (FAR/DFARS), prime contractors are legally required to "flow down" certain clauses to their subcontractors. When our user's company receives a PO, they need to:
- Identify which clauses they must comply with
- Identify which clauses they must pass on to *their* suppliers
- This creates a cascade of compliance requirements through the supply chain

---

## Solution Overview

ClauseFlow provides:

1. **Intelligent Document Chunking**: Upload a PDF contract/PO → LLM breaks it into discrete clauses
2. **Systematic Review Workflow**: Work through clauses one at a time with clear progress tracking
3. **AI-Assisted Categorization**: For each clause, AI suggests what it applies to; user confirms or modifies
4. **ERP Clause Matching**: Check if a clause exactly matches something already in the company's ERP clause library
5. **State Persistence**: Never lose track of where you are—progress is saved
6. **Structured Export**: When done, export a structured breakdown for ERP entry or reporting

### What ClauseFlow Does NOT Do (Alpha Scope)
- Does not write directly to the ERP (export only)
- Does not do fuzzy/semantic matching (exact match only for ERP lookup)
- Does not detect conflicts between clauses
- Does not do historical pattern matching across past POs
- Does not modify the original document

---

## User Flow

### Step 1: Upload Document
```
User uploads PDF of contract/PO
    ↓
System extracts text from PDF
    ↓
System sends text to LLM for intelligent chunking
    ↓
User sees: "I found 147 clauses in this document. Ready to begin review."
```

### Step 2: Review Clauses (Core Loop)
```
For each clause (user works through sequentially or can jump around):
    ↓
User sees:
  - The clause text
  - AI's suggested scope (what does this apply to?)
  - ERP match status (exact match found or not)
  - Space for notes
    ↓
User can:
  - Accept or modify the suggested scope
  - Add notes
  - Mark as "reviewed" or "flag for later"
    ↓
Progress bar updates
    ↓
Move to next clause
```

### Step 3: Export
```
When review is complete (or at any point):
    ↓
User exports structured data:
  - JSON for programmatic use
  - CSV for spreadsheet review
  - (Future: formatted report)
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
  pageCount: number;
  status: 'processing' | 'ready' | 'in_review' | 'completed';
}
```

### Clause
```typescript
interface Clause {
  id: string;
  documentId: string;
  
  // From LLM extraction
  clauseNumber: string | null;        // e.g., "7.2.1" if present
  clauseTitle: string | null;         // e.g., "Source Inspection" if present
  text: string;                       // The actual clause content
  pageNumbers: number[];              // Which pages this clause spans
  chunkType: 'clause' | 'administrative' | 'boilerplate' | 'signature' | 'header';
  
  // User-editable fields
  scope: 'entire_po' | 'line_items' | 'flow_down' | 'no_action' | null;
  lineItems: string[] | null;         // If scope is 'line_items', which ones
  notes: string | null;
  
  // Status tracking
  reviewStatus: 'unreviewed' | 'reviewed' | 'flagged';
  reviewedAt: timestamp | null;
  
  // ERP matching
  erpMatchId: string | null;          // ID of matched clause in ERP, if exact match found
  erpMatchText: string | null;        // The matched clause text for display
}
```

### ERP Clause (from external database)
```typescript
interface ErpClause {
  id: string;
  clauseCode: string;                 // e.g., "QA-SOURCE-001"
  text: string;
  normalizedText: string;             // For matching (lowercase, whitespace-normalized)
}
```

### Review Session
```typescript
interface ReviewSession {
  id: string;
  documentId: string;
  startedAt: timestamp;
  lastActivityAt: timestamp;
  currentClauseIndex: number;
  
  // Computed
  totalClauses: number;
  reviewedCount: number;
  flaggedCount: number;
}
```

---

## UI Specification

### Screen 1: Upload / Document List

```
┌─────────────────────────────────────────────────────────────────────┐
│  ClauseFlow                                            [User Menu]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │     [Cloud Upload Icon]                                       │  │
│  │                                                               │  │
│  │     Drop a PDF here or click to upload                        │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│  Recent Documents                                                   │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Boeing_PO_4521A.pdf                                          │  │
│  │  Uploaded: Jan 18, 2025 | 147 clauses | 67% reviewed          │  │
│  │  [Continue Review]                                            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Lockheed_Contract_2024-1892.pdf                              │  │
│  │  Uploaded: Jan 15, 2025 | 203 clauses | Completed ✓           │  │
│  │  [View] [Export]                                              │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Screen 2: Processing State

```
┌─────────────────────────────────────────────────────────────────────┐
│  ClauseFlow                                            [User Menu]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                                                                     │
│                                                                     │
│                    Processing Boeing_PO_4521A.pdf                   │
│                                                                     │
│                    [Spinner Animation]                              │
│                                                                     │
│                    Extracting text from PDF...                      │
│                    ████████████░░░░░░░░░░░░░░  45%                  │
│                                                                     │
│                    [or]                                             │
│                                                                     │
│                    Identifying clauses...                           │
│                    Found 89 clauses so far...                       │
│                                                                     │
│                                                                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Screen 3: Clause Review (Main Interface)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  ClauseFlow    Boeing_PO_4521A.pdf                    [Export ▼] [User Menu]   │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─ Clause Navigator ──────────────────────────────────────────────────────┐   │
│  │                                                                         │   │
│  │  [Unreviewed ▼]  [Search clauses...]                    [← Prev] [Next →]│   │
│  │                                                                         │   │
│  │  Clause 23 of 147                                                       │   │
│  │                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  ┌─ Clause Content ────────────────────────────────────────────────────────┐   │
│  │                                                                         │   │
│  │  Section 7.2 - Source Inspection                              Page 23   │   │
│  │  ───────────────────────────────────────────────────────────────────    │   │
│  │                                                                         │   │
│  │  Supplier shall provide source inspection access to Boeing quality      │   │
│  │  representatives with 48 hours notice. Inspection may occur at any      │   │
│  │  stage of manufacturing. Supplier shall maintain records of all         │   │
│  │  inspection activities and make them available upon request.            │   │
│  │                                                                         │   │
│  │  Reference: AS9102 First Article Inspection Requirements                │   │
│  │                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  ┌─ Classification ────────────────────────────────────────────────────────┐   │
│  │                                                                         │   │
│  │  What does this clause apply to?                                        │   │
│  │                                                                         │   │
│  │    ○ Entire PO                                                          │   │
│  │    ● Specific line items    [Line items: 3, 7, 12                    ]  │   │
│  │    ○ Flow-down to suppliers                                             │   │
│  │    ○ No action needed (administrative/boilerplate)                      │   │
│  │                                                                         │   │
│  │  [AI suggested: Specific line items - flight-critical assemblies]       │   │
│  │                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  ┌─ ERP Match ─────────────────────────────────────────────────────────────┐   │
│  │                                                                         │   │
│  │  ✓ Exact match found in ERP                                             │   │
│  │                                                                         │   │
│  │  Clause Code: QA-SOURCE-001                                             │   │
│  │  "Source inspection access with 48 hours notice..."                     │   │
│  │                                                                         │   │
│  │  [or]                                                                   │   │
│  │                                                                         │   │
│  │  ⚠ No exact match found in ERP clause library                           │   │
│  │                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  ┌─ Notes ─────────────────────────────────────────────────────────────────┐   │
│  │                                                                         │   │
│  │  [Add notes about this clause...]                                       │   │
│  │                                                                         │   │
│  │  Confirmed with Boeing program manager (Jane Smith) that this           │   │
│  │  does not apply to prototype runs, only production units.               │   │
│  │                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  ┌─ Actions ───────────────────────────────────────────────────────────────┐   │
│  │                                                                         │   │
│  │  [✓ Mark as Reviewed]    [⚑ Flag for Later]    [Skip for Now →]         │   │
│  │                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
├────────────────────────────────────────────────────────────────────────────────┤
│  Progress: ████████░░░░░░░░░░░░░░░░░░░░░  23/147 reviewed                     │
│  Unreviewed: 124  |  Reviewed: 22  |  Flagged: 1                              │
└────────────────────────────────────────────────────────────────────────────────┘
```

### Screen 4: Clause List View (Alternative Navigation)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  ClauseFlow    Boeing_PO_4521A.pdf                    [Export ▼] [User Menu]   │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  View: [Card View] [● List View]       Filter: [All ▼]   Search: [______]     │
│                                                                                │
│  ┌──────┬─────────────────────────────────────────┬──────────┬──────────────┐  │
│  │ #    │ Clause                                  │ Scope    │ Status       │  │
│  ├──────┼─────────────────────────────────────────┼──────────┼──────────────┤  │
│  │ 1    │ 1.1 - Definitions                       │ No action│ ✓ Reviewed   │  │
│  │ 2    │ 1.2 - Order of Precedence               │ Entire PO│ ✓ Reviewed   │  │
│  │ 3    │ 2.1 - Pricing                           │ Entire PO│ ✓ Reviewed   │  │
│  │ ...  │ ...                                     │ ...      │ ...          │  │
│  │ 23   │ 7.2 - Source Inspection                 │ Line item│ ○ Unreviewed │  │
│  │ 24   │ 7.3 - Material Certifications           │ Flow-down│ ⚑ Flagged    │  │
│  │ ...  │ ...                                     │ ...      │ ...          │  │
│  └──────┴─────────────────────────────────────────┴──────────┴──────────────┘  │
│                                                                                │
│  Showing 147 clauses                                      Page 1 of 8 [< >]    │
│                                                                                │
├────────────────────────────────────────────────────────────────────────────────┤
│  Progress: ████████░░░░░░░░░░░░░░░░░░░░░  23/147 reviewed                     │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Architecture

### Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   React App     │────▶│   FastAPI       │────▶│   Claude API    │
│   (Frontend)    │     │   (Backend)     │     │   (LLM)         │
│                 │     │                 │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
           ┌─────────────────┐     ┌─────────────────┐
           │                 │     │                 │
           │   SQLite        │     │   ERP Database  │
           │   (Local State) │     │   (Read-only)   │
           │                 │     │                 │
           └─────────────────┘     └─────────────────┘
```

### Frontend (React)

**Dependencies:**
- React 18+
- react-pdf or @react-pdf-viewer/core (for PDF display, if we include it)
- Tailwind CSS (for styling)
- React Router (for navigation)
- Zustand or React Query (for state management)

**Key Components:**
- `DocumentUpload` - drag/drop PDF upload
- `ProcessingStatus` - shows extraction progress
- `ClauseReview` - main review interface
- `ClauseList` - list/table view of all clauses
- `ClauseCard` - individual clause display with controls
- `ProgressBar` - review progress visualization
- `ExportModal` - export options

### Backend (Python/FastAPI)

**Dependencies:**
- fastapi
- uvicorn
- pdfplumber or pypdf (PDF text extraction)
- anthropic (Claude API client)
- sqlalchemy (database ORM)
- sqlite (database)

**Endpoints:**

```
POST /api/documents/upload
  - Accepts PDF file
  - Extracts text
  - Initiates LLM chunking
  - Returns document ID

GET /api/documents/{id}
  - Returns document metadata and processing status

GET /api/documents/{id}/clauses
  - Returns all clauses for a document

GET /api/clauses/{id}
  - Returns single clause with all details

PATCH /api/clauses/{id}
  - Updates clause (scope, notes, review status)

GET /api/erp/match?text={clause_text}
  - Checks for exact match in ERP clause library
  - Returns matched clause or null

GET /api/documents/{id}/export?format={json|csv}
  - Returns structured export of all clauses
```

### LLM Integration (Claude API)

**Chunking Prompt:**

```
You are analyzing a contract/purchase order document. Your job is to break it into discrete chunks.

For each chunk, identify:
1. chunk_type: One of:
   - "clause" - A discrete contractual obligation or requirement
   - "administrative" - Administrative content (addresses, contacts, dates)
   - "boilerplate" - Standard legal language that doesn't create specific obligations
   - "signature" - Signature blocks
   - "header" - Section headers, table of contents

2. clause_number: If the chunk has a number (e.g., "7.2.1"), extract it. Otherwise null.

3. clause_title: If there's a title/heading for this clause, extract it. Otherwise null.

4. text: The full text of the chunk.

5. page_numbers: Which page(s) this chunk appears on.

Return as JSON array.

Important:
- Keep clauses as discrete units - don't merge multiple numbered clauses
- Preserve the exact text - do not summarize or modify
- When in doubt about chunk_type, use "clause"

Document text:
---
{document_text}
---
```

**Scope Suggestion Prompt (per clause):**

```
You are analyzing a contract clause from an aerospace manufacturing purchase order.

Clause text:
---
{clause_text}
---

What does this clause most likely apply to?

Options:
- "entire_po" - Applies to the entire purchase order
- "line_items" - Applies to specific line items only
- "flow_down" - Needs to be flowed down to suppliers
- "no_action" - Administrative/boilerplate, no action needed

Consider:
- Clauses about quality, inspection, certifications often apply to specific line items
- Clauses about cybersecurity, ethics, compliance often apply to entire PO
- Clauses that reference "subcontractor" or "supplier" often need flow-down
- Definitions, order of precedence, signatures are usually no_action

Return JSON:
{
  "suggested_scope": "entire_po" | "line_items" | "flow_down" | "no_action",
  "confidence": "high" | "medium" | "low",
  "reasoning": "Brief explanation"
}
```

### ERP Integration

**Assumption:** The customer has exposed their ERP clause library as a queryable database or API.

**For alpha:** We'll create a simple adapter that can be swapped out:

```python
class ErpClauseAdapter:
    """
    Abstract interface for ERP clause lookup.
    Implement concrete versions for specific ERPs.
    """
    
    def find_exact_match(self, clause_text: str) -> ErpClause | None:
        """
        Returns matching ERP clause if exact match found, else None.
        
        Matching logic:
        1. Normalize both texts (lowercase, strip whitespace, remove punctuation)
        2. Compare normalized strings
        3. Return match if identical
        """
        pass
    
    def list_all_clauses(self) -> list[ErpClause]:
        """Returns all clauses in ERP for pre-loading/caching."""
        pass
```

**For testing:** Create a mock adapter with sample clauses.

---

## File Structure

```
clauseflow/
├── README.md
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── requirements.txt
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Configuration/settings
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── documents.py           # Document upload/retrieval endpoints
│   │   ├── clauses.py             # Clause CRUD endpoints
│   │   └── export.py              # Export endpoints
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py       # PDF to text extraction
│   │   ├── llm_chunker.py         # Claude API integration for chunking
│   │   ├── clause_analyzer.py     # Scope suggestion logic
│   │   └── erp_adapter.py         # ERP integration interface
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── document.py            # Document SQLAlchemy model
│   │   ├── clause.py              # Clause SQLAlchemy model
│   │   └── schemas.py             # Pydantic schemas for API
│   │
│   └── database/
│       ├── __init__.py
│       ├── connection.py          # Database connection setup
│       └── migrations/            # Alembic migrations (if needed)
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   │
│   ├── src/
│   │   ├── main.jsx               # App entry point
│   │   ├── App.jsx                # Main app component with routing
│   │   │
│   │   ├── components/
│   │   │   ├── DocumentUpload.jsx
│   │   │   ├── ProcessingStatus.jsx
│   │   │   ├── ClauseReview.jsx
│   │   │   ├── ClauseCard.jsx
│   │   │   ├── ClauseList.jsx
│   │   │   ├── ProgressBar.jsx
│   │   │   ├── ExportModal.jsx
│   │   │   └── Navigation.jsx
│   │   │
│   │   ├── pages/
│   │   │   ├── HomePage.jsx       # Upload + document list
│   │   │   ├── ReviewPage.jsx     # Main clause review
│   │   │   └── ExportPage.jsx     # Export options
│   │   │
│   │   ├── hooks/
│   │   │   ├── useDocument.js     # Document data fetching
│   │   │   ├── useClauses.js      # Clause data fetching
│   │   │   └── useReviewState.js  # Local review state
│   │   │
│   │   ├── api/
│   │   │   └── client.js          # API client functions
│   │   │
│   │   └── styles/
│   │       └── globals.css        # Tailwind imports + custom styles
│   │
│   └── public/
│       └── index.html
│
└── sample_data/
    ├── sample_po.pdf              # Test document
    └── sample_erp_clauses.json    # Mock ERP clause library
```

---

## Development Phases

### Phase 1: Core Pipeline (Week 1)
- [ ] PDF upload and text extraction
- [ ] LLM chunking integration
- [ ] Basic database models
- [ ] Simple API endpoints for documents and clauses

### Phase 2: Review Interface (Week 2)
- [ ] Clause list view
- [ ] Individual clause review card
- [ ] Scope selection controls
- [ ] Review status tracking
- [ ] Progress bar

### Phase 3: ERP Integration (Week 3)
- [ ] ERP adapter interface
- [ ] Exact match lookup
- [ ] Display match status in UI

### Phase 4: Polish & Export (Week 4)
- [ ] Export to JSON/CSV
- [ ] Session persistence
- [ ] Error handling
- [ ] Basic styling/UX improvements

---

## Open Questions for Customer

1. **Scope Categories**: I've assumed four categories (Entire PO, Line Items, Flow-down, No Action). What categories do they actually use? Are there others?

2. **ERP Integration Details**: 
   - What ERP system are they using?
   - What does the exposed clause database look like (schema)?
   - Is it a direct SQL connection, REST API, or something else?

3. **Line Item References**: When a clause applies to specific line items, how do they identify them? By number? By part number? By description?

4. **Export Format**: What format would be most useful for getting data into their ERP?
   - CSV they can copy-paste?
   - JSON for programmatic import?
   - Formatted report?

5. **Multi-user**: Will multiple people work on the same document? Do we need collaboration features?

6. **Document Types**: Are they only dealing with PDFs? Or also Word docs, scanned images, etc.?

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM misidentifies clause boundaries | Clauses merged or split incorrectly | Allow manual adjustment; tune prompts with real examples |
| PDF text extraction fails (scanned docs) | No text to analyze | Add OCR fallback (tesseract); warn user about quality |
| ERP match rate is low | Feature feels useless | Start with exact match, gather data on near-misses for future fuzzy matching |
| Documents too long for context window | Chunking fails | Process in sections; use Claude's 200K context window |
| User abandons mid-review | Lost work | Auto-save after each clause review |

---

## Success Metrics (Alpha)

- User can upload a real PO and see it chunked into clauses
- Clauses are correctly identified >80% of the time
- User can work through all clauses and mark them reviewed
- Progress is saved and can be resumed
- Export produces usable structured data

---

## Appendix: Sample Clause Types

**Typical aerospace PO clause categories:**

- Quality requirements (AS9100, first article inspection, source inspection)
- Cybersecurity (DFARS 252.204-7012, CMMC)
- Export control (ITAR, EAR)
- Material certifications (certs, COCs, test reports)
- Delivery requirements (packaging, shipping, marking)
- Pricing/payment terms
- Change management
- Intellectual property
- Termination provisions
- Flow-down requirements (FAR/DFARS clauses that must go to subcontractors)
- Warranty
- Insurance/liability

---

## Contact & Resources

- xSkel (customer context): Wire harness manufacturing, AI quality tools
- Existing ERP integration: [Details TBD with customer]
- Sample documents: [To be provided by customer]

---

*End of Specification Document*
