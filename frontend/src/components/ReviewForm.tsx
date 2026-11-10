import React, { useState } from 'react';
import { useReviews } from '../hooks/useReviews';

interface ReviewFormProps {
  review: any;
  onSave: () => void;
}

export const ReviewForm: React.FC<ReviewFormProps> = ({ review, onSave }) => {
  const [fieldPath, setFieldPath] = useState('');
  const [correctedValue, setCorrectedValue] = useState('');
  const { addCorrection, loading, error } = useReviews();

  const handleAddCorrection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fieldPath) return;

    // Resolve original value from original_extraction
    const parts = fieldPath.split('.');
    let curr = review.original_extraction;
    for (const p of parts) {
      if (curr && typeof curr === 'object') {
        curr = curr[p];
      } else {
        curr = null;
        break;
      }
    }

    try {
      await addCorrection(review.id, {
        field_path: fieldPath,
        original_value: curr,
        corrected_value: correctedValue,
        reviewer_id: 'frontend-reviewer',
      });
      setFieldPath('');
      setCorrectedValue('');
      onSave();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <form onSubmit={handleAddCorrection} className="space-y-4">
      <h3 className="font-semibold text-sm">Add Field Correction</h3>
      {error && <div className="text-red-500 text-xs">{error}</div>}

      <div>
        <label className="block text-xs font-medium text-gray-700">Field Path (e.g. po_number or line_items.0.quantity)</label>
        <input
          type="text"
          value={fieldPath}
          onChange={(e) => setFieldPath(e.target.value)}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm border p-1 text-xs"
          placeholder="po_number"
          required
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-700">Corrected Value</label>
        <input
          type="text"
          value={correctedValue}
          onChange={(e) => setCorrectedValue(e.target.value)}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm border p-1 text-xs"
          placeholder="New value"
          required
        />
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={loading}
          className="px-3 py-1 bg-green-500 text-white rounded text-xs hover:bg-green-600 disabled:opacity-50"
        >
          {loading ? 'Saving...' : 'Save Correction'}
        </button>
        <button
          type="button"
          onClick={onSave}
          className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-xs hover:bg-gray-300"
        >
          Cancel
        </button>
      </div>
    </form>
  );
};
