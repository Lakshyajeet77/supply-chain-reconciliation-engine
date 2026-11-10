import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TransactionDashboard } from './TransactionDashboard';
import apiClient from '../api/client';
import { vi, describe, it, expect, beforeEach } from 'vitest';

vi.mock('../api/client');

describe('TransactionDashboard', () => {
  const mockDocuments = [
    {
      id: 'po-1',
      document_type: 'purchase_order',
      original_filename: 'po_1.pdf',
      content_type: 'application/pdf',
      size_bytes: 100,
      sha256: 'abc',
      stored_path: '/tmp/po_1.pdf',
      processing_status: 'extracted',
      uploaded_at: new Date().toISOString(),
      extraction_fixture_id: null,
      failure_reason: null,
      extracted_data: { extracted: { po_number: 'PO-100' } },
    },
    {
      id: 'inv-1',
      document_type: 'invoice',
      original_filename: 'inv_1.pdf',
      content_type: 'application/pdf',
      size_bytes: 100,
      sha256: 'def',
      stored_path: '/tmp/inv_1.pdf',
      processing_status: 'extracted',
      uploaded_at: new Date().toISOString(),
      extraction_fixture_id: null,
      failure_reason: null,
      extracted_data: { extracted: { invoice_number: 'INV-100', po_reference: 'PO-100' } },
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading and fetches relationships on mount', async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: [] });

    render(<TransactionDashboard documents={mockDocuments} />);

    expect(screen.getByText(/Transaction Relationships & Reconciliation/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/relationships');
    });
  });

  it('displays suggested and confirmed relationships and allows confirmation', async () => {
    const relationships = [
      {
        id: 'rel-1',
        po_id: 'po-1',
        invoice_id: 'inv-1',
        delivery_id: null,
        status: 'SUGGESTED',
        created_at: new Date().toISOString(),
        confirmed_at: null,
        confirmed_by: null,
      },
    ];

    (apiClient.get as any).mockResolvedValueOnce({ data: relationships });
    (apiClient.post as any).mockResolvedValueOnce({ data: { ...relationships[0], status: 'CONFIRMED' } });
    (apiClient.get as any).mockResolvedValueOnce({
      data: [{ ...relationships[0], status: 'CONFIRMED', confirmed_at: new Date().toISOString(), confirmed_by: 'user' }],
    });

    render(<TransactionDashboard documents={mockDocuments} />);

    await waitFor(() => {
      expect(screen.getByText(/Suggested Relationships \(1\)/i)).toBeInTheDocument();
    });

    const confirmButton = screen.getByRole('button', { name: /Confirm Relationship/i });
    await userEvent.click(confirmButton);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/relationships/rel-1/confirm', null, {
        params: { confirmed_by: 'dashboard-user' },
      });
    });
  });
});
