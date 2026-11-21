import { apiClient } from '../api/apiClient';
import { Transaction } from '../../types';
import { MOCK_TRANSACTIONS } from '../../mock/mockData';

let inMemoryTransactions = [...MOCK_TRANSACTIONS];
let accountNamesCache: Record<number, string> = {};

export interface TransactionFilters {
  searchTerm?: string;
  category?: string;
  accountId?: number;
  direction?: 'all' | 'debit' | 'credit';
  status?: string;
  sortBy?: 'date_desc' | 'date_asc' | 'amount_desc' | 'amount_asc';
}

function inferCategory(description: string): string {
  const desc = (description || '').toLowerCase();
  if (desc.includes('transfer') || desc.includes('trf') || desc.includes('own ac')) return 'Internal Transfer';
  if (desc.includes('salary') || desc.includes('consulting') || desc.includes('deposit') || desc.includes('received')) return 'Consulting Income';
  if (desc.includes('aws') || desc.includes('cloud') || desc.includes('github') || desc.includes('openai') || desc.includes('software')) return 'Cloud Infrastructure & Tech';
  if (desc.includes('food') || desc.includes('swiggy') || desc.includes('zomato') || desc.includes('restaurant') || desc.includes('dining')) return 'Dining & Entertainment';
  if (desc.includes('rent') || desc.includes('utility') || desc.includes('electric') || desc.includes('housing')) return 'Housing & Utilities';
  if (desc.includes('dividend') || desc.includes('interest') || desc.includes('mutual') || desc.includes('stock')) return 'Investment Income';
  if (desc.includes('sub') || desc.includes('netflix') || desc.includes('spotify') || desc.includes('prime')) return 'Software Subscriptions';
  return 'General Transaction';
}

function extractRefNumber(description: string, txnId: number): string {
  const match = (description || '').match(/\b(?:REF|UPI|TXN|IMPS)[:\s-]*([A-Za-z0-9]+)\b/i);
  return match ? match[1].toUpperCase() : `TXN-${txnId}`;
}

function normalizeRawTransaction(raw: any): Transaction {
  const debitVal = raw.debit !== null && raw.debit !== undefined ? parseFloat(String(raw.debit)) : null;
  const creditVal = raw.credit !== null && raw.credit !== undefined ? parseFloat(String(raw.credit)) : null;
  const isCredit = creditVal !== null && creditVal > 0;
  const amount = isCredit ? (creditVal || 0) : (debitVal || 0);
  const direction: 'credit' | 'debit' = isCredit ? 'credit' : 'debit';
  const balanceAfter = raw.balance !== null && raw.balance !== undefined ? parseFloat(String(raw.balance)) : null;
  const description = raw.description || 'Transaction';

  return {
    transaction_id: raw.transaction_id,
    account_id: raw.account_id || 0,
    account_name: raw.account_name,
    document_id: raw.document_id ?? null,
    transaction_date: raw.transaction_date ? String(raw.transaction_date).slice(0, 10) : new Date().toISOString().slice(0, 10),
    description,
    category: raw.category || inferCategory(description),
    debit: debitVal,
    credit: creditVal,
    amount,
    direction,
    currency: raw.currency || 'INR',
    balance_after: balanceAfter,
    reference_number: raw.reference_number || extractRefNumber(description, raw.transaction_id),
    is_reconciled: Boolean(raw.is_reconciled),
    status: (raw.status || 'posted') as 'posted' | 'pending' | 'flagged',
  };
}

export const transactionService = {
  async getTransactions(filters?: TransactionFilters): Promise<{ count: number; transactions: Transaction[] }> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 350));
      let filtered = [...inMemoryTransactions];

      if (filters?.searchTerm) {
        const q = filters.searchTerm.toLowerCase();
        filtered = filtered.filter(
          (t) =>
            t.description.toLowerCase().includes(q) ||
            t.category.toLowerCase().includes(q) ||
            t.reference_number?.toLowerCase().includes(q)
        );
      }

      if (filters?.category && filters.category !== 'all') {
        filtered = filtered.filter((t) => t.category === filters.category);
      }

      if (filters?.accountId) {
        filtered = filtered.filter((t) => t.account_id === filters.accountId);
      }

      if (filters?.direction && filters.direction !== 'all') {
        filtered = filtered.filter((t) => t.direction === filters.direction);
      }

      if (filters?.sortBy) {
        switch (filters.sortBy) {
          case 'date_desc':
            filtered.sort((a, b) => new Date(b.transaction_date).getTime() - new Date(a.transaction_date).getTime());
            break;
          case 'date_asc':
            filtered.sort((a, b) => new Date(a.transaction_date).getTime() - new Date(b.transaction_date).getTime());
            break;
          case 'amount_desc':
            filtered.sort((a, b) => b.amount - a.amount);
            break;
          case 'amount_asc':
            filtered.sort((a, b) => a.amount - b.amount);
            break;
        }
      }

      return {
        count: filtered.length,
        transactions: filtered,
      };
    }

    try {
      const res = await apiClient.request<{
        success: boolean;
        message: string;
        count: number;
        transactions: any[];
      }>('/transactions?limit=500&offset=0');

      if (Object.keys(accountNamesCache).length === 0) {
        try {
          const accRes = await apiClient.request<{ success: boolean; accounts: any[] }>('/accounts');
          if (accRes.accounts) {
            accRes.accounts.forEach((a) => {
              accountNamesCache[a.account_id] = a.account_name;
            });
          }
        } catch {
          // ignore
        }
      }

      let normalizedList = (res.transactions || []).map((raw) => {
        const item = normalizeRawTransaction(raw);
        if (!item.account_name && accountNamesCache[item.account_id]) {
          item.account_name = accountNamesCache[item.account_id];
        }
        return item;
      });

      if (filters?.searchTerm) {
        const q = filters.searchTerm.toLowerCase();
        normalizedList = normalizedList.filter(
          (t) =>
            t.description.toLowerCase().includes(q) ||
            t.category.toLowerCase().includes(q) ||
            t.reference_number?.toLowerCase().includes(q)
        );
      }

      if (filters?.category && filters.category !== 'all') {
        normalizedList = normalizedList.filter((t) => t.category === filters.category);
      }

      if (filters?.accountId) {
        normalizedList = normalizedList.filter((t) => t.account_id === filters.accountId);
      }

      if (filters?.direction && filters.direction !== 'all') {
        normalizedList = normalizedList.filter((t) => t.direction === filters.direction);
      }

      if (filters?.sortBy) {
        switch (filters.sortBy) {
          case 'date_desc':
            normalizedList.sort((a, b) => new Date(b.transaction_date).getTime() - new Date(a.transaction_date).getTime());
            break;
          case 'date_asc':
            normalizedList.sort((a, b) => new Date(a.transaction_date).getTime() - new Date(b.transaction_date).getTime());
            break;
          case 'amount_desc':
            normalizedList.sort((a, b) => b.amount - a.amount);
            break;
          case 'amount_asc':
            normalizedList.sort((a, b) => a.amount - b.amount);
            break;
        }
      }

      return {
        count: normalizedList.length,
        transactions: normalizedList,
      };
    } catch (err) {
      console.error('[FinWell] Error fetching transactions:', err);
      throw err;
    }
  },

  async getDocumentTransactions(documentId: number): Promise<Transaction[]> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 250));
      return inMemoryTransactions.slice(0, 4);
    }

    const res = await apiClient.request<{
      success: boolean;
      transactions: any[];
    }>(`/transactions/document/${documentId}`);

    return (res.transactions || []).map(normalizeRawTransaction);
  },
};
