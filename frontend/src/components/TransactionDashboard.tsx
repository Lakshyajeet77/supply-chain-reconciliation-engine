import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import type { DocumentRecord, ReconciliationResult } from '../api/types';
import { formatDocumentType } from '../api/types';

interface TransactionDashboardProps {
  documents: DocumentRecord[];
}

interface DocumentRelationship {
  id: string;
  po_id: string;
  invoice_id: string;
  delivery_id: string | null;
  status: 'SUGGESTED' | 'CONFIRMED';
  created_at: string;
  confirmed_at: string | null;
  confirmed_by: string | null;
}

export const TransactionDashboard: React.FC<TransactionDashboardProps> = ({ documents }) => {
  const [relationships, setRelationships] = useState<DocumentRelationship[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state for creating relationship
  const [selectedPoId, setSelectedPoId] = useState('');
  const [selectedInvoiceId, setSelectedInvoiceId] = useState('');
  const [selectedDeliveryId, setSelectedDeliveryId] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  // Reconciliation state for selected relationship
  const [reconciliationResults, setReconciliationResults] = useState<Record<string, ReconciliationResult>>({});
  const [reconciliationErrors, setReconciliationErrors] = useState<Record<string, string>>({});
  const [runningId, setRunningId] = useState<string | null>(null);

  const fetchRelationships = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/relationships');
      setRelationships(response.data);
      setError(null);
    } catch (err: any) {
      console.error('Error fetching relationships:', err);
      setError('Could not load relationships.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRelationships();
  }, [fetchRelationships]);

  const handleCreateRelationship = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPoId || !selectedInvoiceId) return;

    setIsCreating(true);
    setError(null);
    try {
      await apiClient.post('/relationships', {
        po_id: selectedPoId,
        invoice_id: selectedInvoiceId,
        delivery_id: selectedDeliveryId || null,
        status: 'SUGGESTED',
      });
      setSelectedPoId('');
      setSelectedInvoiceId('');
      setSelectedDeliveryId('');
      await fetchRelationships();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create relationship suggestion.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleConfirmRelationship = async (relationshipId: string) => {
    setError(null);
    try {
      await apiClient.post(`/relationships/${relationshipId}/confirm`, null, {
        params: { confirmed_by: 'dashboard-user' },
      });
      await fetchRelationships();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to confirm relationship.');
    }
  };

  const handleDeleteRelationship = async (relationshipId: string) => {
    setError(null);
    try {
      await apiClient.delete(`/relationships/${relationshipId}`);
      await fetchRelationships();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete relationship.');
    }
  };

  const handleRunApprovedReconciliation = async (rel: DocumentRelationship) => {
    setRunningId(rel.id);
    setReconciliationErrors((prev) => ({ ...prev, [rel.id]: '' }));
    try {
      const payload = {
        po_id: rel.po_id,
        invoice_id: rel.invoice_id,
        delivery: rel.delivery_id ? { id: rel.delivery_id } : null,
      };
      const response = await apiClient.post('/reconciliation/run-approved', payload);
      setReconciliationResults((prev) => ({ ...prev, [rel.id]: response.data }));
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.response?.data?.message || 'Approved reconciliation failed';
      setReconciliationErrors((prev) => ({ ...prev, [rel.id]: msg }));
    } finally {
      setRunningId(null);
    }
  };

  const purchaseOrders = documents.filter((d) => d.document_type === 'purchase_order');
  const invoices = documents.filter((d) => d.document_type === 'invoice');
  const deliveries = documents.filter((d) => d.document_type === 'delivery');

  const getDoc = (id: string | null) => documents.find((d) => d.id === id);

  const suggestedRels = relationships.filter((r) => r.status === 'SUGGESTED');
  const confirmedRels = relationships.filter((r) => r.status === 'CONFIRMED');

  return (
    <section style={{ padding: '1.5rem', border: '1px solid var(--border)', borderRadius: '12px', background: 'var(--social-bg)', marginBottom: '2rem', textAlign: 'left' }}>
      <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>Transaction Relationships & Reconciliation</h2>
      <p style={{ marginTop: 0, fontSize: '0.9rem', color: 'var(--text)' }}>
        Group Purchase Orders, Invoices, and Delivery Challans into transaction relationships, confirm them, and run approved reconciliations.
      </p>

      {error && <div style={{ color: '#ff4444', marginBottom: '1rem', fontSize: '0.9rem' }}>{error}</div>}

      {/* Suggest Relationship Form */}
      <form onSubmit={handleCreateRelationship} style={{ background: 'rgba(0,0,0,0.02)', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', border: '1px solid var(--border)' }}>
        <h3 style={{ fontSize: '1.1rem', marginBottom: '0.75rem' }}>Suggest Document Relationship</h3>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <label style={{ flex: 1, minWidth: '200px' }}>
            <span style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.25rem' }}>Purchase Order</span>
            <select
              value={selectedPoId}
              onChange={(e) => setSelectedPoId(e.target.value)}
              style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)' }}
              required
            >
              <option value="">— Select PO —</option>
              {purchaseOrders.map((po) => (
                <option key={po.id} value={po.id}>
                  {po.original_filename} ({po.extracted_data?.extracted?.po_number || 'No PO#'})
                </option>
              ))}
            </select>
          </label>

          <label style={{ flex: 1, minWidth: '200px' }}>
            <span style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.25rem' }}>Supplier Invoice</span>
            <select
              value={selectedInvoiceId}
              onChange={(e) => setSelectedInvoiceId(e.target.value)}
              style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)' }}
              required
            >
              <option value="">— Select Invoice (Multiple per PO allowed) —</option>
              {invoices.map((inv) => (
                <option key={inv.id} value={inv.id}>
                  {inv.original_filename} ({inv.extracted_data?.extracted?.invoice_number || 'No Inv#'})
                </option>
              ))}
            </select>
          </label>

          <label style={{ flex: 1, minWidth: '200px' }}>
            <span style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.25rem' }}>Delivery Challan (Optional)</span>
            <select
              value={selectedDeliveryId}
              onChange={(e) => setSelectedDeliveryId(e.target.value)}
              style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)' }}
            >
              <option value="">— none —</option>
              {deliveries.map((del) => (
                <option key={del.id} value={del.id}>
                  {del.original_filename} ({del.extracted_data?.extracted?.delivery_challan_number || 'No Challan#'})
                </option>
              ))}
            </select>
          </label>
        </div>
        <button
          type="submit"
          disabled={!selectedPoId || !selectedInvoiceId || isCreating}
          style={{
            padding: '0.5rem 1.25rem',
            background: 'var(--accent)',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: selectedPoId && selectedInvoiceId && !isCreating ? 'pointer' : 'not-allowed',
            opacity: selectedPoId && selectedInvoiceId && !isCreating ? 1 : 0.6,
            fontSize: '0.9rem',
          }}
        >
          {isCreating ? 'Suggesting...' : 'Suggest Relationship'}
        </button>
      </form>

      {/* Suggested Relationships Section */}
      <div style={{ marginBottom: '2rem' }}>
        <h3 style={{ fontSize: '1.2rem', marginBottom: '0.75rem' }}>Suggested Relationships ({suggestedRels.length})</h3>
        {suggestedRels.length === 0 ? (
          <p style={{ fontSize: '0.85rem', color: 'var(--text)' }}>No suggested relationships pending confirmation.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {suggestedRels.map((rel) => {
              const poDoc = getDoc(rel.po_id);
              const invDoc = getDoc(rel.invoice_id);
              const delDoc = getDoc(rel.delivery_id);
              return (
                <div key={rel.id} style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '1rem', background: 'rgba(180,83,9,0.04)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#b45309' }}>Status: SUGGESTED</span>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        onClick={() => handleConfirmRelationship(rel.id)}
                        style={{ padding: '0.3rem 0.8rem', background: '#15803d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}
                      >
                        Confirm Relationship
                      </button>
                      <button
                        onClick={() => handleDeleteRelationship(rel.id)}
                        style={{ padding: '0.3rem 0.8rem', background: '#b91c1c', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.5rem', fontSize: '0.85rem' }}>
                    <div><strong>PO:</strong> {poDoc?.original_filename || rel.po_id}</div>
                    <div><strong>Invoice:</strong> {invDoc?.original_filename || rel.invoice_id}</div>
                    <div><strong>Delivery:</strong> {delDoc ? delDoc.original_filename : 'None'}</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Confirmed Relationships & Reconciliation Section */}
      <div>
        <h3 style={{ fontSize: '1.2rem', marginBottom: '0.75rem' }}>Confirmed Relationships & Approved Reconciliation ({confirmedRels.length})</h3>
        {confirmedRels.length === 0 ? (
          <p style={{ fontSize: '0.85rem', color: 'var(--text)' }}>No confirmed relationships yet. Confirm suggested relationships above to enable approved reconciliation.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {confirmedRels.map((rel) => {
              const poDoc = getDoc(rel.po_id);
              const invDoc = getDoc(rel.invoice_id);
              const delDoc = getDoc(rel.delivery_id);
              const res = reconciliationResults[rel.id];
              const err = reconciliationErrors[rel.id];
              const isRunning = runningId === rel.id;

              return (
                <div key={rel.id} style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '1rem', background: 'rgba(21,128,61,0.04)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#15803d' }}>
                      Status: CONFIRMED (Confirmed by: {rel.confirmed_by || 'system'} at {rel.confirmed_at ? new Date(rel.confirmed_at).toLocaleString() : '—'})
                    </span>
                    <button
                      onClick={() => handleRunApprovedReconciliation(rel)}
                      disabled={isRunning}
                      style={{
                        padding: '0.4rem 1rem',
                        background: 'var(--accent)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: isRunning ? 'not-allowed' : 'pointer',
                        fontSize: '0.85rem',
                        opacity: isRunning ? 0.6 : 1,
                      }}
                    >
                      {isRunning ? 'Running Approved Recon...' : 'Run Approved Reconciliation'}
                    </button>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.5rem', fontSize: '0.85rem', marginBottom: '0.75rem' }}>
                    <div><strong>PO:</strong> {poDoc?.original_filename || rel.po_id}</div>
                    <div><strong>Invoice:</strong> {invDoc?.original_filename || rel.invoice_id}</div>
                    <div><strong>Delivery:</strong> {delDoc ? delDoc.original_filename : 'None'}</div>
                  </div>

                  {err && <div style={{ color: '#ff4444', fontSize: '0.85rem', marginBottom: '0.5rem' }}>{err}</div>}

                  {res && (
                    <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'white', borderRadius: '6px', border: '1px solid var(--border)' }}>
                      <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: '0.25rem' }}>
                        Reconciliation Result Status: <span style={{ color: res.status === 'matched' ? '#15803d' : '#b91c1c' }}>{res.status.toUpperCase()}</span>
                      </div>
                      {res.notes.length > 0 && (
                        <ul style={{ fontSize: '0.8rem', margin: '0.25rem 0', paddingLeft: '1rem' }}>
                          {res.notes.map((n, i) => (
                            <li key={i}>{n}</li>
                          ))}
                        </ul>
                      )}
                      {res.discrepancies.length > 0 ? (
                        <div style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>
                          <strong>Discrepancies ({res.discrepancies.length}):</strong>
                          <ul style={{ margin: '0.25rem 0', paddingLeft: '1rem' }}>
                            {res.discrepancies.map((d, i) => (
                              <li key={i}>
                                [{d.severity}] {d.field}: expected {d.expected || '—'}, observed {d.observed || '—'} ({d.explanation})
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : (
                        <div style={{ fontSize: '0.8rem', color: '#15803d', marginTop: '0.25rem' }}>No discrepancies found.</div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
};
