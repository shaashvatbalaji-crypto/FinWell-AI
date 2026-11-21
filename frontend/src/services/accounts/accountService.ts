import { apiClient } from '../api/apiClient';
import { Account, AccountType } from '../../types';
import { MOCK_ACCOUNTS } from '../../mock/mockData';

export interface CreateAccountDTO {
  account_name: string;
  institution_name: string;
  account_type: AccountType;
  masked_account_number: string;
  currency: string;
  initial_balance?: number;
}

const ACCOUNT_COLORS: Record<string, string> = {
  savings: '#20D9F2',
  current: '#4263FF',
  salary: '#36D399',
  credit_card: '#FB7185',
  investment: '#875BFF',
  loan: '#FBBF24',
  cash: '#10B981',
  other: '#94A3B8',
};

// In-memory mock store for session modifications
let inMemoryAccounts = [...MOCK_ACCOUNTS];

export const accountService = {
  async getAccounts(): Promise<Account[]> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 300));
      return [...inMemoryAccounts];
    }

    try {
      const res = await apiClient.request<{
        success: boolean;
        accounts: any[];
      }>('/accounts');

      if (!res.accounts || res.accounts.length === 0) {
        return [];
      }

      // Optionally enrich with latest balances from analytics
      let balanceMap: Record<number, number> = {};
      try {
        const balRes = await apiClient.request<{
          success: boolean;
          account_balances: any[];
        }>('/analytics/account-balances');

        if (balRes.account_balances) {
          balRes.account_balances.forEach((b) => {
            if (b.account_id && b.latest_recorded_balance !== null && b.latest_recorded_balance !== undefined) {
              balanceMap[b.account_id] = parseFloat(String(b.latest_recorded_balance)) || 0;
            }
          });
        }
      } catch {
        // Balance enrichment failure is non-fatal
      }

      return res.accounts.map((acc) => {
        const balance = balanceMap[acc.account_id] ?? (acc.current_balance !== undefined ? parseFloat(acc.current_balance) : 0);
        const rawMasked = acc.masked_account_number || '';
        const masked = rawMasked.includes('••')
          ? rawMasked
          : rawMasked.length >= 4
          ? `•••• ${rawMasked.slice(-4)}`
          : rawMasked ? `•••• ${rawMasked}` : '•••• 0000';

        return {
          account_id: acc.account_id,
          user_id: acc.user_id,
          account_name: acc.account_name,
          institution_name: acc.institution_name || 'Financial Institution',
          account_type: (acc.account_type || 'other') as AccountType,
          masked_account_number: masked,
          currency: acc.currency || 'INR',
          current_balance: balance,
          available_balance: balance,
          last_synced: acc.created_at ? new Date(acc.created_at).toLocaleDateString() : 'Active',
          color: ACCOUNT_COLORS[acc.account_type] || '#4263FF',
        };
      });
    } catch (err) {
      console.error('[FinWell] Error fetching accounts:', err);
      throw err;
    }
  },

  async getAccountById(id: number): Promise<Account | null> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 200));
      const acc = inMemoryAccounts.find((a) => a.account_id === id);
      return acc || null;
    }

    try {
      const res = await apiClient.request<{
        success: boolean;
        account: any;
      }>(`/accounts/${id}`);

      if (!res.account) return null;
      const acc = res.account;
      return {
        account_id: acc.account_id,
        user_id: acc.user_id,
        account_name: acc.account_name,
        institution_name: acc.institution_name || 'Financial Institution',
        account_type: (acc.account_type || 'other') as AccountType,
        masked_account_number: acc.masked_account_number || '•••• 0000',
        currency: acc.currency || 'INR',
        current_balance: parseFloat(acc.current_balance || '0'),
        available_balance: parseFloat(acc.current_balance || '0'),
        last_synced: acc.created_at ? new Date(acc.created_at).toLocaleDateString() : 'Active',
        color: ACCOUNT_COLORS[acc.account_type] || '#4263FF',
      };
    } catch {
      return null;
    }
  },

  async createAccount(data: CreateAccountDTO): Promise<Account> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 500));
      const newAcc: Account = {
        account_id: Date.now(),
        user_id: 101,
        account_name: data.account_name,
        institution_name: data.institution_name,
        account_type: data.account_type,
        masked_account_number: data.masked_account_number.startsWith('••••')
          ? data.masked_account_number
          : `•••• ${data.masked_account_number.slice(-4)}`,
        currency: data.currency || 'USD',
        current_balance: data.initial_balance || 0,
        available_balance: data.initial_balance || 0,
        last_synced: 'Just now',
        color: ACCOUNT_COLORS[data.account_type] || '#4263FF',
      };
      inMemoryAccounts.unshift(newAcc);
      return newAcc;
    }

    const payload = {
      account_name: data.account_name.trim(),
      institution_name: data.institution_name ? data.institution_name.trim() : null,
      account_type: data.account_type,
      masked_account_number: data.masked_account_number ? data.masked_account_number.trim() : null,
      currency: (data.currency || 'INR').trim().toUpperCase(),
    };

    const res = await apiClient.request<{
      success: boolean;
      message: string;
      user_id: number;
      account_id: number;
    }>('/accounts', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    const created = await this.getAccountById(res.account_id);
    if (created) return created;

    return {
      account_id: res.account_id,
      user_id: res.user_id,
      account_name: data.account_name,
      institution_name: data.institution_name,
      account_type: data.account_type,
      masked_account_number: data.masked_account_number,
      currency: payload.currency,
      current_balance: 0,
      available_balance: 0,
      last_synced: 'Just now',
      color: ACCOUNT_COLORS[data.account_type] || '#4263FF',
    };
  },
};
