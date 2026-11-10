import { useEffect, useState, useCallback } from 'react';
import apiClient from './api/client';
import { DashboardOverview } from './components/DashboardOverview';
import { DocumentUpload } from './components/DocumentUpload';
import { DocumentDetail } from './components/DocumentDetail';
import { ReconciliationPanel } from './components/ReconciliationPanel';
import { TransactionDashboard } from './components/TransactionDashboard';
import type { DocumentRecord } from './api/types';
import { formatDocumentType } from './api/types';
import './index.css';

function App() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      const response = await apiClient.get('/documents');
      setDocuments(response.data.documents);
      setLoadError(null);
    } catch (error) {
      console.error('Error fetching documents:', error);
      setLoadError('Could not load documents. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const getStatusCounts = () => {
    const counts: { [key: string]: number } = {};
    documents.forEach(doc => {
      counts[doc.processing_status] = (counts[doc.processing_status] || 0) + 1;
    });
    return counts;
  };

  return (
    <div id="root" style={{ padding: '2rem' }}>
      <h1>Supply Chain Dashboard</h1>

      <DashboardOverview totalDocs={documents.length} statusCounts={getStatusCounts()} />

      <DocumentUpload onUploadSuccess={fetchDocuments} />

      <TransactionDashboard documents={documents} />

      <ReconciliationPanel documents={documents} />

      <section>
        <h2>Recent Documents</h2>
        {loading ? <p>Loading…</p> : loadError ? (
          <p style={{ color: '#ff4444' }}>{loadError}</p>
        ) : documents.length === 0 ? (
          <p style={{ color: 'var(--text)' }}>No documents uploaded yet.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border)' }}>
                <th style={{ padding: '0.5rem', textAlign: 'left' }}>Filename</th>
                <th style={{ padding: '0.5rem', textAlign: 'left' }}>Type</th>
                <th style={{ padding: '0.5rem', textAlign: 'left' }}>Status</th>
                <th style={{ padding: '0.5rem', textAlign: 'left' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {documents.map(doc => (
                <tr key={doc.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '0.5rem' }}>{doc.original_filename}</td>
                  <td style={{ padding: '0.5rem', textTransform: 'capitalize' }}>{formatDocumentType(doc.document_type)}</td>
                  <td style={{ padding: '0.5rem', textTransform: 'capitalize' }}>{doc.processing_status.replace('_', ' ')}</td>
                  <td style={{ padding: '0.5rem' }}>
                    <button onClick={() => setSelectedId(doc.id)}>View Details</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {selectedId && (
        <DocumentDetail
          documentId={selectedId}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}

export default App;
