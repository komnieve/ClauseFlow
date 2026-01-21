# ClauseFlow: Modular Project Plan

## Overview

Breaking the full spec into independent, testable components. Each component can be built, tested, and validated before moving to the next.

---

## Component Breakdown

### Component 1: PDF Text Extraction
**What it does:** Takes a PDF file, extracts clean text with page number tracking.

**Inputs:** PDF file
**Outputs:** Structured text with page boundaries

**Scope:**
- Extract text from PDF using pdfplumber or pypdf
- Handle multi-page documents
- Track which text came from which page
- Handle common edge cases (multi-column, tables, headers/footers)

**NOT in scope:**
- OCR for scanned documents (future)
- Word docs or other formats

**Deliverable:** Python module with `extract_text(pdf_path) -> PagedText` function

**Test:** Feed it a sample contract PDF, verify text is readable and page numbers are correct.

---

### Component 2: LLM Clause Extraction
**What it does:** Takes extracted text, uses Claude to identify and chunk into discrete clauses.

**Inputs:** Raw text with page markers
**Outputs:** List of clause objects with text, type, numbering, page refs

**Scope:**
- Prompt engineering for clause identification
- Parse LLM response into structured data
- Handle documents that exceed context window (chunked processing)
- Classify chunk types: clause, administrative, boilerplate, signature, header

