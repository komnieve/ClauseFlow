import { useState, useEffect } from 'react';
import { getReferenceDoc } from '../api/client';

/**
 * Reference document detail view — shows extracted requirements
 */
export default function ReferenceDocDetail({ refDocId, onBack }) {
  const [refDoc, setRefDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedReqs, setExpandedReqs] = useState(new Set());

  useEffect(() => {
    loadRefDoc();
  }, [refDocId]);

  const loadRefDoc = async () => {
    setLoading(true);
    try {
      const data = await getReferenceDoc(refDocId);
      setRefDoc(data);
    } catch (err) {
      console.error('Failed to load reference doc:', err);
    }
    setLoading(false);
  };

  const toggleReq = (reqId) => {
    setExpandedReqs(prev => {
      const next = new Set(prev);
      if (next.has(reqId)) next.delete(reqId);
      else next.add(reqId);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto text-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
      </div>
    );
  }

  if (!refDoc) {
    return (
      <div className="max-w-4xl mx-auto text-center py-12 text-gray-500">
        Reference document not found.
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <button
        onClick={onBack}
        className="text-sm text-blue-600 hover:text-blue-800 mb-6 inline-block"
      >
        &larr; Back to library
      </button>

      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-2xl font-bold mb-2">
          {refDoc.doc_identifier || refDoc.filename}
          {refDoc.version && <span className="text-gray-500 ml-2 text-lg">{refDoc.version}</span>}
        </h2>
        {refDoc.title && (
          <div className="text-gray-600 mb-2">{refDoc.title}</div>
        )}
        <div className="flex gap-4 text-sm text-gray-500">
          <span>{refDoc.filename}</span>
          <span>{refDoc.total_lines} lines</span>
          <span className={refDoc.status === 'ready' ? 'text-green-600' : 'text-yellow-600'}>
            {refDoc.status}
          </span>
        </div>
      </div>

      {/* Children (if multi-spec book) */}
      {refDoc.children && refDoc.children.length > 0 && (
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold">Contained Specifications ({refDoc.children.length})</h3>
          </div>
          <div className="divide-y">
            {refDoc.children.map(child => (
              <div key={child.id} className="px-6 py-3 flex justify-between items-center">
                <div>
                  <span className="font-medium">{child.doc_identifier || child.filename}</span>
                  {child.version && <span className="text-gray-500 ml-2">{child.version}</span>}
                  {child.title && <span className="text-gray-400 ml-2">- {child.title}</span>}
                </div>
                <span className="text-sm text-gray-500">{child.requirement_count} requirements</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Requirements */}
      {refDoc.requirements && refDoc.requirements.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold">
              Requirements ({refDoc.requirements.length})
            </h3>
          </div>
          <div className="divide-y">
            {refDoc.requirements.map(req => (
              <div key={req.id} className="px-6 py-3">
                <div
                  className="flex justify-between items-center cursor-pointer hover:bg-gray-50 -mx-6 px-6 py-1"
                  onClick={() => toggleReq(req.id)}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-400 w-4">
                      {expandedReqs.has(req.id) ? '&#9660;' : '&#9654;'}
                    </span>
                    {req.requirement_number && (
                      <span className="font-mono text-blue-600 text-sm">{req.requirement_number}</span>
                    )}
                    <span className="text-sm">{req.title || '(untitled)'}</span>
                  </div>
                  <span className="text-xs text-gray-400">
                    Lines {req.start_line}-{req.end_line}
                  </span>
                </div>
                {expandedReqs.has(req.id) && req.text && (
                  <div className="mt-2 ml-7 bg-gray-50 rounded p-3 max-h-48 overflow-y-auto">
                    <pre className="whitespace-pre-wrap text-sm font-mono text-gray-700">{req.text}</pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {refDoc.requirements?.length === 0 && !refDoc.children?.length && (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          No requirements extracted from this document.
        </div>
      )}
    </div>
  );
}
