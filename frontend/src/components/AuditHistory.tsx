import React, { useState, useEffect } from 'react';
import { useReviews } from '../hooks/useReviews';

interface AuditHistoryProps {
  review: any;
}

export const AuditHistory: React.FC<AuditHistoryProps> = ({ review }) => {
  return (
    <div className="mt-6 border-t pt-4">
      <h3 className="font-semibold mb-3">Audit History</h3>

      <div className="space-y-4">
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-2">Corrections</h4>
          {review.corrections && review.corrections.length > 0 ? (
            <div className="space-y-2">
              {review.corrections.map((c: any) => (
                <div key={c.id} className="bg-gray-50 p-2 rounded text-xs">
                  <div className="font-semibold">{c.field_path} (v{c.version})</div>
                  <div className="text-red-600">Original: {JSON.stringify(c.original_value)}</div>
                  <div className="text-green-600">Corrected: {JSON.stringify(c.corrected_value)}</div>
                  <div className="text-gray-400 mt-1">By {c.corrected_by} at {new Date(c.corrected_at).toLocaleString()}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-400">No corrections recorded.</p>
          )}
        </div>

        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-2">Review Actions</h4>
          {review.actions && review.actions.length > 0 ? (
            <div className="space-y-2">
              {review.actions.map((a: any) => (
                <div key={a.id} className="bg-gray-50 p-2 rounded text-xs">
                  <div className="font-semibold text-blue-600">{a.action}</div>
                  {a.notes && <div className="text-gray-600">Notes: {a.notes}</div>}
                  <div className="text-gray-400 mt-1">By {a.reviewer_id} at {new Date(a.performed_at).toLocaleString()}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-400">No review actions recorded.</p>
          )}
        </div>
      </div>
    </div>
  );
};
