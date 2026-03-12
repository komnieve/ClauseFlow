import { useState, useEffect } from 'react';
import { getReviewSummary } from '../api/client';

/**
 * Attention dashboard — shows verification and workflow status above the review tabs.
 * Two rows: ERP verification attention + workflow attention.
 */
export default function AttentionDashboard({ documentId, clauses, onRefresh }) {
  const [summary, setSummary] = useState(null);

  const loadSummary = async () => {
    try {
      const data = await getReviewSummary(documentId);
      setSummary(data);
    } catch (err) {
      console.error('Failed to load review summary:', err);
    }
  };

  useEffect(() => {
    if (documentId) loadSummary();
  }, [documentId, clauses]);

  if (!summary) return null;

  const hasVerificationAttention = summary.mismatched > 0 || summary.not_found > 0 || summary.external_pending > 0;
  const hasWorkflowAttention = summary.unreviewed > 0;

  if (!hasVerificationAttention && !hasWorkflowAttention && summary.export_ready) return null;

  return (
    <div className="mb-6 space-y-3">
      {/* Verification attention */}
      {hasVerificationAttention && (
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-amber-400">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">ERP Verification</h3>
          <div className="flex flex-wrap gap-4 text-sm">
            {summary.mismatched > 0 && (
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-yellow-500"></span>
                <span className="font-medium text-yellow-800">{summary.mismatched} mismatch{summary.mismatched !== 1 ? 'es' : ''}</span>
                <span className="text-gray-500">need resolution</span>
              </span>
            )}
            {summary.not_found > 0 && (
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                <span className="font-medium text-red-800">{summary.not_found} new clause{summary.not_found !== 1 ? 's' : ''}</span>
                <span className="text-gray-500">to add to ERP</span>
              </span>
            )}
            {summary.external_pending > 0 && (
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-gray-400"></span>
                <span className="font-medium text-gray-700">{summary.external_pending} external ref{summary.external_pending !== 1 ? 's' : ''}</span>
                <span className="text-gray-500">pending verification</span>
              </span>
            )}
            {summary.matched > 0 && (
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-green-500"></span>
                <span className="text-green-800">{summary.matched} matched</span>
              </span>
            )}
          </div>
        </div>
      )}

      {/* Workflow attention */}
      {(hasWorkflowAttention || !summary.export_ready) && (
        <div className={`bg-white rounded-lg shadow p-4 border-l-4 ${summary.export_ready ? 'border-green-400' : 'border-blue-400'}`}>
          <div className="flex justify-between items-center">
            <div className="flex flex-wrap gap-4 text-sm">
              {summary.unreviewed > 0 && (
                <span className="text-gray-700">
                  <span className="font-medium">{summary.unreviewed}</span> clause{summary.unreviewed !== 1 ? 's' : ''} still unreviewed
                </span>
              )}
              {summary.reviewed > 0 && (
                <span className="text-green-700">
                  <span className="font-medium">{summary.reviewed}</span> reviewed
                </span>
              )}
              {summary.flagged > 0 && (
                <span className="text-yellow-700">
                  <span className="font-medium">{summary.flagged}</span> flagged
                </span>
              )}
              {summary.skipped > 0 && (
                <span className="text-gray-500">
                  <span className="font-medium">{summary.skipped}</span> skipped
                </span>
              )}
            </div>
            <div className="text-sm">
              {summary.export_ready ? (
                <span className="text-green-600 font-medium">Ready to export</span>
              ) : (
                <span className="text-gray-500">Export blocked</span>
              )}
            </div>
          </div>
          {summary.blockers.length > 0 && (
            <div className="mt-2 text-xs text-gray-500">
              {summary.blockers.map((b, i) => (
                <span key={i}>{i > 0 ? ' · ' : ''}{b}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
