// ==========================================
// FINWELL AI — CORE TYPE DEFINITIONS
// Matches FastAPI backend & MySQL/Chroma schemas
// ==========================================

export interface User {
  user_id: number;
  username: string;
  email: string;
  full_name?: string;
  avatar?: string;
  created_at?: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  isMockMode: boolean;
}

export type AccountType = 
  | 'savings' 
  | 'current' 
  | 'salary' 
  | 'credit_card' 
  | 'loan' 
  | 'investment' 
  | 'cash' 
  | 'other';

export interface Account {
  account_id: number;
  user_id: number;
  account_name: string;
  institution_name: string;
  account_type: AccountType;
  masked_account_number: string;
  currency: string;
  current_balance: number;
  available_balance?: number;
  last_synced?: string;
  color?: string;
}

export interface Transaction {
  transaction_id: number;
  account_id: number;
  account_name?: string;
  document_id?: number | null;
  transaction_date: string;
  description: string;
  category: string;
  debit: number | null;
  credit: number | null;
  amount: number;
  direction: 'debit' | 'credit';
  currency: string;
  balance_after?: number | null;
  reference_number?: string;
  is_reconciled?: boolean;
  status: 'posted' | 'pending' | 'flagged';
}

export interface ReconciliationEvidence {
  evidence_type: 
    | 'transaction_reference' 
    | 'amount_match' 
    | 'date_match' 
    | 'description_match' 
    | 'statement_balance' 
    | 'merchant_match' 
    | 'document_reference' 
    | 'other';
  description: string;
  score: number;
}

export interface ReconciliationCase {
  case_id: number;
  case_type: 
    | 'duplicate' 
    | 'internal_transfer' 
    | 'refund' 
    | 'settlement' 
    | 'merchant_verification' 
    | 'balance_discrepancy';
  status: 
    | 'detected' 
    | 'evaluated' 
    | 'suggested' 
    | 'confirmed' 
    | 'rejected' 
    | 'needs_review' 
    | 'unmatched';
  confidence_score: number; // 0 to 100
  title: string;
  description: string;
  created_at: string;
  source_transaction: Transaction;
  target_transaction?: Transaction;
  evidences: ReconciliationEvidence[];
}

export type DocumentProcessingStage = 
  | 'uploaded' 
  | 'validating' 
  | 'extracting_transactions' 
  | 'normalizing' 
  | 'validating_records' 
  | 'saving_records' 
  | 'ready_for_ai' 
  | 'error';

export interface DocumentRecord {
  document_id: number;
  user_id: number;
  filename: string;
  file_size_bytes: number;
  file_type: string;
  uploaded_at: string;
  status: 'processing' | 'completed' | 'failed';
  current_stage: DocumentProcessingStage;
  progress_percent: number;
  extracted_transactions_count: number;
  institution_detected?: string;
  statement_period?: string;
  validation_status: 'valid' | 'warning' | 'error';
}

export interface AnalyticsSummary {
  total_balance: number;
  total_income: number;
  total_expenses: number;
  net_cash_flow: number;
  savings_rate: number;
  comparison_last_month: {
    income_change_percent: number;
    expense_change_percent: number;
    balance_change_percent: number;
  };
}

export interface MonthlyTrend {
  month: string;
  income: number;
  expense: number;
  net: number;
  current_year_income?: number;
  last_year_income?: number;
}

export interface CategorySpending {
  category: string;
  amount: number;
  percentage: number;
  color: string;
  transaction_count: number;
}

// AI Chat Types
export interface ChromaEvidenceChunk {
  chunk_id: string;
  document_name: string;
  page_number: number;
  similarity_score: number;
  extracted_snippet: string;
  extracted_date: string;
}

export interface MySQLEvidence {
  table_queried: string;
  record_count: number;
  query_latency_ms: number;
  relevant_transaction_ids: number[];
  filter_applied: string;
}

export interface AIResponseEvidence {
  reporting_period: string;
  mysql_evidence: MySQLEvidence;
  chroma_evidence: ChromaEvidenceChunk[];
  data_limitations: string;
  confidence: number;
}

export interface InlineChartData {
  chart_type: 'dual_line' | 'bar' | 'donut';
  title: string;
  data: any[];
  keys: { key: string; name: string; color: string }[];
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: string;
  inline_chart?: InlineChartData;
  financial_summary?: {
    total_analyzed?: string;
    variance?: string;
    key_takeaway?: string;
  };
  evidence?: AIResponseEvidence;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  time_group: 'Today' | 'Yesterday' | 'Last 7 days' | 'Older';
  message_count: number;
}

export interface ReportItem {
  id: string;
  title: string;
  type: 'monthly_financial' | 'income_expenditure' | 'spending' | 'account_summary' | 'reconciliation';
  period: string;
  generated_at: string;
  file_format: 'PDF' | 'CSV';
  file_size: string;
  summary: string;
}