**NOT in scope:**
- Scope suggestions (that's Component 3)
- ERP matching (that's Component 4)

**Deliverable:** Python module with `extract_clauses(text) -> List[Clause]` function

**Test:** Feed it sample contract text, manually verify clause boundaries are sensible.

**Key questions to answer:**
- What prompt produces the best clause boundaries?
- How do we handle documents longer than context window?
- How accurate is the chunking on real documents?

---

### Component 3: Clause Scope Suggestion
**What it does:** For a single clause, suggests what scope it applies to (entire PO, line items, flow-down, no action).

**Inputs:** Single clause text
**Outputs:** Suggested scope + confidence + reasoning

**Scope:**
- Prompt engineering for scope classification
- Return confidence level
- Batch processing option (analyze multiple clauses efficiently)

**NOT in scope:**
- User modification of suggestions (that's frontend)
- Storage of suggestions (that's data layer)

**Deliverable:** Python module with `suggest_scope(clause_text) -> ScopeSuggestion` function

**Test:** Feed it various clause types, verify suggestions are reasonable.

---

### Component 4: ERP Clause Matching
**What it does:** Checks if a clause exactly matches something in the ERP clause library.

**Inputs:** Clause text + ERP clause database
**Outputs:** Match result (matched clause or null)

**Scope:**
- Text normalization (lowercase, strip whitespace, remove punctuation)
- Exact string matching
- Adapter pattern for different ERP backends

**NOT in scope:**
- Fuzzy/semantic matching (future)
- Writing to ERP

**Deliverable:** Python module with `find_match(clause_text, erp_clauses) -> ErpClause | None`

**Test:** Create mock ERP clause library, verify exact matches are found.

---

### Component 5: Data Layer
**What it does:** Stores documents, clauses, and review state.

**Inputs:** Document metadata, clause data, user review actions
**Outputs:** Persisted state that survives browser refresh

**Scope:**
- SQLite database
- Models: Document, Clause, ReviewSession
- CRUD operations
- Session persistence (resume where you left off)

**NOT in scope:**
- Multi-user collaboration
- Cloud sync

**Deliverable:** SQLAlchemy models + repository functions

**Test:** Create document, add clauses, update review state, verify persistence.

---

### Component 6: Backend API
**What it does:** HTTP endpoints that wire together components 1-5.

**Inputs:** HTTP requests
**Outputs:** JSON responses

**Scope:**
- POST /documents/upload - upload PDF, trigger extraction
- GET /documents/{id} - get document status
- GET /documents/{id}/clauses - get all clauses
- PATCH /clauses/{id} - update clause (scope, notes, status)
- GET /documents/{id}/export - export as JSON/CSV

**NOT in scope:**
- Authentication
- Rate limiting

**Deliverable:** FastAPI application

**Test:** Integration tests hitting each endpoint.

---

### Component 7: Frontend - Core Review UI
**What it does:** The main interface for reviewing clauses one at a time.

**Inputs:** Clause data from API
**Outputs:** User actions (scope selection, notes, mark reviewed)

**Scope:**
- Clause display card
- Scope selection radio buttons
- Notes text area
- Review status toggle
- Navigation (prev/next clause)
- Progress bar

**NOT in scope:**
- PDF viewer alongside (adds complexity)
- Filtering/search
- List view

**Deliverable:** React component that works with mock data first, then real API.

**Test:** Can a user work through 10 clauses and mark them all reviewed?

---

### Component 8: Frontend - Upload & Document List
**What it does:** Upload interface and list of documents being processed.

**Inputs:** PDF file from user
**Outputs:** Uploaded document, navigation to review

**Scope:**
- Drag-drop upload
- Processing status display
- Document list with resume capability

**Deliverable:** React pages for home/upload flow.

---

### Component 9: Export
**What it does:** Generate downloadable structured output.

**Inputs:** Completed review data
**Outputs:** JSON file, CSV file

**Scope:**
- JSON export with all clause data
- CSV export for spreadsheet use
- Download trigger

**Deliverable:** Backend endpoint + frontend download button.

---

## Recommended Build Order

```
Phase 1: Core Extraction Pipeline (prove the concept works)
├── Component 1: PDF Text Extraction
├── Component 2: LLM Clause Extraction
└── Validation: Can we reliably break a contract into clauses?

Phase 2: Minimal Backend
├── Component 5: Data Layer (just Document + Clause models)
├── Component 6: Backend API (upload + get clauses endpoints only)
└── Validation: Can we upload a PDF and get clauses back via API?

Phase 3: Review Interface
├── Component 7: Frontend - Core Review UI
└── Validation: Can a user work through clauses and mark them reviewed?

Phase 4: Complete the Loop
├── Component 3: Clause Scope Suggestion
├── Component 4: ERP Clause Matching
├── Component 8: Frontend - Upload & Document List
├── Component 9: Export
└── Validation: End-to-end demo with real document
```

---

## Where to Start: Component 2 (LLM Clause Extraction)

**Why start here:**
- This is the core value proposition
- If clause extraction doesn't work well, nothing else matters
- It's the highest-risk, least-known part
- Can be tested independently with just a text file

**What we'll build:**
1. A Python script that takes contract text and returns structured clauses
2. Test it with sample contracts
3. Iterate on the prompt until extraction is reliable

**Success criteria:**
- Clauses are correctly bounded (not merged, not split)
- Clause numbers are extracted when present
- Page references are accurate
- Works on documents of various lengths

---

## Open Questions (To Answer Before Building)

1. **Do we have sample documents?** Need real contracts/POs to test against.

2. **What's the actual scope taxonomy?** The spec assumes 4 categories - is that right?
   - Entire PO
   - Specific line items
   - Flow-down to suppliers
   - No action needed

3. **ERP clause library format:** What does the exposed ERP database look like? Schema? Access method?

4. **Context window handling:** For 50+ page documents, do we process in chunks or use Claude's full 200K context?

5. **PDF quality:** Are these clean digital PDFs or scanned documents needing OCR?

---

## Tech Stack Summary

**Backend:**
- Python 3.11+
- FastAPI
- pdfplumber (PDF extraction)
- anthropic (Claude API)
- SQLAlchemy + SQLite

**Frontend:**
- React 18
- Vite
- Tailwind CSS

**Infrastructure (alpha):**
- Local development only
- SQLite file database
- No deployment infrastructure yet

---

## Next Step

Start with Component 2 (LLM Clause Extraction) as a standalone Python module. Build it, test it with sample text, iterate on prompts until it works reliably.

Command: `Let's build the clause extraction module first.`
