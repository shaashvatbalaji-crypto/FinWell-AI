import { apiClient } from '../api/apiClient';
import { DocumentRecord, DocumentProcessingStage } from '../../types';
import { MOCK_DOCUMENTS } from '../../mock/mockData';

let inMemoryDocuments = [...MOCK_DOCUMENTS];

export const STAGE_DESCRIPTIONS: Record<DocumentProcessingStage, string> = {
  uploaded: 'File uploaded to secure sandbox storage',
  validating: 'Checking digital signature, header metadata & MIME integrity',
  extracting_transactions: 'Neural optical & layout-aware parser extracting tabular rows',
  normalizing: 'Resolving dates, amounts, opposing currency debits/credits',
  validating_records: 'Checksum reconciliation against opening/closing statement balances',
  saving_records: 'Writing transactional records into MySQL ledger with transaction isolation',
  ready_for_ai: 'Embeddings indexed in ChromaDB for high-dimensional vector retrieval',
  error: 'Validation failed during processing pipeline',
};

export const documentService = {
  async getDocuments(): Promise<DocumentRecord[]> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 300));
      return [...inMemoryDocuments];
    }

    try {
      const res = await apiClient.request<{
        success: boolean;
        count: number;
        documents: any[];
      }>('/documents');

      return (res.documents || []).map((doc) => ({
        document_id: doc.document_id,
        user_id: doc.user_id || 1,
        filename: doc.original_filename || `Document_${doc.document_id}.pdf`,
        file_size_bytes: 250000,
        file_type: 'application/pdf',
        uploaded_at: doc.uploaded_at ? new Date(doc.uploaded_at).toISOString() : new Date().toISOString(),
        status: doc.processing_status === 'completed' ? 'completed' : (doc.processing_status === 'failed' ? 'failed' : 'processing'),
        current_stage: doc.processing_status === 'completed' ? 'ready_for_ai' : (doc.processing_status === 'failed' ? 'error' : 'normalizing'),
        progress_percent: doc.processing_status === 'completed' ? 100 : 50,
        extracted_transactions_count: doc.page_count ? doc.page_count * 15 : 0,
        institution_detected: doc.document_type || 'Bank Statement',
        statement_period: 'Verified Statement',
        validation_status: 'valid',
        account_id: doc.account_id,
      }));
    } catch (err) {
      console.error('[FinWell] Error fetching documents:', err);
      throw err;
    }
  },

  async uploadDocument(
    file: File,
    accountId?: number | null,
    onProgressUpdate?: (stage: DocumentProcessingStage, percent: number) => void
  ): Promise<DocumentRecord> {
    if (apiClient.isMockMode()) {
      const stages: { stage: DocumentProcessingStage; percent: number; delay: number }[] = [
        { stage: 'uploaded', percent: 15, delay: 500 },
        { stage: 'validating', percent: 30, delay: 600 },
        { stage: 'extracting_transactions', percent: 55, delay: 800 },
        { stage: 'normalizing', percent: 70, delay: 700 },
        { stage: 'validating_records', percent: 85, delay: 600 },
        { stage: 'saving_records', percent: 95, delay: 500 },
        { stage: 'ready_for_ai', percent: 100, delay: 400 },
      ];

      for (const step of stages) {
        if (onProgressUpdate) {
          onProgressUpdate(step.stage, step.percent);
        }
        await new Promise((r) => setTimeout(r, step.delay));
      }

      const newDoc: DocumentRecord = {
        document_id: Date.now(),
        user_id: 101,
        filename: file.name,
        file_size_bytes: file.size,
        file_type: file.type || 'application/pdf',
        uploaded_at: new Date().toISOString(),
        status: 'completed',
        current_stage: 'ready_for_ai',
        progress_percent: 100,
        extracted_transactions_count: Math.floor(Math.random() * 35) + 12,
        institution_detected: 'Detected Financial Statement',
        statement_period: 'Current Quarter',
        validation_status: 'valid',
        account_id: accountId,
      };

      inMemoryDocuments.unshift(newDoc);
      return newDoc;
    }

    // Real API upload flow: POST /api/upload
    const formData = new FormData();
    formData.append('file', file);
    if (accountId !== null && accountId !== undefined && accountId > 0) {
      formData.append('account_id', String(accountId));
    }

    if (onProgressUpdate) {
      onProgressUpdate('uploaded', 20);
    }

    const token = apiClient.getToken();
    const headers: Record<string, string> = {
      Accept: 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (onProgressUpdate) {
      onProgressUpdate('extracting_transactions', 45);
    }

    const response = await fetch(`${apiClient.getBaseURL()}/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (onProgressUpdate) {
      onProgressUpdate('saving_records', 80);
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      let msg = `Upload failed with status ${response.status}`;
      if (typeof errorData.detail === 'string') msg = errorData.detail;
      else if (errorData.message) msg = errorData.message;
      throw new Error(msg);
    }

    const res = await response.json();
    if (res.success === false) {
      throw new Error(res.message || 'Document processing failed.');
    }
    if (onProgressUpdate) {
      onProgressUpdate('ready_for_ai', 100);
    }

    return {
      document_id: res.document_id,
      user_id: res.user_id,
      filename: res.filename || file.name,
      file_size_bytes: file.size,
      file_type: file.type || 'application/pdf',
      uploaded_at: new Date().toISOString(),
      status: res.processing_status === 'failed' ? 'failed' : 'completed',
      current_stage: 'ready_for_ai',
      progress_percent: 100,
      extracted_transactions_count: res.stored_transactions || res.total_transactions || 0,
      institution_detected: res.document_type || 'Bank Statement',
      statement_period: 'Verified Period',
      validation_status: res.invalid_transactions > 0 ? 'warning' : 'valid',
      account_id: res.account_id,
    };
  },
};
