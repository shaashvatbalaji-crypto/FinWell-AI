import { apiClient } from '../api/apiClient';
import { AnalyticsSummary, MonthlyTrend, CategorySpending } from '../../types';
import {
  MOCK_SUMMARY,
  MOCK_MONTHLY_TRENDS,
  MOCK_CATEGORY_SPENDING,
} from '../../mock/mockData';

export const analyticsService = {
  async getSummary(): Promise<AnalyticsSummary> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 200));
      return { ...MOCK_SUMMARY };
    }

    const res = await apiClient.request<{ success: boolean; summary: AnalyticsSummary }>(
      '/analytics/summary'
    );
    return res.summary;
  },

  async getMonthlyTrends(): Promise<MonthlyTrend[]> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 250));
      return [...MOCK_MONTHLY_TRENDS];
    }

    const res = await apiClient.request<{
      success: boolean;
      monthly_trends: MonthlyTrend[];
    }>('/analytics/monthly');
    return res.monthly_trends;
  },

  async getCategorySpending(): Promise<CategorySpending[]> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 200));
      return [...MOCK_CATEGORY_SPENDING];
    }

    return [...MOCK_CATEGORY_SPENDING];
  },
};
