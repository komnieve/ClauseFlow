import { useState, useEffect, useRef } from 'react';
import {
  getCustomers, deleteCustomer,
  getCustomerReferenceDocs, uploadReferenceDoc, deleteReferenceDoc,
} from '../api/client';

/**
 * Reference Library management view — browse and upload reference specs per customer
 */
export default function ReferenceLibrary({ onViewRefDoc, onBack }) {
  const [customers, setCustomers] = useState([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState(null);
  const [refDocs, setRefDocs] = useState([]);
  const [loading, setLoading] = useState(false);

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [docIdentifier, setDocIdentifier] = useState('');
  const [version, setVersion] = useState('');
  const fileInputRef = useRef(null);

  useEffect(() => {
    loadCustomers();
  }, []);

  useEffect(() => {
    if (selectedCustomerId) {
      loadRefDocs(selectedCustomerId);
    } else {
      setRefDocs([]);
    }
  }, [selectedCustomerId]);

  const loadCustomers = async () => {
    try {
      const data = await getCustomers();
      setCustomers(data);
      if (data.length > 0 && !selectedCustomerId) {
        setSelectedCustomerId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load customers:', err);
    }
  };

  const loadRefDocs = async (custId) => {
    setLoading(true);
    try {
      const data = await getCustomerReferenceDocs(custId);
      setRefDocs(data);
    } catch (err) {
      console.error('Failed to load reference docs:', err);
    }
    setLoading(false);
  };

  const handleUpload = async (file) => {
    if (!selectedCustomerId) return;
    setUploading(true);
    try {
      await uploadReferenceDoc(
        selectedCustomerId,
        file,
        docIdentifier || null,
        version || null,
      );
      setDocIdentifier('');
      setVersion('');
      // Poll for completion
      const pollInterval = setInterval(async () => {
        const docs = await getCustomerReferenceDocs(selectedCustomerId);
        setRefDocs(docs);
        const allDone = docs.every(d => d.status === 'ready' || d.status === 'error');
        if (allDone) clearInterval(pollInterval);
      }, 2000);
    } catch (err) {
      alert('Upload failed: ' + err.message);
    }
    setUploading(false);
  };

  const handleDelete = async (refDocId) => {
    if (!confirm('Delete this reference document?')) return;
    try {
      await deleteReferenceDoc(refDocId);
      setRefDocs(prev => prev.filter(d => d.id !== refDocId));
    } catch (err) {
      alert('Delete failed: ' + err.message);
    }
  };

  const handleDeleteCustomer = async (custId) => {
    if (!confirm('Delete this customer and all their reference documents?')) return;
    try {
      await deleteCustomer(custId);
      setCustomers(prev => prev.filter(c => c.id !== custId));
      if (selectedCustomerId === custId) {
        setSelectedCustomerId(null);
      }
    } catch (err) {
      alert('Delete failed: ' + err.message);
    }
  };

  // Group ref docs by identifier
  const grouped = {};
  refDocs.forEach(d => {
    const key = d.doc_identifier || d.filename;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(d);
  });

  const statusColors = {
    uploading: 'text-gray-500',
    processing: 'text-yellow-600',
    ready: 'text-green-600',
    error: 'text-red-600',
  };

  return (
    <div className="max-w-4xl mx-auto">
      <button
        onClick={onBack}
        className="text-sm text-blue-600 hover:text-blue-800 mb-6 inline-block"
      >
        &larr; Back to documents
      </button>

      <h2 className="text-2xl font-bold mb-6">Reference Library</h2>

      {/* Customer picker */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">Customer</label>
        <div className="flex items-center gap-3">
          <select
            value={selectedCustomerId || ''}
            onChange={(e) => setSelectedCustomerId(e.target.value ? parseInt(e.target.value) : null)}
            className="px-3 py-2 border rounded text-sm flex-1"
          >
            <option value="">Select a customer...</option>
            {customers.map(c => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.reference_doc_count} specs, {c.document_count} POs)
              </option>
            ))}
          </select>
          {selectedCustomerId && (
            <button
              onClick={() => handleDeleteCustomer(selectedCustomerId)}
              className="px-3 py-2 text-red-600 text-sm hover:text-red-800"
              title="Delete customer"
            >
              Delete
            </button>
          )}
        </div>
      </div>

      {selectedCustomerId && (
        <>
          {/* Upload area */}
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <h3 className="text-lg font-semibold mb-3">Upload Reference Spec</h3>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Doc Identifier (optional)</label>
                <input
                  type="text"
                  value={docIdentifier}
                  onChange={(e) => setDocIdentifier(e.target.value)}
                  placeholder="e.g. SPXQC-17"
                  className="w-full px-3 py-2 border rounded text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Version (optional)</label>
                <input
                  type="text"
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  placeholder="e.g. v57.0"
                  className="w-full px-3 py-2 border rounded text-sm"
                />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.pdf"
                onChange={(e) => e.target.files[0] && handleUpload(e.target.files[0])}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {uploading ? 'Uploading...' : 'Choose File & Upload'}
              </button>
              <span className="text-xs text-gray-500">Supports .txt and .pdf files</span>
            </div>
          </div>

          {/* Reference docs list */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b">
              <h3 className="text-lg font-semibold">
                Reference Documents ({refDocs.length})
              </h3>
            </div>

            {loading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto" />
              </div>
            ) : refDocs.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No reference documents uploaded yet.
              </div>
            ) : (
              <div className="divide-y">
                {Object.entries(grouped).map(([key, docs]) => (
                  <div key={key} className="px-6 py-3">
                    <div className="font-medium text-sm text-gray-800 mb-1">{key}</div>
                    {docs.map(doc => (
                      <div
                        key={doc.id}
                        className="flex items-center justify-between py-1 pl-4"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-sm">{doc.filename}</span>
                          {doc.version && (
                            <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">{doc.version}</span>
                          )}
                          {doc.title && (
                            <span className="text-xs text-gray-500">{doc.title}</span>
                          )}
                          <span className={`text-xs ${statusColors[doc.status]}`}>
                            {doc.status}
                          </span>
                          {doc.requirement_count > 0 && (
                            <span className="text-xs text-gray-400">
                              {doc.requirement_count} req{doc.requirement_count !== 1 ? 's' : ''}
                            </span>
                          )}
                          {doc.children_count > 0 && (
                            <span className="text-xs text-purple-600">
                              book ({doc.children_count} specs)
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {doc.status === 'ready' && (
                            <button
                              onClick={() => onViewRefDoc(doc.id)}
                              className="text-xs text-blue-600 hover:text-blue-800"
                            >
                              View
                            </button>
                          )}
                          <button
                            onClick={() => handleDelete(doc.id)}
                            className="text-xs text-red-500 hover:text-red-700"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
