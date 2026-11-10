import React, { useMemo, useState } from 'react';
import apiClient from '../api/client';
import type { DocumentRecord, ReconciliationResult, LineItemMatch, MatchType } from '../api/types';
import { formatDocumentType, formatScore } from '../api/types';

interface ReconciliationPanelProps {
  documents: DocumentRecord[];
}

type Role = 'purchase_order' | 'delivery' | 'invoice';

const ROLE_LABELS: Record<Role, string> = {
  purchase_order: 'Purchase Order',
  delivery: 'Delivery Challan',
  invoice: 'Supplier Invoice',
};

const SEVERITY_ORDER = ['critical', 'error', 'warning', 'info'] as const;

const STATUS_STYLES: Record<ReconciliationResult['status'], { label: string; color: string; bg: string }> = {
  matched: { label: 'MATCHED', color: '#15803d', bg: 'rgba(21,128,61,0.12)' },
  flagged: { label: 'FLAGGED', color: '#b45309', bg: 'rgba(180,83,9,0.12)' },
  needs_human_review: { label: 'NEEDS HUMAN REVIEW', color: '#b91c1c', bg: 'rgba(185,28,28,0.12)' },
};

const MATCH_TYPE_LABELS: Record<MatchType, { label: string; color: string; bg: string }> = {
  exact_sku: { label: 'Verified', color: '#15803d', bg: 'rgba(21,128,61,0.12)' },
  exact_description: { label: 'Verified', color: '#15803d', bg: 'rgba(21,128,61,0.12)' },
  fuzzy_description: { label: 'Review Required', color: '#b45309', bg: 'rgba(180,83,9,0.12)' },
  unmatched: { label: "Documents Don't Match", color: '#b91c1c', bg: 'rgba(185,28,28,0.12)' },
};

