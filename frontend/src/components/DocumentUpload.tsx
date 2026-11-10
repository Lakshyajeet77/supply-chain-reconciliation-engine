import React, { useState } from 'react';
import apiClient from '../api/client';

interface UploadProps {
  onUploadSuccess: () => void;
}

export const DocumentUpload: React.FC<UploadProps> = ({ onUploadSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState('invoice');
  const [fixtureId, setFixtureId] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', docType);
    if (fixtureId) {
      formData.append('fixture_id', fixtureId);
    }

    try {
      await apiClient.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setFile(null);
      setFixtureId('');
      onUploadSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail?.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <section style={{ padding: '1.5rem', border: '1px solid var(--border)', borderRadius: '12px', background: 'var(--social-bg)', marginBottom: '2rem', textAlign: 'left' }}>
      <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>Upload Document</h2>
      <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <select value={docType} onChange={(e) => setDocType(e.target.value)} style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)' }}>
            <option value="invoice">Invoice</option>
            <option value="purchase_order">Purchase Order</option>
            <option value="delivery">Delivery Challan</option>
          </select>
          <input
            type="text"
            placeholder="Fixture ID (optional)"
            value={fixtureId}
            onChange={(e) => setFixtureId(e.target.value)}
            style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)', flex: '1' }}
          />
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            style={{ padding: '0.5rem', border: '1px solid var(--border)', borderRadius: '4px', flex: '1' }}
          />
          <button
            type="submit"
            disabled={!file || isUploading}
            style={{
              padding: '0.6rem 1.5rem',
              background: 'var(--accent)',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: file && !isUploading ? 'pointer' : 'not-allowed',
              opacity: file && !isUploading ? 1 : 0.6
            }}
          >
            {isUploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
        {error && <p style={{ color: '#ff4444', fontSize: '0.9rem', margin: 0 }}>{error}</p>}
      </form>
    </section>
  );
};
