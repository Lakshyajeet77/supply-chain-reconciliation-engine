import type { DocumentRecord, DocumentType, StoredExtractionData } from '../api/types';

/** Build a DocumentRecord fixture for tests. */
export function makeDocument(overrides: Partial<DocumentRecord> = {}): DocumentRecord {
  return {
    id: overrides.id ?? crypto.randomUUID(),
    document_type: overrides.document_type ?? 'invoice',
    original_filename: overrides.original_filename ?? 'invoice.png',
    content_type: overrides.content_type ?? 'image/png',
    size_bytes: overrides.size_bytes ?? 1024,
    sha256: overrides.sha256 ?? 'a'.repeat(64),
    stored_path: overrides.stored_path ?? 'stored.png',
    processing_status: overrides.processing_status ?? 'extracted',
    uploaded_at: overrides.uploaded_at ?? new Date().toISOString(),
    extraction_fixture_id: overrides.extraction_fixture_id ?? 'invoice_matched',
    failure_reason: overrides.failure_reason ?? null,
    extracted_data: overrides.extracted_data ?? null,
  };
}

export function makeExtractedData(extracted: Record<string, unknown> = {}, docType: DocumentType = 'invoice'): StoredExtractionData {
  return {
    schema_version: '1',
    document_type: docType,
    extracted: {
      document_type: docType,
      invoice_number: 'INV-9001',
      currency: 'INR',
      total: '29.50',
      line_items: [],
      ...extracted,
    },
    confidence: {
      schema_version: '1',
      source: 'baseline-heuristic::invoice',
      overall_score: 0.95,
      fields: {
        invoice_number: { status: 'present', score: 0.95, note: null },
        tax_total: { status: 'missing', score: null, note: null },
      },
    },
    source: { provider: 'fixture', fixture_id: 'invoice_matched', modality: 'text' },
    extracted_summary: {},
  };
}
