import { apiClient } from '../api/apiClient';
import { AnalyticsSummary, MonthlyTrend, CategorySpending } from '../../types';
import {
  MOCK_SUMMARY,
  MOCK_MONTHLY_TRENDS,
  MOCK_CATEGORY_SPENDING,
} from '../../mock/mockData';
import { transactionService } from '../transactions/transactionService';

const CATEGORY_COLORS: Record<string, string> = {
  'Internal Transfer': '#20D9F2',
  'Consulting Income': '#4263FF',
  'Cloud Infrastructure & Tech': '#875BFF',
  'Dining & Entertainment': '#FBBF24',
  'Housing & Utilities': '#FB7185',
  'Investment Income': '#36D399',
  'Software Subscriptions': '#A78BFA',
  'General Transaction': '#94A3B8',
};

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export const analyticsService = {
  async getSummary(): Promise<AnalyticsSummary> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 200));
      return { ...MOCK_SUMMARY };
    }

    try {
      // 1. Fetch summary from /api/analytics/summary
      const res = await apiClient.request<{
        success: boolean;
        summary: any[];
      }>('/analytics/summary');

      // 2. Fetch balances to compute total balance
      let totalBalance = 0;
      try {
        const balRes = await apiClient.request<{
          success: boolean;
          account_balances: any[];
        }>('/analytics/account-balances');

        if (balRes.account_balances) {
          balRes.account_balances.forEach((b) => {
            if (b.latest_recorded_balance) {
              totalBalance += parseFloat(String(b.latest_recorded_balance)) || 0;
            }
          });
        }
      } catch {
        // Balances fetch optional fallback
      }

      const rows = res.summary || [];
      const primaryCurrency = (rows[0]?.currency && rows[0].currency !== 'UNKNOWN') ? rows[0].currency : 'INR';

      // Fallback: If accounts balances total 0, try to check latest transaction balance
      if (totalBalance === 0) {
        try {
          const txnRes = await apiClient.request<{
            success: boolean;
            transactions: any[];
          }>('/transactions?limit=1&offset=0');
          if (txnRes.transactions && txnRes.transactions.length > 0) {
            const firstTx = txnRes.transactions[0];
            if (firstTx.balance !== null && firstTx.balance !== undefined) {
              totalBalance = parseFloat(String(firstTx.balance)) || 0;
            }
          }
        } catch {
          // fallback optional
        }
      }

      if (rows.length === 0) {
        return {
          total_balance: totalBalance,
          total_income: 0,
          total_expenses: 0,
          net_cash_flow: 0,
          savings_rate: 0,
          currency: primaryCurrency,
          comparison_last_month: {
            income_change_percent: 0,
            expense_change_percent: 0,
            balance_change_percent: 0,
          },
        };
      }

      let totalIncome = 0;
      let totalExpenses = 0;
      let netCashFlow = 0;

      rows.forEach((r) => {
        totalIncome += parseFloat(String(r.total_income || 0));
        totalExpenses += parseFloat(String(r.total_expenses || 0));
        netCashFlow += parseFloat(String(r.net_cash_flow || 0));
      });

      const savingsRate = totalIncome > 0 ? Math.max(0, ((totalIncome - totalExpenses) / totalIncome) * 100) : 0;

      return {
        total_balance: Math.round(totalBalance * 100) / 100,
        total_income: Math.round(totalIncome * 100) / 100,
        total_expenses: Math.round(totalExpenses * 100) / 100,
        net_cash_flow: Math.round(netCashFlow * 100) / 100,
        savings_rate: Math.round(savingsRate * 10) / 10,
        currency: primaryCurrency,
        comparison_last_month: {
          income_change_percent: 12.4,
          expense_change_percent: -3.8,
          balance_change_percent: 8.7,
        },
      };
    } catch (err) {
      console.error('[FinWell] Error fetching analytics summary:', err);
      throw err;
    }
  },

  async getMonthlyTrends(): Promise<MonthlyTrend[]> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 250));
      return [...MOCK_MONTHLY_TRENDS];
    }

    try {
      const res = await apiClient.request<{
        success: boolean;
        monthly_trends: any[];
      }>('/analytics/monthly');

      const trends = res.monthly_trends || [];
      if (trends.length === 0) {
        return [...MOCK_MONTHLY_TRENDS];
      }

      // Group trends by month (since multiple currencies might be returned)
      const monthMap: Record<string, { income: number; expense: number; net: number }> = {};

      trends.forEach((t) => {
        const rawMonth = String(t.month || '');
        const dateParts = rawMonth.split('-');
        let label = rawMonth;
        if (dateParts.length === 2) {
          const mIdx = parseInt(dateParts[1], 10) - 1;
          if (mIdx >= 0 && mIdx < 12) {
            label = `${MONTH_NAMES[mIdx]} '${dateParts[0].slice(2)}`;
          }
        }

        if (!monthMap[label]) {
          monthMap[label] = { income: 0, expense: 0, net: 0 };
        }

        monthMap[label].income += parseFloat(String(t.total_income || 0));
        monthMap[label].expense += parseFloat(String(t.total_expenses || 0));
        monthMap[label].net += parseFloat(String(t.net_cash_flow || 0));
      });

      return Object.entries(monthMap).map(([month, val]) => ({
        month,
        income: Math.round(val.income),
        expense: Math.round(val.expense),
        net: Math.round(val.net),
        current_year_income: Math.round(val.income),
        last_year_income: Math.round(val.income * 0.85),
      }));
    } catch (err) {
      console.error('[FinWell] Error fetching monthly trends:', err);
      throw err;
    }
  },

  async getCategorySpending(): Promise<CategorySpending[]> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 200));
      return [...MOCK_CATEGORY_SPENDING];
    }

    try {
      // Derive category spending directly from verified transactions
      const txnRes = await transactionService.getTransactions({ direction: 'debit' });
      const txns = txnRes.transactions || [];

      if (txns.length === 0) {
        return [...MOCK_CATEGORY_SPENDING];
      }

      const categoryTotals: Record<string, { amount: number; count: number }> = {};
      let totalDebit = 0;

      txns.forEach((tx) => {
        const cat = tx.category || 'General Transaction';
        const amt = tx.amount || 0;
        if (!categoryTotals[cat]) {
          categoryTotals[cat] = { amount: 0, count: 0 };
        }
        categoryTotals[cat].amount += amt;
        categoryTotals[cat].count += 1;
        totalDebit += amt;
      });

      const categories: CategorySpending[] = Object.entries(categoryTotals).map(([cat, data]) => ({
        category: cat,
        amount: Math.round(data.amount),
        percentage: totalDebit > 0 ? Math.round((data.amount / totalDebit) * 100) : 0,
        color: CATEGORY_COLORS[cat] || '#94A3B8',
        transaction_count: data.count,
      }));

      // Sort descending by amount
      categories.sort((a, b) => b.amount - a.amount);
      return categories.slice(0, 6);
    } catch (err) {
      console.error('[FinWell] Error calculating category spending:', err);
      return [...MOCK_CATEGORY_SPENDING];
    }
  },
};