export const ReconciliationPanel: React.FC<ReconciliationPanelProps> = ({ documents }) => {
  const [selected, setSelected] = useState<Record<Role, string>>({
    purchase_order: '',
    delivery: '',
    invoice: '',
  });
  const [result, setResult] = useState<ReconciliationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  // Only extracted documents carry structured payloads the engine can consume.
  const extractedByRole = useMemo(() => {
    const byRole: Record<Role, DocumentRecord[]> = {
      purchase_order: [],
      delivery: [],
      invoice: [],
    };
    for (const doc of documents) {
      if (doc.extracted_data?.extracted) {
        byRole[doc.document_type].push(doc);
      }
    }
    return byRole;
  }, [documents]);

  const handleChange = (role: Role, value: string) => {
    setSelected((prev) => ({ ...prev, [role]: value }));
    setResult(null);
    setError(null);
  };

  const canRun = Boolean(selected.invoice && selected.purchase_order);

  const handleRun = async () => {
    setIsRunning(true);
    setError(null);
    setResult(null);
    try {
      const payload = {
        purchase_order: selected.purchase_order
          ? documents.find((d) => d.id === selected.purchase_order)?.extracted_data?.extracted ?? null
          : null,
        delivery: selected.delivery
          ? documents.find((d) => d.id === selected.delivery)?.extracted_data?.extracted ?? null
          : null,
        invoice: selected.invoice
          ? documents.find((d) => d.id === selected.invoice)?.extracted_data?.extracted ?? null
          : null,
      };
      const response = await apiClient.post('/reconciliation/run', payload);
      setResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail?.message || err.response?.data?.message || 'Reconciliation failed');
    } finally {
      setIsRunning(false);
    }
  };

  const sortedDiscrepancies = result
    ? [...result.discrepancies].sort(
        (a, b) => SEVERITY_ORDER.indexOf(a.severity as any) - SEVERITY_ORDER.indexOf(b.severity as any),
      )
    : [];

  return (
    <section style={{ padding: '1.5rem', border: '1px solid var(--border)', borderRadius: '12px', background: 'var(--social-bg)', marginBottom: '2rem', textAlign: 'left' }}>
      <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>Reconciliation</h2>
      <p style={{ marginTop: 0, fontSize: '0.9rem', color: 'var(--text)' }}>
        Select one extracted document per role. A purchase order and an invoice are required
        for MATCHED. All matching decisions are computed by the backend engine.
      </p>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        {(Object.keys(ROLE_LABELS) as Role[]).map((role) => (
          <label key={role} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', flex: '1', minWidth: '220px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>
              {ROLE_LABELS[role]}
              {role === 'delivery' && <em style={{ fontWeight: 400 }}> (optional)</em>}
            </span>
            <select
              value={selected[role]}
              onChange={(e) => handleChange(role, e.target.value)}
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)' }}
            >
              <option value="">— none —</option>
              {extractedByRole[role].map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.original_filename} ({formatDocumentType(doc.document_type)})
                </option>
              ))}
            </select>
            {extractedByRole[role].length === 0 && (
              <span style={{ fontSize: '0.75rem', color: 'var(--text)' }}>No extracted {ROLE_LABELS[role].toLowerCase()} available.</span>
            )}
          </label>
        ))}
      </div>
      <button
        onClick={handleRun}
        disabled={!canRun || isRunning}
        style={{
          padding: '0.6rem 1.5rem',
          background: 'var(--accent)',
          color: 'white',
          border: 'none',
          borderRadius: '6px',
          cursor: canRun && !isRunning ? 'pointer' : 'not-allowed',
          opacity: canRun && !isRunning ? 1 : 0.6,
        }}
      >
        {isRunning ? 'Running…' : 'Run Reconciliation'}
      </button>
      {!canRun && (
        <p style={{ fontSize: '0.8rem', color: 'var(--text)', marginTop: '0.5rem', marginBottom: 0 }}>
          Select at least one purchase order and one invoice.
        </p>
      )}
      {error && <p style={{ color: '#ff4444', fontSize: '0.9rem' }}>{error}</p>}

      {result && (
        <div style={{ marginTop: '1.5rem' }}>
          <div
            style={{
              display: 'inline-block',
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              fontWeight: 700,
              color: STATUS_STYLES[result.status].color,
              background: STATUS_STYLES[result.status].bg,
            }}
          >
            Status: {STATUS_STYLES[result.status].label}
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text)' }}>
            Status is informational only — MATCHED is not payment authorization.
          </p>

          {result.notes.length > 0 && (
            <ul style={{ fontSize: '0.85rem' }}>
              {result.notes.map((note, i) => (
                <li key={i}>{note}</li>
              ))}
            </ul>
          )}

          {result.matching_details && (
            <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
              <h3 style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>Matching Details</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <h4>Invoice → PO Matches</h4>
                  {Object.entries(result.matching_details.invoice_to_po).map(([idx, match]) => (
                    <div key={idx} style={{ padding: '0.5rem', background: MATCH_TYPE_LABELS[match.match_type].bg, borderRadius: '4px', marginBottom: '0.5rem' }}>
                      <strong>Line {Number(idx) + 1}:</strong> {MATCH_TYPE_LABELS[match.match_type].label} (Score: {formatScore(match.score)})
                      <p style={{ fontSize: '0.8rem', margin: '0.2rem 0' }}>{match.explanation}</p>
                      <div style={{ fontSize: '0.75rem' }}>
                        Signals: {match.signals.map(s => `${s.name}: ${formatScore(s.score)}`).join(', ')}
                      </div>
                    </div>
                  ))}
                </div>
                <div>
                  <h4>Delivery → PO Matches</h4>
                  {Object.entries(result.matching_details.delivery_to_po).map(([idx, match]) => (
                    <div key={idx} style={{ padding: '0.5rem', background: MATCH_TYPE_LABELS[match.match_type].bg, borderRadius: '4px', marginBottom: '0.5rem' }}>
                      <strong>Line {Number(idx) + 1}:</strong> {MATCH_TYPE_LABELS[match.match_type].label} (Score: {formatScore(match.score)})
                      <p style={{ fontSize: '0.8rem', margin: '0.2rem 0' }}>{match.explanation}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {sortedDiscrepancies.length === 0 ? (
            <p style={{ color: 'var(--text)' }}>No discrepancies found.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border)' }}>
                  <th style={{ padding: '0.5rem', textAlign: 'left' }}>Severity</th>
                  <th style={{ padding: '0.5rem', textAlign: 'left' }}>Type</th>
                  <th style={{ padding: '0.5rem', textAlign: 'left' }}>Field</th>
                  <th style={{ padding: '0.5rem', textAlign: 'left' }}>Expected</th>
                  <th style={{ padding: '0.5rem', textAlign: 'left' }}>Observed</th>
                  <th style={{ padding: '0.5rem', textAlign: 'left' }}>Explanation</th>
                  <th style={{ padding: '0.5rem', textAlign: 'left' }}>Recommended action</th>
                </tr>
              </thead>
              <tbody>
                {sortedDiscrepancies.map((d, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '0.5rem', fontWeight: 700, color: d.severity === 'critical' || d.severity === 'error' ? '#b91c1c' : 'var(--text)' }}>
                      {d.severity}
                    </td>
                    <td style={{ padding: '0.5rem' }}>{d.discrepancy_type.replace(/_/g, ' ')}</td>
                    <td style={{ padding: '0.5rem', fontFamily: 'var(--mono)' }}>{d.field}</td>
                    <td style={{ padding: '0.5rem' }}>{d.expected ?? '—'}</td>
                    <td style={{ padding: '0.5rem' }}>{d.observed ?? '—'}</td>
                    <td style={{ padding: '0.5rem' }}>{d.explanation}</td>
                    <td style={{ padding: '0.5rem' }}>{d.recommended_action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </section>
  );
};
