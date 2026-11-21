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

    const res = await apiClient.request<{
      success: boolean;
      documents: DocumentRecord[];
    }>('/documents');
    return res.documents;
  },

  async uploadDocument(
    file: File,
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
      };

      inMemoryDocuments.unshift(newDoc);
      return newDoc;
    }

    // Real API upload flow: POST /api/upload
    const formData = new FormData();
    formData.append('file', file);

    const token = apiClient.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${apiClient.getBaseURL()}/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed with status ${response.status}`);
    }

    const result = await response.json();
    return result.document;
  },
};
