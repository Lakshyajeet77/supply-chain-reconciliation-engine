import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { DocumentDetail } from './DocumentDetail';
import apiClient from '../api/client';
import { makeDocument, makeExtractedData } from '../test/helpers';

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    defaults: { baseURL: 'http://localhost:8000' },
  },
}));

const mockedGet = vi.mocked(apiClient.get);

beforeEach(() => {
  mockedGet.mockReset();
});

describe('DocumentDetail', () => {
  it('shows a loading state initially', () => {
    mockedGet.mockReturnValue(new Promise(() => {}) as never);
    render(<DocumentDetail documentId="abc" onClose={() => {}} />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders extracted data and confidence scores', async () => {
    mockedGet.mockResolvedValueOnce({
      data: makeDocument({
        id: 'abc',
        extracted_data: makeExtractedData({}, 'invoice'),
        document_type: 'invoice',
      }),
    } as never);

    render(<DocumentDetail documentId="abc" onClose={() => {}} />);

    await waitFor(() => expect(screen.getByText(/INV-9001/)).toBeInTheDocument());
    expect(screen.getByText(/overall: 0.95/i)).toBeInTheDocument();
    // Present field has a numeric score; MISSING field renders an em dash instead of crashing.
    expect(screen.getByText('invoice_number')).toBeInTheDocument();
    expect(screen.getByText('tax_total')).toBeInTheDocument();
    const dash = screen.getAllByText('—');
    expect(dash.length).toBeGreaterThanOrEqual(1);
  });

  it('shows an error state on failed fetch', async () => {
    mockedGet.mockRejectedValueOnce({ response: { status: 404 } } as never);
    render(<DocumentDetail documentId="abc" onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText(/document not found/i)).toBeInTheDocument());
  });

  it('renders an image preview for image documents', async () => {
    mockedGet.mockResolvedValueOnce({ data: makeDocument({ id: 'abc' }) } as never);
    render(<DocumentDetail documentId="abc" onClose={() => {}} />);
    await waitFor(() => {
      const img = screen.getByAltText(/preview of/i);
      expect(img).toHaveAttribute('src', 'http://localhost:8000/documents/abc/file');
    });
  });
});
