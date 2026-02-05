import { useState } from 'react';

/**
 * Document overview page — shows PO metadata, line items, sections summary,
 * clause distribution report, and action buttons.
 * V3: Expandable text for sections and line items.
 */
export default function DocumentOverview({ document, clauses, sections, lineItems, onStartReview, onReprocess, onBack }) {
  const clauseCount = clauses.length;
  const sectionCount = sections.length;
  const lineItemCount = lineItems.length;

  const [expandedSections, setExpandedSections] = useState(new Set());
  const [expandedLineItems, setExpandedLineItems] = useState(new Set());

  const toggleSection = (sectionId) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(sectionId)) next.delete(sectionId);
      else next.add(sectionId);
      return next;
    });
  };

  const toggleLineItem = (itemId) => {
    setExpandedLineItems(prev => {
      const next = new Set(prev);
      if (next.has(itemId)) next.delete(itemId);
      else next.add(itemId);
      return next;
    });
  };

  // Derive line item text from parent section
  const getLineItemText = (item) => {
    if (!item.start_line || !item.end_line) return null;
    const parentSection = sections.find(s => s.id === item.section_id);
    if (!parentSection || !parentSection.text) return null;
    const sectionLines = parentSection.text.split('\n');
    const offset = parentSection.start_line;
    const startIdx = item.start_line - offset;
    const endIdx = item.end_line - offset + 1;
    if (startIdx < 0 || endIdx > sectionLines.length) return null;
    return sectionLines.slice(startIdx, endIdx).join('\n');
  };

  // --- Distribution stats ---
  const poWideClauses = clauses.filter(c => c.scope_type === 'po_wide');
  const lineSpecificClauses = clauses.filter(c => c.scope_type === 'line_specific');
  const poWideCount = poWideClauses.length;
  const lineSpecificCount = lineSpecificClauses.length;
  const poWidePct = clauseCount > 0 ? Math.round((poWideCount / clauseCount) * 100) : 0;
  const lineSpecificPct = clauseCount > 0 ? Math.round((lineSpecificCount / clauseCount) * 100) : 0;

  // Chunk type counts
  const chunkTypeCounts = {};
  clauses.forEach(c => {
    const t = c.chunk_type || 'clause';
    chunkTypeCounts[t] = (chunkTypeCounts[t] || 0) + 1;
  });

  // Review progress by scope
  const poWideReviewed = poWideClauses.filter(c => c.review_status === 'reviewed' || c.review_status === 'flagged').length;
  const lineSpecificReviewed = lineSpecificClauses.filter(c => c.review_status === 'reviewed' || c.review_status === 'flagged').length;

  // Reference stats
  const allRefLinks = clauses.flatMap(c => c.reference_links || []);
  const unresolvedCount = allRefLinks.filter(l => l.match_status === 'unresolved').length;
  const matchedCount = allRefLinks.filter(l => l.match_status === 'matched').length;
  const partialCount = allRefLinks.filter(l => l.match_status === 'partial').length;

  return (
    <div className="max-w-4xl mx-auto">
      {/* Back link */}
      <button
        onClick={onBack}
        className="text-sm text-blue-600 hover:text-blue-800 mb-6 inline-block"
      >
        &larr; Back to documents
      </button>

      {/* Document metadata */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-2xl font-bold">{document.filename}</h2>
          {document.customer_name && (
            <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs font-medium rounded">
              {document.customer_name}
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-50 rounded">
            <div className="text-2xl font-bold text-gray-900">{document.total_lines || '-'}</div>
            <div className="text-sm text-gray-500">Lines</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded">
            <div className="text-2xl font-bold text-gray-900">{sectionCount}</div>
            <div className="text-sm text-gray-500">Sections</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded">
            <div className="text-2xl font-bold text-blue-600">{clauseCount}</div>
            <div className="text-sm text-gray-500">Clauses</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded">
            <div className="text-2xl font-bold text-gray-900">{lineItemCount}</div>
            <div className="text-sm text-gray-500">Line Items</div>
          </div>
        </div>
      </div>

      {/* Reference summary (if any) */}
      {allRefLinks.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">External References</h3>
          <div className="flex gap-4 text-sm">
            {matchedCount > 0 && (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 bg-green-500 rounded-full inline-block"></span>
                {matchedCount} matched
              </span>
            )}
            {partialCount > 0 && (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 bg-yellow-500 rounded-full inline-block"></span>
                {partialCount} partial
              </span>
            )}
            {unresolvedCount > 0 && (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 bg-red-500 rounded-full inline-block"></span>
                {unresolvedCount} unresolved
              </span>
            )}
          </div>
        </div>
      )}

      {/* Line items table */}
      {lineItems.length > 0 && (
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold">Line Items</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">#</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Part Number</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Description</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Quantity</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Quality Level</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {lineItems.map((item, index) => {
                  const itemText = getLineItemText(item);
                  const isExpanded = expandedLineItems.has(item.id);
                  return (
                    <tr
                      key={item.id || index}
                      className={`hover:bg-gray-50 ${itemText ? 'cursor-pointer' : ''}`}
                      onClick={() => itemText && toggleLineItem(item.id)}
                    >
                      <td className="px-4 py-3 text-sm text-gray-500" colSpan={isExpanded ? 5 : undefined}>
                        {isExpanded ? (
                          <div>
                            <div className="flex items-center gap-3 mb-2">
                              <span className="text-xs text-gray-400">&#9660;</span>
                              <span className="font-medium">Line {item.line_number || index + 1}</span>
                              <span className="font-mono text-xs">{item.part_number || '-'}</span>
                              <span className="text-xs text-gray-500">{item.description || '-'}</span>
                            </div>
                            <div className="bg-gray-50 rounded p-3 max-h-40 overflow-y-auto">
                              <pre className="whitespace-pre-wrap text-xs font-mono text-gray-700">{itemText}</pre>
                            </div>
                          </div>
                        ) : (
                          <span className="flex items-center gap-1">
                            {itemText && <span className="text-xs text-gray-400">&#9654;</span>}
                            {item.line_number || index + 1}
                          </span>
                        )}
                      </td>
                      {!isExpanded && (
                        <>
                          <td className="px-4 py-3 text-sm font-mono">{item.part_number || '-'}</td>
                          <td className="px-4 py-3 text-sm">{item.description || '-'}</td>
                          <td className="px-4 py-3 text-sm">{item.quantity || '-'}</td>
                          <td className="px-4 py-3 text-sm">{item.quality_level || '-'}</td>
                        </>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sections summary — expandable text */}
      {sections.length > 0 && (
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold">Sections</h3>
          </div>
          <div className="divide-y">
            {sections.map(section => {
              const sectionClauses = clauses.filter(c => c.section_id === section.id);
              const reviewed = sectionClauses.filter(c => c.review_status === 'reviewed' || c.review_status === 'flagged').length;
              const flagged = sectionClauses.filter(c => c.review_status === 'flagged').length;
              const total = sectionClauses.length;
              const isExpanded = expandedSections.has(section.id);

              return (
                <div key={section.id}>
                  <div
                    className="px-6 py-3 flex justify-between items-center cursor-pointer hover:bg-gray-50"
                    onClick={() => toggleSection(section.id)}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">
                        {isExpanded ? '\u25BC' : '\u25B6'}
                      </span>
                      <span className="font-medium">{section.section_title || `Section ${section.order_index + 1}`}</span>
                      <span className="text-sm text-gray-500">
                        Lines {section.start_line}&ndash;{section.end_line}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      {total > 0 && (
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-500 rounded-full h-2"
                            style={{ width: `${Math.round((reviewed / total) * 100)}%` }}
                          />
                        </div>
                      )}
                      <span className="text-sm text-gray-500 whitespace-nowrap">
                        {total} clause{total !== 1 ? 's' : ''}
                        {flagged > 0 && <span className="text-amber-600 ml-1">({flagged} flagged)</span>}
                      </span>
                    </div>
                  </div>
                  {isExpanded && section.text && (
                    <div className="px-6 pb-3">
                      <div className="bg-gray-50 rounded p-3 max-h-64 overflow-y-auto">
                        <pre className="whitespace-pre-wrap text-xs font-mono text-gray-700">{section.text}</pre>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Clause Distribution Report */}
      {clauseCount > 0 && (
        <div className="bg-white rounded-lg shadow mb-6 p-6">
          <h3 className="text-lg font-semibold mb-4">Clause Distribution</h3>

          {/* Scope breakdown bar */}
          <div className="mb-5">
            <div className="text-sm text-gray-600 mb-2">Scope Breakdown</div>
            <div className="flex h-6 rounded-full overflow-hidden bg-gray-200">
              {poWideCount > 0 && (
                <div
                  className="bg-indigo-500 flex items-center justify-center text-white text-xs font-medium"
                  style={{ width: `${poWidePct}%` }}
                  title={`PO-Wide: ${poWideCount}`}
                >
                  {poWidePct >= 15 && `${poWideCount}`}
                </div>
              )}
              {lineSpecificCount > 0 && (
                <div
                  className="bg-teal-500 flex items-center justify-center text-white text-xs font-medium"
                  style={{ width: `${lineSpecificPct}%` }}
                  title={`Line-Specific: ${lineSpecificCount}`}
                >
                  {lineSpecificPct >= 15 && `${lineSpecificCount}`}
                </div>
              )}
            </div>
            <div className="flex justify-between mt-1 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <span className="inline-block w-2 h-2 bg-indigo-500 rounded-full"></span>
                PO-Wide: {poWideCount} ({poWidePct}%)
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-2 h-2 bg-teal-500 rounded-full"></span>
                Line-Specific: {lineSpecificCount} ({lineSpecificPct}%)
              </span>
            </div>
          </div>

          {/* Chunk type summary */}
          <div className="mb-5">
            <div className="text-sm text-gray-600 mb-1">Chunk Types</div>
            <div className="text-sm text-gray-800">
              {Object.entries(chunkTypeCounts).map(([type, count], i) => (
                <span key={type}>
                  {i > 0 && ', '}
                  <span className="font-medium">{count}</span> {type}
                </span>
              ))}
            </div>
          </div>

          {/* Review progress by scope */}
          <div>
            <div className="text-sm text-gray-600 mb-2">Review Progress by Scope</div>
            <div className="space-y-2">
              {poWideCount > 0 && (
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-700 w-28">PO-Wide</span>
                  <div className="flex-1 bg-gray-200 rounded-full h-3">
                    <div
                      className="bg-indigo-500 rounded-full h-3 transition-all"
                      style={{ width: `${poWideCount > 0 ? Math.round((poWideReviewed / poWideCount) * 100) : 0}%` }}
                    />
                  </div>
                  <span className="text-sm text-gray-500 w-16 text-right">{poWideReviewed}/{poWideCount}</span>
                </div>
              )}
              {lineSpecificCount > 0 && (
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-700 w-28">Line-Specific</span>
                  <div className="flex-1 bg-gray-200 rounded-full h-3">
                    <div
                      className="bg-teal-500 rounded-full h-3 transition-all"
                      style={{ width: `${lineSpecificCount > 0 ? Math.round((lineSpecificReviewed / lineSpecificCount) * 100) : 0}%` }}
                    />
                  </div>
                  <span className="text-sm text-gray-500 w-16 text-right">{lineSpecificReviewed}/{lineSpecificCount}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="text-center flex justify-center gap-4">
        <button
          onClick={onStartReview}
          className="px-8 py-3 bg-blue-600 text-white rounded-lg text-lg font-medium hover:bg-blue-700 shadow"
        >
          Start Review &mdash; {clauseCount} clause{clauseCount !== 1 ? 's' : ''}
        </button>
        <button
          onClick={onReprocess}
          className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg text-lg font-medium hover:bg-gray-300 shadow"
        >
          Re-extract
        </button>
      </div>
    </div>
  );
}
