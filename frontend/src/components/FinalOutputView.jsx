import { useState, useEffect } from 'react';
import { getFinalOutput } from '../api/client';
import ERPStatusBadge from './ERPStatusBadge';

/**
 * Final output view — clean, grouped, print-friendly format for ERP entry.
 * Only accessible after all clauses are addressed.
 */
export default function FinalOutputView({ documentId, documentName, onBack }) {
  const [output, setOutput] = useState(null);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('by_clause'); // by_clause | by_line

  useEffect(() => {
    loadOutput();
  }, [documentId]);

  const loadOutput = async () => {
    try {
      const data = await getFinalOutput(documentId);
      setOutput(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  };

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <div className="text-yellow-600 text-lg font-medium mb-2">Export Not Ready</div>
        <div className="text-gray-500 mb-4">{error}</div>
        <button onClick={onBack} className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
          Back to Review
        </button>
      </div>
    );
  }

  if (!output) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
      </div>
    );
  }

  const vs = output.verification_summary;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Final Output</h2>
          <p className="text-sm text-gray-500">{documentName} — All clauses addressed</p>
        </div>
        <div className="flex gap-2">
          <button onClick={onBack} className="px-4 py-2 text-sm border rounded hover:bg-gray-50">
            Back to Review
          </button>
          <button
            onClick={() => window.print()}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Print
          </button>
        </div>
      </div>

      {/* Verification Summary */}
      <div className="bg-white rounded-lg shadow p-6 print:shadow-none print:border">
        <h3 className="text-lg font-semibold mb-4">Verification Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-50 rounded">
            <div className="text-2xl font-bold text-gray-900">{vs.total}</div>
            <div className="text-xs text-gray-500">Total Clauses</div>
          </div>
          <div className="text-center p-3 bg-green-50 rounded">
            <div className="text-2xl font-bold text-green-700">{vs.matched}</div>
            <div className="text-xs text-green-600">Matched</div>
          </div>
          <div className="text-center p-3 bg-yellow-50 rounded">
            <div className="text-2xl font-bold text-yellow-700">{vs.mismatched}</div>
            <div className="text-xs text-yellow-600">Mismatched</div>
          </div>
          <div className="text-center p-3 bg-red-50 rounded">
            <div className="text-2xl font-bold text-red-700">{vs.not_found + (vs.external_pending || 0)}</div>
            <div className="text-xs text-red-600">New / External</div>
          </div>
        </div>
        <div className="mt-3 text-sm text-gray-500">
          {vs.po_wide} PO-wide · {vs.line_specific} line-specific
        </div>
      </div>

      {/* PO-Wide Clauses */}
      <div className="bg-white rounded-lg shadow p-6 print:shadow-none print:border">
        <h3 className="text-lg font-semibold mb-4">PO-Wide Clauses ({output.po_wide_clauses.length})</h3>
        {output.po_wide_clauses.length === 0 ? (
          <p className="text-gray-500 text-sm">No PO-wide clauses found.</p>
        ) : (
          <div className="space-y-3">
            {output.po_wide_clauses.map((c, i) => (
              <div key={c.id} className="flex items-start gap-3 py-2 border-b last:border-0">
                <span className="text-gray-400 text-sm font-mono w-8 flex-shrink-0">{i + 1}.</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm">
                      {c.clause_number && <span className="text-blue-600">{c.clause_number}</span>}
                      {c.clause_number && c.clause_title && ' — '}
                      {c.clause_title}
                    </span>
                    <ERPStatusBadge
                      status={c.erp_match_status}
                      revision={c.erp_revision}
                      date={c.erp_date}
                      mismatchDetails={c.mismatch_details}
                      compact
                    />
                  </div>
                  {c.mismatch_details && (
                    <div className="text-xs text-yellow-700 mt-1">{c.mismatch_details}</div>
                  )}
                  {c.notes && (
                    <div className="text-xs text-gray-500 mt-1 italic">Note: {c.notes}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Line-Specific Clauses */}
      <div className="bg-white rounded-lg shadow p-6 print:shadow-none print:border">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Line-Specific Clauses ({output.line_specific_by_clause.length})</h3>
          <div className="flex gap-1 bg-gray-100 rounded p-0.5">
            <button
              onClick={() => setViewMode('by_clause')}
              className={`px-3 py-1 rounded text-xs font-medium ${viewMode === 'by_clause' ? 'bg-white shadow text-gray-900' : 'text-gray-500'}`}
            >
              By Clause
            </button>
            <button
              onClick={() => setViewMode('by_line')}
              className={`px-3 py-1 rounded text-xs font-medium ${viewMode === 'by_line' ? 'bg-white shadow text-gray-900' : 'text-gray-500'}`}
            >
              By Line
            </button>
          </div>
        </div>

        {viewMode === 'by_clause' ? (
          <div className="space-y-3">
            {output.line_specific_by_clause.map((c, i) => (
              <div key={c.id} className="flex items-start gap-3 py-2 border-b last:border-0">
                <span className="text-gray-400 text-sm font-mono w-8 flex-shrink-0">{i + 1}.</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm">
                      {c.clause_number && <span className="text-blue-600">{c.clause_number}</span>}
                      {c.clause_number && c.clause_title && ' — '}
                      {c.clause_title}
                    </span>
                    <ERPStatusBadge status={c.erp_match_status} compact />
                  </div>
                  {c.applicable_lines && (
                    <div className="text-xs text-teal-700 mt-1">
                      Applies to: {c.applicable_lines}
                    </div>
                  )}
                  {c.mismatch_details && (
                    <div className="text-xs text-yellow-700 mt-1">{c.mismatch_details}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(output.line_specific_by_line)
              .sort(([a], [b]) => {
                const numA = parseInt(a.replace(/\D/g, '')) || 0;
                const numB = parseInt(b.replace(/\D/g, '')) || 0;
                return numA - numB;
              })
              .map(([lineKey, lineClauses]) => (
                <div key={lineKey}>
                  <h4 className="text-sm font-semibold text-teal-800 mb-2 border-b pb-1">{lineKey}</h4>
                  <div className="space-y-2 pl-4">
                    {lineClauses.map(c => (
                      <div key={c.id} className="flex items-center gap-2 text-sm">
                        <ERPStatusBadge status={c.erp_match_status} compact />
                        <span>
                          {c.clause_number && <span className="text-blue-600 font-mono">{c.clause_number}</span>}
                          {c.clause_title && <span className="text-gray-700 ml-1">— {c.clause_title}</span>}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}
