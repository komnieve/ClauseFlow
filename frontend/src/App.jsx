import { useState, useEffect } from 'react';
import DocumentUpload from './components/DocumentUpload';
import ClauseCard from './components/ClauseCard';
import ProgressBar from './components/ProgressBar';
import { getDocuments, getDocument, exportDocument } from './api/client';

function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [clauses, setClauses] = useState([]);
  const [currentClauseIndex, setCurrentClauseIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('home'); // home, review, list
  const [filter, setFilter] = useState('all'); // all, clause, unreviewed, flagged

  // Load documents on mount
  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  const handleUploadComplete = async (result) => {
    // Poll for processing completion
    const pollInterval = setInterval(async () => {
      const docs = await getDocuments();
      setDocuments(docs);

      const doc = docs.find(d => d.id === result.document_id);
      if (doc && doc.status === 'ready') {
        clearInterval(pollInterval);
        selectDocument(doc.id);
      } else if (doc && doc.status === 'error') {
        clearInterval(pollInterval);
        alert('Processing failed: ' + doc.error_message);
      }
    }, 2000);
  };

  const selectDocument = async (documentId) => {
    setLoading(true);
    try {
      const doc = await getDocument(documentId);
      setSelectedDocument(doc);
      setClauses(doc.clauses);
      setCurrentClauseIndex(0);
      setView('review');
    } catch (err) {
      console.error('Failed to load document:', err);
    }
    setLoading(false);
  };

  const handleClauseUpdate = (updatedClause) => {
    setClauses(clauses.map(c => c.id === updatedClause.id ? updatedClause : c));

    // Update document stats
    if (selectedDocument) {
      const reviewed = clauses.filter(c =>
        c.id === updatedClause.id ? updatedClause.review_status === 'reviewed' : c.review_status === 'reviewed'
      ).length;
      const flagged = clauses.filter(c =>
        c.id === updatedClause.id ? updatedClause.review_status === 'flagged' : c.review_status === 'flagged'
      ).length;
      setSelectedDocument({
        ...selectedDocument,
        reviewed_count: reviewed,
        flagged_count: flagged,
      });
    }
  };

  const handleExport = async (format) => {
    if (!selectedDocument) return;

    try {
      if (format === 'csv') {
        const blob = await exportDocument(selectedDocument.id, 'csv');
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${selectedDocument.filename}_clauses.csv`;
        a.click();
      } else {
        const data = await exportDocument(selectedDocument.id, 'json');
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${selectedDocument.filename}_clauses.json`;
        a.click();
      }
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  // Filter clauses based on current filter
  const filteredClauses = clauses.filter(c => {
    if (filter === 'all') return true;
    if (filter === 'clause') return c.chunk_type === 'clause';
    if (filter === 'unreviewed') return c.review_status === 'unreviewed';
    if (filter === 'flagged') return c.review_status === 'flagged';
    return true;
  });

  const currentClause = filteredClauses[currentClauseIndex];

  // Stats
  const stats = {
    reviewed: clauses.filter(c => c.review_status === 'reviewed').length,
    flagged: clauses.filter(c => c.review_status === 'flagged').length,
    total: clauses.length,
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1
            className="text-2xl font-bold text-gray-900 cursor-pointer"
            onClick={() => { setView('home'); setSelectedDocument(null); }}
          >
            ClauseFlow
          </h1>

          {selectedDocument && (
            <div className="flex items-center gap-4">
              <span className="text-gray-600">{selectedDocument.filename}</span>
              <div className="flex gap-2">
                <button
                  onClick={() => handleExport('json')}
                  className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
                >
                  Export JSON
                </button>
                <button
                  onClick={() => handleExport('csv')}
                  className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
                >
                  Export CSV
                </button>
              </div>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Home View */}
        {view === 'home' && (
          <div>
            <div className="mb-8">
              <DocumentUpload onUploadComplete={handleUploadComplete} />
            </div>

            {documents.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold mb-4">Recent Documents</h2>
                <div className="grid gap-4">
                  {documents.map(doc => (
                    <div
                      key={doc.id}
                      className="bg-white rounded-lg shadow p-4 flex justify-between items-center hover:shadow-md cursor-pointer"
                      onClick={() => doc.status === 'ready' && selectDocument(doc.id)}
                    >
                      <div>
                        <div className="font-medium">{doc.filename}</div>
                        <div className="text-sm text-gray-500">
                          {doc.clause_count} clauses | {doc.reviewed_count} reviewed
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {doc.status === 'processing' && (
                          <span className="text-yellow-600 text-sm">Processing...</span>
                        )}
                        {doc.status === 'ready' && (
                          <span className="text-green-600 text-sm">Ready</span>
                        )}
                        {doc.status === 'error' && (
                          <span className="text-red-600 text-sm">Error</span>
                        )}
                        {doc.status === 'ready' && (
                          <button className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
                            Review
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Review View */}
        {view === 'review' && selectedDocument && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Sidebar */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-lg shadow p-4 sticky top-4">
                <h3 className="font-semibold mb-4">Progress</h3>
                <ProgressBar
                  reviewed={stats.reviewed}
                  flagged={stats.flagged}
                  total={stats.total}
                />

                <div className="mt-6">
                  <h3 className="font-semibold mb-2">Filter</h3>
                  <div className="flex flex-col gap-2">
                    {[
                      { value: 'all', label: `All (${clauses.length})` },
                      { value: 'clause', label: `Clauses (${clauses.filter(c => c.chunk_type === 'clause').length})` },
                      { value: 'unreviewed', label: `Unreviewed (${clauses.filter(c => c.review_status === 'unreviewed').length})` },
                      { value: 'flagged', label: `Flagged (${clauses.filter(c => c.review_status === 'flagged').length})` },
                    ].map(option => (
                      <button
                        key={option.value}
                        onClick={() => { setFilter(option.value); setCurrentClauseIndex(0); }}
                        className={`text-left px-3 py-2 rounded text-sm ${
                          filter === option.value
                            ? 'bg-blue-100 text-blue-800'
                            : 'hover:bg-gray-100'
                        }`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="mt-6">
                  <button
                    onClick={() => setView('list')}
                    className="w-full px-3 py-2 text-sm border rounded hover:bg-gray-50"
                  >
                    View as List
                  </button>
                </div>
              </div>
            </div>

            {/* Main content */}
            <div className="lg:col-span-3">
              {loading ? (
                <div className="text-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
                </div>
              ) : currentClause ? (
                <ClauseCard
                  key={currentClause.id}
                  clause={currentClause}
                  onUpdate={handleClauseUpdate}
                  onNext={() => setCurrentClauseIndex(Math.min(currentClauseIndex + 1, filteredClauses.length - 1))}
                  onPrev={() => setCurrentClauseIndex(Math.max(currentClauseIndex - 1, 0))}
                  currentIndex={currentClauseIndex}
                  totalCount={filteredClauses.length}
                />
              ) : (
                <div className="text-center py-12 text-gray-500">
                  No clauses match the current filter.
                </div>
              )}
            </div>
          </div>
        )}

        {/* List View */}
        {view === 'list' && selectedDocument && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">All Clauses</h2>
              <button
                onClick={() => setView('review')}
                className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
              >
                Back to Review
              </button>
            </div>

            <div className="bg-white rounded-lg shadow overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Lines</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Clause</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Type</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Scope</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {clauses.map((clause, index) => (
                    <tr
                      key={clause.id}
                      className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => { setCurrentClauseIndex(index); setView('review'); setFilter('all'); }}
                    >
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {clause.start_line}-{clause.end_line}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {clause.clause_number || '-'}
                        {clause.clause_title && ` - ${clause.clause_title}`}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{clause.chunk_type}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{clause.scope || '-'}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded text-xs ${
                          clause.review_status === 'reviewed' ? 'bg-green-100 text-green-800' :
                          clause.review_status === 'flagged' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {clause.review_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
