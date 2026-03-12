/**
 * Side-by-side diff panel for ERP mismatches.
 * Shows PO clause text vs ERP snapshot text with metadata.
 */
export default function ERPDiffPanel({ clause }) {
  if (clause.erp_match_status !== 'mismatched' || !clause.erp_snapshot_text) {
    return null;
  }

  return (
    <div className="mb-6 border border-yellow-200 rounded-lg overflow-hidden">
      <div className="bg-yellow-50 px-4 py-2 border-b border-yellow-200">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-yellow-800">Revision Mismatch</span>
          <span className="text-xs text-yellow-700">{clause.mismatch_details}</span>
        </div>
      </div>
      <div className="grid grid-cols-2 divide-x divide-yellow-200">
        {/* PO clause */}
        <div className="p-4">
          <div className="text-xs font-semibold text-gray-500 mb-1 uppercase tracking-wide">PO Clause</div>
          {clause.clause_number && (
            <div className="text-sm font-medium text-gray-700 mb-2">{clause.clause_number}</div>
          )}
          <div className="bg-gray-50 rounded p-3 max-h-48 overflow-y-auto">
            <pre className="whitespace-pre-wrap text-xs font-mono text-gray-700">{clause.text}</pre>
          </div>
        </div>
        {/* ERP clause */}
        <div className="p-4">
          <div className="text-xs font-semibold text-gray-500 mb-1 uppercase tracking-wide">ERP Record</div>
          <div className="text-sm font-medium text-gray-700 mb-2">
            {clause.erp_clause_id}
            {clause.erp_revision && <span className="text-gray-500 ml-1">({clause.erp_revision})</span>}
          </div>
          <div className="bg-gray-50 rounded p-3 max-h-48 overflow-y-auto">
            <pre className="whitespace-pre-wrap text-xs font-mono text-gray-700">{clause.erp_snapshot_text}</pre>
          </div>
        </div>
      </div>
    </div>
  );
}
