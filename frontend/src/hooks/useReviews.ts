import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';

export interface CorrectionCreate {
  field_path: string;
  original_value: any;
  corrected_value: any;
  reviewer_id?: string;
}

export interface ReviewActionCreate {
  action: 'APPROVED' | 'REJECTED' | 'IN_REVIEW';
  reviewer_id?: string;
  notes?: string;
}

export const useReviews = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const listReviews = useCallback(async (status?: string | null) => {
    setLoading(true);
    setError(null);
    try {
      const params = status ? { status } : {};
      const res = await api.get('/reviews', { params });
      return res.data;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch reviews');
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const getReview = useCallback(async (reviewId: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/reviews/${reviewId}`);
      return res.data;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch review');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const addCorrection = useCallback(async (reviewId: string, data: CorrectionCreate) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post(`/reviews/${reviewId}/corrections`, data);
      return res.data;
    } catch (err: any) {
      setError(err.message || 'Failed to save correction');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const performAction = useCallback(async (reviewId: string, data: ReviewActionCreate) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post(`/reviews/${reviewId}/actions`, data);
      return res.data;
    } catch (err: any) {
      setError(err.message || 'Failed to perform review action');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    listReviews,
    getReview,
    addCorrection,
    performAction,
  };
};
