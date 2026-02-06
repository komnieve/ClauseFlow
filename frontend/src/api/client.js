/**
 * API client for ClauseFlow backend
 */

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:9847') + '/api';

export async function uploadDocument(file, customerId = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (customerId) {
    formData.append('customer_id', customerId);
  }

  const response = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Upload failed');
  }

  return response.json();
}

export async function getDocuments(customerId = null) {
  const params = new URLSearchParams();
  if (customerId) params.append('customer_id', customerId);
  const response = await fetch(`${API_BASE}/documents?${params}`);
  if (!response.ok) {
    throw new Error('Failed to fetch documents');
  }
  return response.json();
}

export async function getDocument(id) {
  const response = await fetch(`${API_BASE}/documents/${id}`);
  if (!response.ok) {
    throw new Error('Failed to fetch document');
  }
  return response.json();
}

export function getDocumentRawUrl(id) {
  return `${API_BASE}/documents/${id}/raw`;
}

export async function getDocumentStats(id) {
  const response = await fetch(`${API_BASE}/documents/${id}/stats`);
  if (!response.ok) {
    throw new Error('Failed to fetch stats');
  }
  return response.json();
}

export async function getClauses(documentId, filters = {}) {
  const params = new URLSearchParams();
  if (filters.chunk_type) params.append('chunk_type', filters.chunk_type);
  if (filters.review_status) params.append('review_status', filters.review_status);
  if (filters.scope_type) params.append('scope_type', filters.scope_type);
  if (filters.section_id) params.append('section_id', filters.section_id);

  const url = `${API_BASE}/documents/${documentId}/clauses?${params}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error('Failed to fetch clauses');
  }
  return response.json();
}

export async function updateClause(clauseId, updates) {
  const response = await fetch(`${API_BASE}/clauses/${clauseId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  });

  if (!response.ok) {
    throw new Error('Failed to update clause');
  }

  return response.json();
}

export async function markClauseReviewed(clauseId) {
  const response = await fetch(`${API_BASE}/clauses/${clauseId}/mark-reviewed`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('Failed to mark clause reviewed');
  }

  return response.json();
}

export async function flagClause(clauseId) {
  const response = await fetch(`${API_BASE}/clauses/${clauseId}/flag`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('Failed to flag clause');
  }

  return response.json();
}

export async function exportDocument(documentId, format = 'json') {
  const response = await fetch(`${API_BASE}/documents/${documentId}/export?format=${format}`);
  if (!response.ok) {
    throw new Error('Failed to export document');
  }

  if (format === 'csv') {
    return response.blob();
  }

  return response.json();
}

export async function deleteDocument(documentId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete document');
  }
  return response.json();
}

export async function reprocessDocument(documentId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}/reprocess`, {
    method: 'POST',
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to reprocess document');
  }

  return response.json();
}

// --- V2: Section and Line Item endpoints ---

export async function getSections(documentId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}/sections`);
  if (!response.ok) {
    throw new Error('Failed to fetch sections');
  }
  return response.json();
}

export async function getLineItems(documentId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}/line-items`);
  if (!response.ok) {
    throw new Error('Failed to fetch line items');
  }
  return response.json();
}

// --- V3: Customer endpoints ---

export async function getCustomers() {
  const response = await fetch(`${API_BASE}/customers`);
  if (!response.ok) {
    throw new Error('Failed to fetch customers');
  }
  return response.json();
}

export async function createCustomer(name) {
  const response = await fetch(`${API_BASE}/customers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create customer');
  }
  return response.json();
}

export async function deleteCustomer(customerId) {
  const response = await fetch(`${API_BASE}/customers/${customerId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete customer');
  }
  return response.json();
}

// --- V3: Reference document endpoints ---

export async function getCustomerReferenceDocs(customerId) {
  const response = await fetch(`${API_BASE}/customers/${customerId}/reference-docs`);
  if (!response.ok) {
    throw new Error('Failed to fetch reference docs');
  }
  return response.json();
}

export async function uploadReferenceDoc(customerId, file, docIdentifier = null, version = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (docIdentifier) formData.append('doc_identifier', docIdentifier);
  if (version) formData.append('version', version);

  const response = await fetch(`${API_BASE}/customers/${customerId}/reference-docs/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to upload reference doc');
  }

  return response.json();
}

export async function getReferenceDoc(refDocId) {
  const response = await fetch(`${API_BASE}/reference-docs/${refDocId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch reference doc');
  }
  return response.json();
}

export async function deleteReferenceDoc(refDocId) {
  const response = await fetch(`${API_BASE}/reference-docs/${refDocId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete reference doc');
  }
  return response.json();
}

// --- V3: Reference matching endpoints ---

export async function matchDocumentReferences(documentId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}/match-references`, {
    method: 'POST',
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to match references');
  }
  return response.json();
}

export async function getDocumentReferences(documentId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}/references`);
  if (!response.ok) {
    throw new Error('Failed to fetch references');
  }
  return response.json();
}

export async function getUnresolvedReferences(documentId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}/unresolved-references`);
  if (!response.ok) {
    throw new Error('Failed to fetch unresolved references');
  }
  return response.json();
}
