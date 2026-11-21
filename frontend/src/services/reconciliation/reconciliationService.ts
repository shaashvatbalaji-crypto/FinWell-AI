import { apiClient } from '../api/apiClient';
import { ReconciliationCase } from '../../types';
import { MOCK_RECONCILIATION_CASES } from '../../mock/mockData';

let inMemoryCases = [...MOCK_RECONCILIATION_CASES];

export const reconciliationService = {
  async getCases(): Promise<ReconciliationCase[]> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 300));
      return [...inMemoryCases];
    }

    const res = await apiClient.request<{
      success: boolean;
      cases: ReconciliationCase[];
    }>('/reconciliation/cases');
    return res.cases;
  },

  async updateCaseStatus(
    caseId: number,
    newStatus: ReconciliationCase['status']
  ): Promise<ReconciliationCase> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 400));
      const idx = inMemoryCases.findIndex((c) => c.case_id === caseId);
      if (idx !== -1) {
        inMemoryCases[idx] = {
          ...inMemoryCases[idx],
          status: newStatus,
        };
        return inMemoryCases[idx];
      }
      throw new Error('Case not found');
    }

    const res = await apiClient.request<{
      success: boolean;
      case: ReconciliationCase;
    }>(`/reconciliation/cases/${caseId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus }),
    });
    return res.case;
  },
};
