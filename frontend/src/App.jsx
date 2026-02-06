import { useState, useEffect, useCallback, useRef } from 'react';
import DocumentUpload from './components/DocumentUpload';
import DocumentOverview from './components/DocumentOverview';
import ReviewView from './components/ReviewView';
import ClauseListView from './components/ClauseListView';
import ReferenceLibrary from './components/ReferenceLibrary';
import ReferenceDocDetail from './components/ReferenceDocDetail';
import { getDocuments, getDocument, exportDocument, reprocessDocument, matchDocumentReferences, getDocumentRawUrl, deleteDocument } from './api/client';

function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [clauses, setClauses] = useState([]);
  const [sections, setSections] = useState([]);
  const [lineItems, setLineItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('home'); // home, overview, review, list, library, ref-doc-detail
  const [selectedRefDocId, setSelectedRefDocId] = useState(null);
  const skipPushRef = useRef(false);

  // Push browser history when view changes
  const navigate = useCallback((newView, docId = null) => {
    if (!skipPushRef.current) {
      history.pushState({ view: newView, docId }, '', `#${newView}${docId ? `/${docId}` : ''}`);
    }
    skipPushRef.current = false;
  }, []);

  // Store ref to selectedDocument for popstate handler (avoids stale closure)
  const selectedDocRef = useRef(null);
  selectedDocRef.current = selectedDocument;

  // Listen for browser back/forward
  useEffect(() => {
    const handlePopState = async (e) => {
      const state = e.state;
      if (!state) {
        setView('home');
        setSelectedDocument(null);
        setClauses([]);
        setSections([]);
        setLineItems([]);
        return;
      }
      skipPushRef.current = true;
      if (state.view === 'home' || state.view === 'library') {
        setView(state.view);
        setSelectedDocument(null);
        setClauses([]);
        setSections([]);
        setLineItems([]);
      } else if (state.docId && (state.view === 'overview' || state.view === 'review' || state.view === 'list')) {
        if (selectedDocRef.current?.id === state.docId) {
          setView(state.view);
        } else {
          try {
            const doc = await getDocument(state.docId);
            setSelectedDocument(doc);
            setClauses(doc.clauses || []);
            setSections(doc.sections || []);
            setLineItems(doc.line_items || []);
            setView(state.view);
          } catch (err) {
            console.error('Failed to load document:', err);
            setView('home');
          }
        }
      }
    };

    window.addEventListener('popstate', handlePopState);
    history.replaceState({ view: 'home' }, '', '#home');
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

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
      setClauses(doc.clauses || []);
      setSections(doc.sections || []);
      setLineItems(doc.line_items || []);
      setView('overview');
      navigate('overview', doc.id);
    } catch (err) {
      console.error('Failed to load document:', err);
    }
    setLoading(false);
  };

  const handleClauseUpdate = (updatedClause) => {
    setClauses(prev => prev.map(c => c.id === updatedClause.id ? updatedClause : c));
  };

  const handleExport = async (format) => {
    if (!selectedDocument) return;

    // Gated export: confirm if not all addressed
    const allAddressed = clauses.length > 0 && clauses.every(
      c => c.review_status === 'reviewed' || c.review_status === 'flagged'
    );
    if (!allAddressed) {
      const ok = confirm('Not all clauses have been reviewed or flagged. Export anyway?');
      if (!ok) return;
    }

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

  const handleReprocess = async () => {
    if (!selectedDocument) return;
    const ok = confirm('This will re-run extraction and reset all review progress. Continue?');
    if (!ok) return;

    try {
      const result = await reprocessDocument(selectedDocument.id);
      // Go back to home and start polling like a fresh upload
      setView('home');
      setSelectedDocument(null);
      setClauses([]);
      setSections([]);
      setLineItems([]);
      navigate('home');
      handleUploadComplete(result);
    } catch (err) {
      alert('Re-extract failed: ' + err.message);
    }
  };

  const handleSelectClauseFromList = (clause, index) => {
    setView('review');
    navigate('review', selectedDocument?.id);
  };

  const handleDeleteDocument = async (docId, e) => {
    e.stopPropagation();
    if (!confirm('Delete this document and all its clauses?')) return;
    try {
      await deleteDocument(docId);
      setDocuments(prev => prev.filter(d => d.id !== docId));
      if (selectedDocument?.id === docId) {
        setSelectedDocument(null);
        setClauses([]);
        setSections([]);
        setLineItems([]);
        setView('home');
      }
    } catch (err) {
      alert('Delete failed: ' + err.message);
    }
  };

  const handleNavigateToLibrary = () => {
    setView('library');
    navigate('library');
  };

  const handleViewRefDoc = (refDocId) => {
    setSelectedRefDocId(refDocId);
    setView('ref-doc-detail');
    navigate('ref-doc-detail');
  };

  const getStatusDisplay = (status) => {
    switch (status) {
      case 'processing': return { text: 'Processing...', className: 'text-yellow-600' };
      case 'segmenting': return { text: 'Segmenting...', className: 'text-yellow-600' };
      case 'extracting': return { text: 'Extracting clauses...', className: 'text-yellow-600' };
      case 'matching': return { text: 'Matching references...', className: 'text-yellow-600' };
      case 'ready': return { text: 'Ready', className: 'text-green-600' };
      case 'error': return { text: 'Error', className: 'text-red-600' };
      default: return { text: status, className: 'text-gray-600' };
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-6">
            <h1
              className="text-2xl font-bold text-gray-900 cursor-pointer"
              onClick={() => { setView('home'); setSelectedDocument(null); setClauses([]); setSections([]); setLineItems([]); navigate('home'); }}
            >
              ClauseFlow
            </h1>
            <nav className="flex gap-4">
              <button
                onClick={() => { setView('home'); setSelectedDocument(null); setClauses([]); setSections([]); setLineItems([]); navigate('home'); }}
                className={`text-sm font-medium ${view === 'home' ? 'text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
              >
                Documents
              </button>
              <button
                onClick={handleNavigateToLibrary}
                className={`text-sm font-medium ${view === 'library' || view === 'ref-doc-detail' ? 'text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
              >
                Reference Library
              </button>
            </nav>
          </div>

          {selectedDocument && view === 'review' && (
            <div className="flex items-center gap-4">
              <a
                href={getDocumentRawUrl(selectedDocument.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-600 hover:text-blue-600 hover:underline"
                title="View original document"
              >{selectedDocument.filename}</a>
              {selectedDocument.customer_name && (
                <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs font-medium rounded">
                  {selectedDocument.customer_name}
                </span>
              )}
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
                  {documents.map(doc => {
                    const status = getStatusDisplay(doc.status);
                    const isClickable = doc.status === 'ready';
                    return (
                      <div
                        key={doc.id}
                        className={`bg-white rounded-lg shadow p-4 flex justify-between items-center ${isClickable ? 'hover:shadow-md cursor-pointer' : ''}`}
                        onClick={() => isClickable && selectDocument(doc.id)}
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <a
                              href={getDocumentRawUrl(doc.id)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-medium text-blue-700 hover:underline"
                              title="View original document"
                              onClick={(e) => e.stopPropagation()}
                            >{doc.filename}</a>
                            {doc.customer_name && (
                              <span className="px-2 py-0.5 bg-purple-100 text-purple-800 text-xs rounded">
                                {doc.customer_name}
                              </span>
                            )}
                          </div>
                          <div className="text-sm text-gray-500">
                            {doc.clause_count} clauses | {doc.reviewed_count} reviewed
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`text-sm ${status.className}`}>{status.text}</span>
                          {isClickable && (
                            <button className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
                              Review
                            </button>
                          )}
                          <button
                            onClick={(e) => handleDeleteDocument(doc.id, e)}
                            className="px-3 py-2 text-red-500 text-sm hover:text-red-700"
                            title="Delete document"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Overview View */}
        {view === 'overview' && selectedDocument && (
          <DocumentOverview
            document={selectedDocument}
            clauses={clauses}
            sections={sections}
            lineItems={lineItems}
            onStartReview={() => { setView('review'); navigate('review', selectedDocument.id); }}
            onReprocess={handleReprocess}
            onBack={() => { setView('home'); setSelectedDocument(null); setClauses([]); setSections([]); setLineItems([]); navigate('home'); }}
          />
        )}

        {/* Review View */}
        {view === 'review' && selectedDocument && (
          <ReviewView
            clauses={clauses}
            sections={sections}
            lineItems={lineItems}
            loading={loading}
            onClauseUpdate={handleClauseUpdate}
            onViewList={() => { setView('list'); navigate('list', selectedDocument.id); }}
            onExport={handleExport}
            onNavigateToLibrary={handleNavigateToLibrary}
          />
        )}

        {/* List View */}
        {view === 'list' && selectedDocument && (
          <ClauseListView
            clauses={clauses}
            sections={sections}
            onSelectClause={handleSelectClauseFromList}
            onBackToReview={() => { setView('review'); navigate('review', selectedDocument.id); }}
          />
        )}

        {/* Reference Library View */}
        {view === 'library' && (
          <ReferenceLibrary
            onViewRefDoc={handleViewRefDoc}
            onBack={() => { setView('home'); navigate('home'); }}
          />
        )}

        {/* Reference Doc Detail View */}
        {view === 'ref-doc-detail' && selectedRefDocId && (
          <ReferenceDocDetail
            refDocId={selectedRefDocId}
            onBack={() => { setView('library'); navigate('library'); }}
          />
        )}
      </main>
    </div>
  );
}

export default App;
