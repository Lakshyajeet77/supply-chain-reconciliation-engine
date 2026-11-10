/**
 * Shared API types mirroring backend Pydantic schemas (app/schemas/*).
 * Keep in sync manually; the backend remains the single source of truth for
 * all reconciliation logic.
 */

export type DocumentType = 'purchase_order' | 'delivery' | 'invoice';

export type ProcessingStatus = 'uploaded' | 'extracting' | 'extracted' | 'processing_failed';

export interface DocumentRecord {
  id: string;
  document_type: DocumentType;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  stored_path: string;
  processing_status: ProcessingStatus;
  uploaded_at: string;
  extraction_fixture_id: string | null;
  failure_reason: string | null;
  extracted_data: StoredExtractionData | null;
}

export interface StoredExtractionData {
  schema_version: string;
  document_type: DocumentType;
  extracted: ExtractedRecord;
  confidence: ConfidenceAssessment;
  source: ExtractionSource;
  extracted_summary: Record<string, string | null>;
}

export interface ExtractionSource {
  provider: string;
  fixture_id: string | null;
  modality: 'text' | 'vision';
}

export interface ConfidenceAssessment {
  schema_version: string;
  source: string | null;
  overall_score: number | null;
  fields: Record<string, FieldConfidence>;
}

export interface FieldConfidence {
  status: 'present' | 'missing' | 'uncertain';
  score: number | null;
  note: string | null;
}

/** Extracted payload is polymorphic; only shared fields are typed here. */
export interface ExtractedRecord {
  document_type: DocumentType;
  line_items?: ExtractedLineItem[];
  [key: string]: unknown;
}

export interface ExtractedLineItem {
  line_number?: number | null;
  description?: string | null;
  sku?: string | null;
  quantity?: string | null;
  unit_of_measure?: string | null;
  unit_price?: string | null;
  line_total?: string | null;
}

export type ReconciliationStatusValue = 'matched' | 'flagged' | 'needs_human_review';

export interface ReconciliationInput {
  purchase_order: ExtractedRecord | null;
  delivery: ExtractedRecord | null;
  invoice: ExtractedRecord | null;
}

export interface ReconciliationResult {
  status: ReconciliationStatusValue;
  discrepancies: Discrepancy[];
  notes: string[];
  matching_details?: MatchingDetails | null;
}

export interface MatchingDetails {
  invoice_to_po: Record<string, LineItemMatch>;
  delivery_to_po: Record<string, LineItemMatch>;
}

export interface LineItemMatch {
  score: number;
  match_type: 'exact_sku' | 'exact_description' | 'fuzzy_description' | 'unmatched';
  signals: MatchSignal[];
  explanation: string;
}

export interface MatchSignal {
  name: string;
  score: number;
}

export interface Discrepancy {
  discrepancy_type: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  field: string;
  expected: string | null;
  observed: string | null;
  difference: string | null;
  explanation: string;
  recommended_action: string;
}

export function formatScore(score: number | null): string {
  return score === null ? '—' : score.toFixed(2);
}

export function formatDocumentType(type: DocumentType): string {
  return type.replace('_', ' ');
}
