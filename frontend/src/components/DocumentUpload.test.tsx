import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DocumentUpload } from './DocumentUpload';
import apiClient from '../api/client';

vi.mock('../api/client', () => ({
  default: { post: vi.fn() },
}));

const mockedPost = vi.mocked(apiClient.post);

function pngFile(name = 'invoice.png') {
  return new File([new Uint8Array([0x89, 0x50, 0x4e, 0x47])], name, { type: 'image/png' });
}

beforeEach(() => {
  mockedPost.mockReset();
});

describe('DocumentUpload', () => {
  it('disables submit until a file is chosen', async () => {
    render(<DocumentUpload onUploadSuccess={() => {}} />);
    expect(screen.getByRole('button', { name: /upload/i })).toBeDisabled();
  });

  it('posts multipart form data and calls onUploadSuccess', async () => {
    const user = userEvent.setup();
    const onUploadSuccess = vi.fn();
    mockedPost.mockResolvedValueOnce({ data: {} } as never);

    render(<DocumentUpload onUploadSuccess={onUploadSuccess} />);

    // Upload via input directly (input type=file has no accessible role label)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, pngFile());
    await user.click(screen.getByRole('button', { name: /upload/i }));

    await waitFor(() => expect(onUploadSuccess).toHaveBeenCalledTimes(1));
    expect(mockedPost).toHaveBeenCalledTimes(1);
    const [url, body, config] = mockedPost.mock.calls[0];
    expect(url).toBe('/documents/upload');
    expect(body).toBeInstanceOf(FormData);
    expect((body as FormData).get('document_type')).toBe('invoice');
    const headers = config?.headers as Record<string, unknown> | undefined;
    expect(headers?.['Content-Type']).toBe('multipart/form-data');
  });

  it('shows an error message when upload fails', async () => {
    const user = userEvent.setup();
    mockedPost.mockRejectedValueOnce({
      response: { data: { detail: { message: 'Exact-file duplicate detected' } } },
    } as never);

    render(<DocumentUpload onUploadSuccess={() => {}} />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, pngFile());
    await user.click(screen.getByRole('button', { name: /upload/i }));

    await waitFor(() => expect(screen.getByText(/exact-file duplicate/i)).toBeInTheDocument());
  });
});
