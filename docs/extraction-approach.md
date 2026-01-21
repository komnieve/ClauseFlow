# Clause Extraction: Line-Reference Approach

## The Problem

When using an LLM to extract clauses, we don't want the model to copy/reproduce text because:
- Models can hallucinate or subtly modify text
- Formatting can be lost
- No way to verify the extracted text matches the original
- Wastes tokens reproducing content we already have

## The Solution: Line-Reference Extraction

Instead of the model returning clause text, it returns **pointers** to where clauses exist in the original document.

### How It Works

**Step 1: Pre-process the document**
```
1  | ================================================================================
2  |                             PURCHASE ORDER
3  | ================================================================================
4  |
5  | ACME AEROSPACE CORPORATION
6  | 1200 Aviation Boulevard
...
145 | 1.3 ACCEPTANCE OF ORDER
146 |
147 | This Purchase Order constitutes an offer by Buyer to Supplier. Supplier's
148 | acceptance of this offer is expressly limited to the terms and conditions
149 | contained herein. Commencement of performance or shipment of Goods shall
150 | constitute acceptance of all terms and conditions. Any additional or different
151 | terms proposed by Supplier are hereby rejected unless expressly agreed to in
152 | writing by Buyer's authorized procurement representative.
```

**Step 2: Model returns line ranges**
```json
{
  "clauses": [
    {
      "start_line": 145,
      "end_line": 152,
      "clause_number": "1.3",
      "clause_title": "ACCEPTANCE OF ORDER",
      "chunk_type": "clause"
    }
  ]
}
```

**Step 3: We programmatically extract**
```python
clause_text = "\n".join(lines[145:153])  # Guaranteed accurate
```

## Benefits

1. **Zero reproduction risk** - Model never copies text
2. **Exact preservation** - Original formatting, whitespace, everything
3. **Verifiable** - Line numbers either exist or they don't
4. **Efficient** - Model output is tiny (just numbers and metadata)
5. **Auditable** - Easy to show "the model identified lines 145-152 as clause 1.3"

## Implementation Details

### Input Format

Add line numbers as a prefix, clearly delimited:

```
[001] ================================================================================
[002]                             PURCHASE ORDER
[003] ================================================================================
[004]
[005] ACME AEROSPACE CORPORATION
```

Use a format that's unambiguous and won't appear in the document:
- `[001]` with brackets
- Zero-padded for consistent width
- Delimiter (space or tab) after the number

### Output Schema

```typescript
interface ClauseReference {
  start_line: number;        // First line of the clause (inclusive)
  end_line: number;          // Last line of the clause (inclusive)
  clause_number: string | null;  // e.g., "1.3", "7.2.1" if present
  clause_title: string | null;   // e.g., "ACCEPTANCE OF ORDER" if present
  chunk_type: "clause" | "administrative" | "boilerplate" | "header" | "signature";
}

interface ExtractionResult {
  clauses: ClauseReference[];
}
```

### Validation Rules

After receiving the model's response, validate:

1. **Line numbers exist**: `1 <= start_line <= end_line <= total_lines`
2. **No overlaps**: Clauses shouldn't overlap (warn if they do)
3. **Reasonable coverage**: Flag large gaps that might be missed clauses
4. **Contiguous**: `start_line` to `end_line` defines a continuous range

### Prompt Design

```
You are analyzing a contract document to identify discrete clauses and sections.

The document has been pre-processed with line numbers in the format [NNN] at the start of each line.

Your task is to identify where clauses BEGIN and END by their line numbers.

IMPORTANT:
- DO NOT reproduce any text from the document
- ONLY return line number references
- A clause includes its header/title line AND all body text
- Identify the chunk_type for each section:
  - "clause" = A contractual obligation or requirement
  - "administrative" = Addresses, contacts, dates, PO details
  - "boilerplate" = Standard legal language, signatures
  - "header" = Section headers, table of contents, dividers

Return JSON in this exact format:
{
  "clauses": [
    {
      "start_line": <first line number>,
      "end_line": <last line number>,
      "clause_number": "<number like 1.3 or 7.2.1, or null if none>",
      "clause_title": "<title if present, or null>",
      "chunk_type": "<one of: clause, administrative, boilerplate, header>"
    }
  ]
}

Document:
---
{numbered_document}
---
```

### Edge Cases

**Multi-page clauses**: Just use the line range that spans pages. We track page breaks separately.

**Nested clauses**: For "7.2" containing "7.2.1" and "7.2.2":
- Option A: Return only the leaf clauses (7.2.1, 7.2.2)
- Option B: Return both parent and children with nesting indicated
- Recommendation: Start with Option A (simpler)

**Tables and lists**: Include the full table/list in the line range of the containing clause.

**Empty lines**: Include them in the range - we're capturing the complete block.

### Code Implementation

```python
def add_line_numbers(text: str) -> tuple[str, list[str]]:
    """Add line numbers to document text."""
    lines = text.split('\n')
    numbered_lines = []
    for i, line in enumerate(lines, start=1):
        numbered_lines.append(f"[{i:03d}] {line}")
    return '\n'.join(numbered_lines), lines

def extract_clause_text(lines: list[str], ref: ClauseReference) -> str:
    """Extract actual text using line reference."""
    # Convert to 0-indexed, end_line is inclusive
    start_idx = ref.start_line - 1
    end_idx = ref.end_line  # slice end is exclusive, so no -1
    return '\n'.join(lines[start_idx:end_idx])

def validate_references(refs: list[ClauseReference], total_lines: int) -> list[str]:
    """Validate clause references, return list of warnings."""
    warnings = []

    for ref in refs:
        if ref.start_line < 1:
            warnings.append(f"Invalid start_line {ref.start_line}")
        if ref.end_line > total_lines:
            warnings.append(f"end_line {ref.end_line} exceeds document length {total_lines}")
        if ref.start_line > ref.end_line:
            warnings.append(f"start_line {ref.start_line} > end_line {ref.end_line}")

    # Check for overlaps
    sorted_refs = sorted(refs, key=lambda r: r.start_line)
    for i in range(len(sorted_refs) - 1):
        if sorted_refs[i].end_line >= sorted_refs[i+1].start_line:
            warnings.append(
                f"Overlap: lines {sorted_refs[i].start_line}-{sorted_refs[i].end_line} "
                f"and {sorted_refs[i+1].start_line}-{sorted_refs[i+1].end_line}"
            )

    return warnings
```

## Comparison: Copy vs Reference

| Aspect | Copy Approach | Reference Approach |
|--------|--------------|-------------------|
| Text accuracy | Model might modify | Guaranteed exact |
| Token usage | High (full text repeated) | Low (just numbers) |
| Verification | Diff against original | Line numbers valid? |
| Formatting | May lose whitespace/special chars | Perfectly preserved |
| Debugging | "Why did it change this?" | "Why did it pick these lines?" |

## Open Questions

1. **Granularity**: Should we capture every paragraph, or just top-level clauses?
   - Recommendation: Start with top-level clauses (1.1, 1.2, 2.1, etc.)

2. **Handling insertions**: What if a clause references another? (e.g., "See Section 3.2")
   - For now: Just identify the boundaries, don't resolve references

3. **Context window**: For very long documents, do we:
   - Process in chunks and merge results?
   - Use full 200K context?
   - Recommendation: Test with full context first, add chunking if needed

## Next Steps

1. Build the line-numbering preprocessor
2. Build the LLM extraction function with the reference prompt
3. Build the validation layer
4. Test on sample PO
5. Iterate on prompt until extraction is reliable
