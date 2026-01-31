/**
 * API client for ClauseFlow backend
 */

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:9847') + '/api';

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Upload failed');
  }

  return response.json();
}

export async function getDocuments() {
  const response = await fetch(`${API_BASE}/documents`);
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
