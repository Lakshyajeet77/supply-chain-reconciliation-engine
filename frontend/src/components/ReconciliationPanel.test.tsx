import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ReconciliationPanel } from './ReconciliationPanel';
import apiClient from '../api/client';
import { makeDocument, makeExtractedData } from '../test/helpers';
import type { DocumentRecord, DocumentType } from '../api/types';

vi.mock('../api/client', () => ({
  default: { post: vi.fn() },
}));

const mockedPost = vi.mocked(apiClient.post);

function doc(type: DocumentType, name: string): DocumentRecord {
  return makeDocument({
    document_type: type,
    original_filename: name,
    extracted_data: makeExtractedData({}, type),
  });
}

beforeEach(() => {
  mockedPost.mockReset();
});

describe('ReconciliationPanel', () => {
  it('disables run until a PO and an invoice are selected', async () => {
    const user = userEvent.setup();
    const po = doc('purchase_order', 'po.png');
    const invoice = doc('invoice', 'inv.png');
    render(<ReconciliationPanel documents={[po, invoice]} />);

    const runButton = screen.getByRole('button', { name: /run reconciliation/i });
    expect(runButton).toBeDisabled();

    const selects = screen.getAllByRole('combobox');
    // selects order: purchase_order, delivery, invoice; option values are document ids
    await user.selectOptions(selects[0], po.id);
    await user.selectOptions(selects[2], invoice.id);
    expect(runButton).toBeEnabled();
  });

  it('posts extracted payloads and displays status and discrepancies', async () => {
    const user = userEvent.setup();
    const po = doc('purchase_order', 'po.png');
    const invoice = doc('invoice', 'inv.png');
    mockedPost.mockResolvedValueOnce({
      data: {
        status: 'flagged',
        notes: ['Delivery record supplied; quantity compared against delivered amounts when SKUs align.'],
        discrepancies: [
          {
            discrepancy_type: 'price_mismatch',
            severity: 'error',
            field: 'unit_price:SKU-1',
            expected: '2500.00',
            observed: '2750.00',
            difference: '250.00',
            explanation: 'Invoice unit price differs from approved PO price.',
            recommended_action: 'Flag for price review.',
          },
        ],
      },
    } as never);

    render(<ReconciliationPanel documents={[po, invoice]} />);
    const selects = screen.getAllByRole('combobox');
    await user.selectOptions(selects[0], po.id);
    await user.selectOptions(selects[2], invoice.id);
    await user.click(screen.getByRole('button', { name: /run reconciliation/i }));

    await waitFor(() => expect(screen.getByText(/status: flagged/i)).toBeInTheDocument());
    expect(screen.getByText('unit_price:SKU-1')).toBeInTheDocument();
    expect(screen.getByText('2500.00')).toBeInTheDocument();
    expect(screen.getByText('2750.00')).toBeInTheDocument();
    expect(screen.getByText(/flag for price review/i)).toBeInTheDocument();

    const [url, payload] = mockedPost.mock.calls[0];
    expect(url).toBe('/reconciliation/run');
    expect(payload).toMatchObject({
      purchase_order: { document_type: 'purchase_order' },
      invoice: { document_type: 'invoice' },
      delivery: null,
    });
  });

  it('shows no-discrepancies message for a matched result', async () => {
    const user = userEvent.setup();
    const po = doc('purchase_order', 'po.png');
    const invoice = doc('invoice', 'inv.png');
    mockedPost.mockResolvedValueOnce({
      data: { status: 'matched', notes: [], discrepancies: [] },
    } as never);

    render(<ReconciliationPanel documents={[po, invoice]} />);
    const selects = screen.getAllByRole('combobox');
    await user.selectOptions(selects[0], po.id);
    await user.selectOptions(selects[2], invoice.id);
    await user.click(screen.getByRole('button', { name: /run reconciliation/i }));

    await waitFor(() => expect(screen.getByText(/no discrepancies found/i)).toBeInTheDocument());
  });

  it('allows selecting a Delivery Challan and includes it in the payload', async () => {
    const user = userEvent.setup();
    const po = doc('purchase_order', 'po.png');
    const delivery = doc('delivery', 'delivery.png');
    const invoice = doc('invoice', 'inv.png');
    mockedPost.mockResolvedValueOnce({
      data: { status: 'matched', notes: ['Delivery record supplied; quantity compared against delivered amounts when SKUs align.'], discrepancies: [] },
    } as never);

    render(<ReconciliationPanel documents={[po, delivery, invoice]} />);
    const selects = screen.getAllByRole('combobox');
    await user.selectOptions(selects[0], po.id);
    await user.selectOptions(selects[1], delivery.id);
    await user.selectOptions(selects[2], invoice.id);
    await user.click(screen.getByRole('button', { name: /run reconciliation/i }));

    await waitFor(() => expect(screen.getByText(/status: matched/i)).toBeInTheDocument());
    const [, payload] = mockedPost.mock.calls[0] as [string, { delivery: { document_type: string } | null }];
    expect(payload.delivery).not.toBeNull();
    expect(payload.delivery?.document_type).toBe('delivery');
  });

  it('displays delivery-related discrepancy when quantity exceeds delivered', async () => {
    const user = userEvent.setup();
    const po = doc('purchase_order', 'po.png');
    const delivery = doc('delivery', 'delivery_partial.png');
    const invoice = doc('invoice', 'inv.png');
    mockedPost.mockResolvedValueOnce({
      data: {
        status: 'flagged',
        notes: ['Delivery record supplied; quantity compared against delivered amounts when SKUs align.'],
        discrepancies: [
          {
            discrepancy_type: 'quantity_mismatch',
            severity: 'error',
            field: 'delivered_vs_invoiced:LOG-MX-001',
            expected: '8',
            observed: '10',
            difference: '2',
            explanation: 'Invoiced quantity exceeds delivered quantity.',
            recommended_action: 'Flag over-billing relative to delivery.',
          },
        ],
      },
    } as never);

    render(<ReconciliationPanel documents={[po, delivery, invoice]} />);
    const selects = screen.getAllByRole('combobox');
    await user.selectOptions(selects[0], po.id);
    await user.selectOptions(selects[1], delivery.id);
    await user.selectOptions(selects[2], invoice.id);
    await user.click(screen.getByRole('button', { name: /run reconciliation/i }));

    await waitFor(() => expect(screen.getByText(/status: flagged/i)).toBeInTheDocument());
    expect(screen.getByText('delivered_vs_invoiced:LOG-MX-001')).toBeInTheDocument();
    expect(screen.getByText('Flag over-billing relative to delivery.')).toBeInTheDocument();
  });
});
