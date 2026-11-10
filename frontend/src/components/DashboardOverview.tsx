import React from 'react';

interface OverviewProps {
  totalDocs: number;
  statusCounts: { [key: string]: number };
}

export const DashboardOverview: React.FC<OverviewProps> = ({ totalDocs, statusCounts }) => {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
      <div style={{ padding: '1rem', border: '1px solid var(--border)', borderRadius: '8px', background: 'var(--bg)' }}>
        <h3>Total Documents</h3>
        <p style={{ fontSize: '2rem', fontWeight: 'bold', margin: '0.5rem 0' }}>{totalDocs}</p>
      </div>
      {Object.entries(statusCounts).map(([status, count]) => (
        <div key={status} style={{ padding: '1rem', border: '1px solid var(--border)', borderRadius: '8px', background: 'var(--bg)' }}>
          <h3 style={{ textTransform: 'capitalize' }}>{status.replace('_', ' ')}</h3>
          <p style={{ fontSize: '2rem', fontWeight: 'bold', margin: '0.5rem 0' }}>{count}</p>
        </div>
      ))}
    </div>
  );
};
