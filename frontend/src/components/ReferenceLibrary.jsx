import { useState, useEffect, useRef } from 'react';
import {
  getCustomers, deleteCustomer,
  getCustomerReferenceDocs, uploadReferenceDoc, deleteReferenceDoc,
} from '../api/client';

/**
 * Try to guess doc identifier and version from a filename.
 * e.g. "SDC-Q-100_RevC_Source_Inspection.txt" → { id: "SDC-Q-100", ver: "Rev C" }
 */
function guessFromFilename(filename) {
  const name = filename.replace(/\.(txt|pdf)$/i, '');

  // Common patterns: "SPEC-123_RevA_Title", "SPEC-123_v4.1_Title"
  const revMatch = name.match(/^([A-Z][A-Z0-9\-]+\d+)[_\s]+(Rev\s*[A-Z0-9]+)/i);
  if (revMatch) return { id: revMatch[1], ver: revMatch[2].replace(/^(Rev)\s*([A-Z0-9]+)$/i, '$1 $2') };

  const verMatch = name.match(/^([A-Z][A-Z0-9\-]+\d+)[_\s]+(v[\d.]+)/i);
  if (verMatch) return { id: verMatch[1], ver: verMatch[2] };

  // Just the identifier prefix before first underscore
  const idMatch = name.match(/^([A-Z][A-Z0-9\-]+\d+)/i);
  if (idMatch) return { id: idMatch[1], ver: '' };

  return { id: '', ver: '' };
}

/**
 * Reference Library management view — browse and upload reference specs per customer
 */
export default function ReferenceLibrary({ onViewRefDoc, onBack }) {
  const [customers, setCustomers] = useState([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState(null);
  const [refDocs, setRefDocs] = useState([]);
  const [loading, setLoading] = useState(false);

  // Upload state — two-step: pick file, then confirm & upload
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
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

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    const guess = guessFromFilename(file.name);
    setDocIdentifier(guess.id);
    setVersion(guess.ver);
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    setDocIdentifier('');
    setVersion('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleUpload = async () => {
    if (!selectedCustomerId || !selectedFile) return;
    setUploading(true);
    try {
      await uploadReferenceDoc(
        selectedCustomerId,
        selectedFile,
        docIdentifier || null,
        version || null,
      );
      handleClearFile();
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

  // Show each doc as its own entry — only group children under their parent
  const topLevelDocs = refDocs.filter(d => !d.parent_id);

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
          {/* Upload area — two-step: choose file, then review & upload */}
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <h3 className="text-lg font-semibold mb-3">Upload Reference Spec</h3>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.pdf"
              onChange={(e) => e.target.files[0] && handleFileSelect(e.target.files[0])}
              className="hidden"
            />

            {!selectedFile ? (
              <div className="flex items-center gap-3">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded border border-gray-300 hover:bg-gray-200"
                >
                  Choose File...
                </button>
                <span className="text-xs text-gray-500">Supports .txt and .pdf files</span>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 mb-3 p-2 bg-blue-50 rounded border border-blue-200">
                  <svg className="w-4 h-4 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="text-sm font-medium text-blue-800 flex-1 truncate">{selectedFile.name}</span>
                  <button
                    onClick={handleClearFile}
                    className="text-xs text-gray-500 hover:text-red-500"
                    title="Remove file"
                  >✕</button>
                </div>
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Doc Identifier</label>
                    <input
                      type="text"
                      value={docIdentifier}
                      onChange={(e) => setDocIdentifier(e.target.value)}
                      placeholder="e.g. SDC-Q-100"
                      className="w-full px-3 py-2 border rounded text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Version</label>
                    <input
                      type="text"
                      value={version}
                      onChange={(e) => setVersion(e.target.value)}
                      placeholder="e.g. Rev C"
                      className="w-full px-3 py-2 border rounded text-sm"
                    />
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleUpload}
                    disabled={uploading}
                    className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    {uploading ? 'Uploading...' : 'Upload'}
                  </button>
                  <button
                    onClick={handleClearFile}
                    className="px-4 py-2 text-gray-500 text-sm hover:text-gray-700"
                  >
                    Cancel
                  </button>
                  <span className="text-xs text-gray-400">
                    Identifier and version are auto-detected from filename — adjust if needed
                  </span>
                </div>
              </>
            )}
          </div>

          {/* Reference docs list */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b">
              <h3 className="text-lg font-semibold">
                Reference Documents ({topLevelDocs.length})
              </h3>
            </div>

            {loading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto" />
              </div>
            ) : topLevelDocs.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No reference documents uploaded yet.
              </div>
            ) : (
              <div className="divide-y">
                {topLevelDocs.map(doc => (
                  <div key={doc.id} className="px-6 py-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <span className="font-medium text-sm text-gray-900">
                          {doc.doc_identifier || doc.filename}
                        </span>
                        {doc.version && (
                          <span className="text-xs bg-gray-100 px-2 py-0.5 rounded flex-shrink-0">{doc.version}</span>
                        )}
                        {doc.title && (
                          <span className="text-xs text-gray-500 truncate">{doc.title}</span>
                        )}
                        <span className={`text-xs flex-shrink-0 ${statusColors[doc.status]}`}>
                          {doc.status}
                        </span>
                        {doc.requirement_count > 0 && (
                          <span className="text-xs text-gray-400 flex-shrink-0">
                            {doc.requirement_count} req{doc.requirement_count !== 1 ? 's' : ''}
                          </span>
                        )}
                        {doc.children_count > 0 && (
                          <span className="text-xs text-purple-600 flex-shrink-0">
                            book ({doc.children_count} specs)
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0 ml-3">
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
                    <div className="text-xs text-gray-400 mt-0.5">{doc.filename}</div>
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
