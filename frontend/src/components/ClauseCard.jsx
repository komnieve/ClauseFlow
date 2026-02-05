import { useState, useEffect, useRef } from 'react';
import { updateClause, markClauseReviewed, flagClause } from '../api/client';

/**
 * Card for reviewing a single clause
 */
export default function ClauseCard({ clause, onUpdate, onNext, onPrev, currentIndex, totalCount, sectionTitle, lineItems: docLineItems }) {
  const [scope, setScope] = useState(clause.scope || '');
  const [lineItems, setLineItems] = useState(clause.line_items || '');
  const [notes, setNotes] = useState(clause.notes || '');
  const [saving, setSaving] = useState(false);
  const markReviewedRef = useRef(null);
  const flagRef = useRef(null);

  // Keyboard shortcuts: Enter = mark reviewed, F = flag
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.matches('input, textarea')) return;
      if (e.key === 'Enter') {
        e.preventDefault();
        markReviewedRef.current?.();
      } else if (e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        flagRef.current?.();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleScopeChange = async (newScope) => {
    setScope(newScope);
    setSaving(true);
    try {
      const updated = await updateClause(clause.id, { scope: newScope });
      onUpdate(updated);
    } catch (err) {
      console.error('Failed to update scope:', err);
    }
    setSaving(false);
  };

  const handleNotesBlur = async () => {
    if (notes !== clause.notes) {
      setSaving(true);
      try {
        const updated = await updateClause(clause.id, { notes });
        onUpdate(updated);
      } catch (err) {
        console.error('Failed to update notes:', err);
      }
      setSaving(false);
    }
  };

  const handleLineItemsBlur = async () => {
    if (lineItems !== clause.line_items) {
      setSaving(true);
      try {
        const updated = await updateClause(clause.id, { line_items: lineItems });
        onUpdate(updated);
      } catch (err) {
        console.error('Failed to update line items:', err);
      }
      setSaving(false);
    }
  };

  const handleMarkReviewed = async () => {
    setSaving(true);
    try {
      const updated = await markClauseReviewed(clause.id);
      onUpdate(updated);
      onNext();
    } catch (err) {
      console.error('Failed to mark reviewed:', err);
    }
    setSaving(false);
  };

  // Keep refs updated with latest handlers
  markReviewedRef.current = handleMarkReviewed;

  const handleFlag = async () => {
    setSaving(true);
    try {
      const updated = await flagClause(clause.id);
      onUpdate(updated);
      onNext();
    } catch (err) {
      console.error('Failed to flag:', err);
    }
    setSaving(false);
  };

  flagRef.current = handleFlag;

  const chunkTypeColors = {
    clause: 'bg-blue-100 text-blue-800',
    header: 'bg-purple-100 text-purple-800',
    administrative: 'bg-gray-100 text-gray-800',
    boilerplate: 'bg-gray-100 text-gray-600',
    signature: 'bg-orange-100 text-orange-800',
  };

  const statusColors = {
    unreviewed: 'bg-gray-100 text-gray-600',
    reviewed: 'bg-green-100 text-green-800',
    flagged: 'bg-yellow-100 text-yellow-800',
  };

  const scopeTypeBadge = clause.scope_type === 'po_wide'
    ? { label: 'PO-Wide', className: 'bg-indigo-100 text-indigo-800' }
    : clause.scope_type === 'line_specific'
    ? { label: 'Line-Specific', className: 'bg-teal-100 text-teal-800' }
    : null;

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Section breadcrumb */}
      {sectionTitle && (
        <div className="text-xs text-gray-500 mb-2">{sectionTitle}</div>
      )}

      {/* Header with navigation */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-3">
          <span className={`px-2 py-1 rounded text-xs font-medium ${chunkTypeColors[clause.chunk_type]}`}>
            {clause.chunk_type}
          </span>
          {scopeTypeBadge && (
            <span className={`px-2 py-1 rounded text-xs font-medium ${scopeTypeBadge.className}`}>
              {scopeTypeBadge.label}
            </span>
          )}
          <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[clause.review_status]}`}>
            {clause.review_status}
          </span>
          {saving && <span className="text-xs text-gray-400">Saving...</span>}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onPrev}
            disabled={currentIndex === 0}
            className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
          >
            ← Prev
          </button>
          <span className="text-sm text-gray-600">
            {currentIndex + 1} of {totalCount}
          </span>
          <button
            onClick={onNext}
            disabled={currentIndex === totalCount - 1}
            className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
          >
            Next →
          </button>
        </div>
      </div>

      {/* Clause title */}
      <div className="mb-4">
        <h2 className="text-xl font-semibold">
          {clause.clause_number && <span className="text-blue-600">{clause.clause_number}</span>}
          {clause.clause_number && clause.clause_title && ' - '}
          {clause.clause_title || (clause.chunk_type === 'clause' ? '(Untitled clause)' : '')}
        </h2>
        <div className="text-sm text-gray-500">
          Lines {clause.start_line} - {clause.end_line}
          {clause.scope_type === 'line_specific' && clause.applicable_lines && (
            <span className="ml-2 text-teal-700">
              (Applies to line items: {clause.applicable_lines})
            </span>
          )}
        </div>
      </div>

      {/* Clause text */}
      <div className="bg-gray-50 rounded p-4 mb-6 max-h-64 overflow-y-auto">
        <pre className="whitespace-pre-wrap text-sm font-mono">{clause.text}</pre>
      </div>

      {/* Scope selection - only for actual clauses */}
      {clause.chunk_type === 'clause' && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            What does this clause apply to?
          </label>
          <div className="flex flex-wrap gap-2">
            {[
              { value: 'entire_po', label: 'Entire PO' },
              { value: 'line_items', label: 'Specific Line Items' },
              { value: 'flow_down', label: 'Flow-down to Suppliers' },
              { value: 'no_action', label: 'No Action Needed' },
            ].map((option) => (
              <button
                key={option.value}
                onClick={() => handleScopeChange(option.value)}
                className={`px-4 py-2 rounded border text-sm ${
                  scope === option.value
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>

          {/* Line items input - only show if scope is line_items */}
          {scope === 'line_items' && (
            <div className="mt-3">
              <input
                type="text"
                value={lineItems}
                onChange={(e) => setLineItems(e.target.value)}
                onBlur={handleLineItemsBlur}
                placeholder="Enter line item numbers (e.g., 1, 3, 5)"
                className="w-full px-3 py-2 border rounded text-sm"
              />
            </div>
          )}
        </div>
      )}

      {/* Notes */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Notes
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          onBlur={handleNotesBlur}
          placeholder="Add any notes about this clause..."
          className="w-full px-3 py-2 border rounded text-sm h-20 resize-none"
        />
      </div>

      {/* Actions */}
      <div className="flex justify-between items-center pt-4 border-t">
        <button
          onClick={handleFlag}
          className="px-4 py-2 text-sm bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200"
        >
          Flag for Later
        </button>
        <button
          onClick={handleMarkReviewed}
          className="px-6 py-2 text-sm bg-green-600 text-white rounded hover:bg-green-700 font-medium"
        >
          Mark as Reviewed →
        </button>
      </div>
    </div>
  );
}
