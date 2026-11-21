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

    try {
      const res = await apiClient.request<{
        success: boolean;
        count: number;
        cases: ReconciliationCase[];
      }>('/reconciliation/cases');
      return res.cases || [];
    } catch (err) {
      console.error('[FinWell] Error fetching reconciliation cases:', err);
      throw err;
    }
  },

  async updateCaseStatus(
    caseId: number,
    newStatus: ReconciliationCase['status']
  ): Promise<{ case_id: number; status: ReconciliationCase['status'] }> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 400));
      const idx = inMemoryCases.findIndex((c) => c.case_id === caseId);
      if (idx !== -1) {
        inMemoryCases[idx] = {
          ...inMemoryCases[idx],
          status: newStatus,
        };
        return { case_id: caseId, status: newStatus };
      }
      throw new Error('Case not found');
    }

    const res = await apiClient.request<{
      success: boolean;
      match_id: number;
      new_status: ReconciliationCase['status'];
      message?: string;
    }>(`/reconciliation/cases/${caseId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus }),
    });

    return { case_id: res.match_id, status: res.new_status };
  },

  async evaluateDryRun(): Promise<any> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 500));
      return { success: true, mode: 'mock_dry_run', writes_performed: false };
    }

    return await apiClient.request('/reconciliation/evaluate', {
      method: 'POST',
    });
  },
};
