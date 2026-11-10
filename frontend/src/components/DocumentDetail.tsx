import React, { useEffect, useState } from 'react';
import apiClient from '../api/client';
import type { DocumentRecord, FieldConfidence } from '../api/types';
import { formatDocumentType, formatScore } from '../api/types';

export const DocumentDetail: React.FC<{ documentId: string; onClose: () => void }> = ({ documentId, onClose }) => {
  const [doc, setDoc] = useState<DocumentRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setDoc(null);
    setError(null);
    setPreviewError(null);
    apiClient
      .get<DocumentRecord>(`/documents/${documentId}`)
      .then((res) => {
        if (!cancelled) setDoc(res.data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err.response?.status === 404
              ? 'Document not found.'
              : 'Could not load document details. Is the backend running?',
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  if (error) {
    return (
      <Modal>
        <p style={{ color: '#ff4444' }}>{error}</p>
      </Modal>
    );
  }
  if (!doc) {
    return (
      <Modal>
        <p>Loading…</p>
      </Modal>
    );
  }

  const previewUrl = apiClient.defaults.baseURL
    ? `${apiClient.defaults.baseURL}/documents/${doc.id}/file`
    : `/api/documents/${doc.id}/file`;

  const confidence = doc.extracted_data?.confidence;
  const fields: [string, FieldConfidence][] = Object.entries(confidence?.fields ?? {});

  return (
    <Modal>
      <button onClick={onClose} style={{ marginBottom: '1rem' }}>Close</button>
      <h2 style={{ marginTop: 0 }}>{doc.original_filename}</h2>
      <p>
        Type: <strong>{formatDocumentType(doc.document_type)}</strong> · Status:{' '}
        <strong>{doc.processing_status.replace('_', ' ')}</strong>
        {doc.failure_reason && <> · <span style={{ color: '#ff4444' }}>Failure: {doc.failure_reason}</span></>}
      </p>

      <h3>Preview</h3>
      {doc.content_type === 'application/pdf' ? (
        previewError ? (
          <p style={{ color: '#ff4444', fontSize: '0.9rem' }}>Preview unavailable ({previewError}).</p>
        ) : (
          <object
            data={previewUrl}
            type="application/pdf"
            style={{ width: '100%', height: '480px', border: '1px solid var(--border)', borderRadius: '8px' }}
            onError={() => setPreviewError('browser cannot render PDF')}
          >
            <p>
              Inline PDF preview not supported here —{' '}
              <a href={previewUrl} target="_blank" rel="noreferrer">open the file</a>.
            </p>
          </object>
        )
      ) : doc.content_type.startsWith('image/') ? (
        previewError ? (
          <p style={{ color: '#ff4444', fontSize: '0.9rem' }}>Preview unavailable ({previewError}).</p>
        ) : (
          <img
            src={previewUrl}
            alt={`Preview of ${doc.original_filename}`}
            style={{ maxWidth: '100%', maxHeight: '480px', border: '1px solid var(--border)', borderRadius: '8px' }}
            onError={() => setPreviewError('file could not be loaded')}
          />
        )
      ) : (
        <p style={{ color: 'var(--text)', fontSize: '0.9rem' }}>
          Preview not supported for {doc.content_type}.{' '}
          <a href={previewUrl} target="_blank" rel="noreferrer">Download the file</a>.
        </p>
      )}

      {doc.extracted_data && confidence && (
        <>
          <h3>Extraction Data</h3>
          <pre style={{ background: 'var(--code-bg)', padding: '1rem', overflowX: 'auto', borderRadius: '8px' }}>
            {JSON.stringify(doc.extracted_data.extracted, null, 2)}
          </pre>

          <h3>
            Confidence (Overall: {formatScore(confidence.overall_score)})
          </h3>
          {fields.length === 0 ? (
            <p style={{ color: 'var(--text)' }}>No field-level confidence recorded.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border)' }}>
                  <th style={{ padding: '0.5rem', textAlign: 'left' }}>Field</th>
                  <th style={{ padding: '0.5rem', textAlign: 'left' }}>Status</th>
                  <th style={{ padding: '0.5rem', textAlign: 'left' }}>Score</th>
                </tr>
              </thead>
              <tbody>
                {fields.map(([field, conf]) => (
                  <tr key={field} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '0.5rem', fontFamily: 'var(--mono)' }}>{field}</td>
                    <td style={{ padding: '0.5rem' }}>{conf.status}</td>
                    <td style={{ padding: '0.5rem' }}>{formatScore(conf.score)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </Modal>
  );
};

const Modal: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', padding: '2rem', overflowY: 'auto', zIndex: 10 }}>
    <div style={{ background: 'var(--bg)', padding: '2rem', borderRadius: '12px', maxWidth: '1000px', margin: 'auto', color: 'var(--text-h)' }}>
      {children}
    </div>
  </div>
);
