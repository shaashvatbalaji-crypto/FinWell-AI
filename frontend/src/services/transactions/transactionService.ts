import { apiClient } from '../api/apiClient';
import { Transaction } from '../../types';
import { MOCK_TRANSACTIONS } from '../../mock/mockData';

let inMemoryTransactions = [...MOCK_TRANSACTIONS];

export interface TransactionFilters {
  searchTerm?: string;
  category?: string;
  accountId?: number;
  direction?: 'all' | 'debit' | 'credit';
  status?: string;
  sortBy?: 'date_desc' | 'date_asc' | 'amount_desc' | 'amount_asc';
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

    const res = await apiClient.request<{
      success: boolean;
      count: number;
      transactions: Transaction[];
    }>('/transactions');

    return {
      count: res.count,
      transactions: res.transactions,
    };
  },

  async getDocumentTransactions(documentId: number): Promise<Transaction[]> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 250));
      return inMemoryTransactions.slice(0, 4);
    }

    const res = await apiClient.request<{
      success: boolean;
      transactions: Transaction[];
    }>(`/transactions/document/${documentId}`);
    return res.transactions;
  },
};
