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

// In-memory mock store for session modifications
let inMemoryAccounts = [...MOCK_ACCOUNTS];

export const accountService = {
  async getAccounts(): Promise<Account[]> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 300));
      return [...inMemoryAccounts];
    }

    const res = await apiClient.request<{ success: boolean; accounts: Account[] }>('/accounts');
    return res.accounts;
  },

  async getAccountById(id: number): Promise<Account | null> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 200));
      const acc = inMemoryAccounts.find((a) => a.account_id === id);
      return acc || null;
    }

    const res = await apiClient.request<{ success: boolean; account: Account }>(`/accounts/${id}`);
    return res.account;
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
        color: '#4263FF',
      };
      inMemoryAccounts.unshift(newAcc);
      return newAcc;
    }

    const res = await apiClient.request<{ success: boolean; account: Account }>('/accounts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return res.account;
  },
};
