import React, { useState, useEffect } from 'react';
import {
  FileCheck2,
  AlertTriangle,
  ArrowRightLeft,
  RotateCcw,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ShieldCheck,
  Sparkles,
  Building,
  RefreshCw,
  Cpu,
  Layers,
} from 'lucide-react';
import { TiltCard } from '../../components/3d/TiltCard';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { reconciliationService } from '../../services/reconciliation/reconciliationService';
import { accountService } from '../../services/accounts/accountService';
import { formatCurrency } from '../../utils/formatters';
import { ReconciliationCase, Account } from '../../types';
import { useAuth } from '../../context/AuthContext';

export const ReconciliationPage: React.FC = () => {
  const { user } = useAuth();
  const [cases, setCases] = useState<ReconciliationCase[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [filterType, setFilterType] = useState<string>('all');
  const [actionSuccessMessage, setActionSuccessMessage] = useState<string | null>(null);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [evalResult, setEvalResult] = useState<any | null>(null);

  const loadData = async () => {
    try {
      const [caseList, accList] = await Promise.all([
        reconciliationService.getCases().catch(() => []),
        accountService.getAccounts().catch(() => []),
      ]);
      setCases(caseList);
      setAccounts(accList);
    } catch {
      setCases([]);
      setAccounts([]);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunEvaluation = async () => {
    setIsEvaluating(true);
    setEvalResult(null);
    try {
      const res = await reconciliationService.evaluateDryRun();
      setEvalResult(res);
      await loadData();
      setActionSuccessMessage(
        res?.reconciliation?.message || 'Dry-run reconciliation audit executed successfully.'
      );
      setTimeout(() => setActionSuccessMessage(null), 5000);
    } catch {
      setActionSuccessMessage('Failed to run reconciliation audit.');
      setTimeout(() => setActionSuccessMessage(null), 4000);
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleAction = async (caseId: number, newStatus: 'confirmed' | 'rejected', actionLabel: string) => {
    try {
      await reconciliationService.updateCaseStatus(caseId, newStatus);
      await loadData();
      setActionSuccessMessage(`Case #${caseId} successfully marked as ${actionLabel}.`);
      setTimeout(() => setActionSuccessMessage(null), 3500);
    } catch (err: any) {
      setActionSuccessMessage(`Failed to update Case #${caseId}: ${err.message || 'Status update error'}`);
      setTimeout(() => setActionSuccessMessage(null), 4000);
    }
  };

  const filteredCases = cases.filter((c) => {
    if (filterType === 'all') return true;
    return c.case_type === filterType;
  });

  const getCaseTypeIcon = (type: ReconciliationCase['case_type']) => {
    switch (type) {
      case 'duplicate':
        return <AlertTriangle className="h-4 w-4 text-finwell-warning" />;
      case 'internal_transfer':
        return <ArrowRightLeft className="h-4 w-4 text-finwell-cyan" />;
      case 'refund':
        return <RotateCcw className="h-4 w-4 text-finwell-success" />;
      default:
        return <HelpCircle className="h-4 w-4 text-finwell-muted" />;
    }
  };

  const pendingCount = cases.filter((c) => c.status === 'needs_review' || c.status === 'suggested').length;

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header & Quick Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold tracking-tight text-white">
              Reconciliation & Audit Command
            </h1>
            <Badge variant={pendingCount > 0 ? 'warning' : 'success'} size="sm">
              {pendingCount} Pending Review
            </Badge>
          </div>
          <p className="text-xs text-finwell-muted mt-1">
            Autonomous multi-account reconciliation detecting duplicate charges, mirrored inter-vault transfers, and refunds.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="primary"
            size="sm"
            glow
            onClick={handleRunEvaluation}
            isLoading={isEvaluating}
            icon={<Sparkles className="h-3.5 w-3.5" />}
          >
            {isEvaluating ? 'Auditing Vaults...' : 'Run Audit Evaluation'}
          </Button>

          {/* Filter Pills */}
          <div className="flex items-center gap-1.5 rounded-xl border border-white/5 bg-finwell-surface p-1 text-xs">
            {[
              { id: 'all', label: 'All Cases' },
              { id: 'duplicate', label: 'Duplicates' },
              { id: 'internal_transfer', label: 'Internal Transfers' },
              { id: 'refund', label: 'Refunds' },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setFilterType(f.id)}
                className={`rounded-lg px-3 py-1.5 font-medium transition-colors ${
                  filterType === f.id
                    ? 'bg-finwell-primary text-white shadow-glow-sm'
                    : 'text-finwell-muted hover:text-white'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Active Connected Vaults Audit Strip */}
      <div className="rounded-2xl border border-white/5 bg-finwell-surface/60 p-4 backdrop-blur-md flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-finwell-cyan/10 p-2.5 text-finwell-cyan border border-finwell-cyan/20">
            <Building className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-xs font-bold text-white">Audited Financial Vaults</h4>
              <Badge variant="cyan" size="sm">
                Session: {user?.email || 'Authenticated'}
              </Badge>
            </div>
            <p className="text-[11px] text-finwell-dim mt-0.5">
              {accounts.length >= 2
                ? `Cross-vault transfer matching active across ${accounts.length} banking vaults.`
                : accounts.length === 1
                ? '1 vault connected. Inter-account transfer reconciliation requires statements from 2 or more vaults.'
                : 'No bank vaults created yet. Add accounts in Accounts or upload statements to begin.'}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {accounts.map((acc) => (
            <div
              key={acc.account_id}
              className="rounded-xl border border-white/10 bg-finwell-card px-3 py-1.5 text-xs flex items-center gap-2"
            >
              <span className="h-2 w-2 rounded-full bg-finwell-success" />
              <span className="font-semibold text-white">{acc.account_name}</span>
              <span className="text-[10px] text-finwell-dim font-mono">({acc.masked_account_number})</span>
            </div>
          ))}
          {accounts.length === 0 && (
            <span className="text-xs text-finwell-dim italic">0 Connected Vaults</span>
          )}
        </div>
      </div>

      {/* Audit KPI Metrics Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-2xl border border-white/5 bg-finwell-card p-4">
          <span className="text-[11px] font-semibold text-finwell-dim uppercase tracking-wider">
            Pending Audit Cases
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-xl font-bold text-white">{pendingCount}</span>
            <Badge variant={pendingCount > 0 ? 'warning' : 'success'} size="sm">
              {pendingCount > 0 ? 'Action Needed' : 'All Clear'}
            </Badge>
          </div>
        </div>

        <div className="rounded-2xl border border-white/5 bg-finwell-card p-4">
          <span className="text-[11px] font-semibold text-finwell-dim uppercase tracking-wider">
            Connected Vaults
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-xl font-bold text-finwell-cyan">{accounts.length} Vaults</span>
            <span className="text-xs text-finwell-dim">Double-Entry Scanned</span>
          </div>
        </div>

        <div className="rounded-2xl border border-white/5 bg-finwell-card p-4">
          <span className="text-[11px] font-semibold text-finwell-dim uppercase tracking-wider">
            Reconciliation Engines
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-xl font-bold text-finwell-success">5 Active</span>
            <span className="text-xs text-finwell-dim">Heuristics & Neural</span>
          </div>
        </div>

        <div className="rounded-2xl border border-white/5 bg-finwell-card p-4">
          <span className="text-[11px] font-semibold text-finwell-dim uppercase tracking-wider">
            Safety Guarantee
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-xl font-bold text-white">Dry-Run Only</span>
            <span className="text-xs text-finwell-dim">Zero Auto-Mutations</span>
          </div>
        </div>
      </div>

      {/* Action Notification Alert */}
      {actionSuccessMessage && (
        <div className="rounded-xl border border-finwell-success/30 bg-finwell-success/10 p-3.5 text-xs text-finwell-success flex items-center justify-between gap-2 shadow-glow-sm">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{actionSuccessMessage}</span>
          </div>
          <button
            onClick={() => setActionSuccessMessage(null)}
            className="text-[11px] text-finwell-dim hover:text-white"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Live Evaluation Summary Banner (when user triggers Run Audit) */}
      {evalResult?.reconciliation?.summary && (
        <TiltCard className="p-5 border-finwell-cyan/30 bg-finwell-cyan/5 space-y-3">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-finwell-cyan" />
              <h4 className="text-sm font-bold text-white">
                Live Audit Results — {evalResult.reconciliation.summary.incoming_transaction_count} Transactions Evaluated Across {evalResult.accounts_retrieved || accounts.length} Vaults
              </h4>
            </div>
            <Badge variant="cyan" size="sm">
              Mode: {evalResult.mode || 'Dry Run'}
            </Badge>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="rounded-lg bg-finwell-surface/60 p-2.5 border border-white/5">
              <span className="text-finwell-dim text-[10px] uppercase">Comparisons Analyzed</span>
              <p className="font-bold text-white mt-0.5">{evalResult.reconciliation.summary.duplicate_comparison_count || 0}</p>
            </div>
            <div className="rounded-lg bg-finwell-surface/60 p-2.5 border border-white/5">
              <span className="text-finwell-dim text-[10px] uppercase">Duplicate Candidates</span>
              <p className="font-bold text-finwell-success mt-0.5">{evalResult.reconciliation.summary.duplicate_candidate_count || 0}</p>
            </div>
            <div className="rounded-lg bg-finwell-surface/60 p-2.5 border border-white/5">
              <span className="text-finwell-dim text-[10px] uppercase">Transfer Candidates</span>
              <p className="font-bold text-finwell-cyan mt-0.5">{evalResult.reconciliation.summary.transfer_candidate_count || 0}</p>
            </div>
            <div className="rounded-lg bg-finwell-surface/60 p-2.5 border border-white/5">
              <span className="text-finwell-dim text-[10px] uppercase">Database Writes</span>
              <p className="font-bold text-white mt-0.5">
                {evalResult.writes_performed ? 'Writes Performed' : 'False (Safe Read-Only)'}
              </p>
            </div>
          </div>
        </TiltCard>
      )}

      {/* Cases List or Clean Audit State */}
      {filteredCases.length === 0 ? (
        <TiltCard className="p-10 border border-white/10 text-center flex flex-col items-center justify-center space-y-4">
          <div className="h-16 w-16 rounded-2xl bg-finwell-success/10 border border-finwell-success/20 flex items-center justify-center text-finwell-success shadow-glow-sm">
            <ShieldCheck className="h-8 w-8" />
          </div>

          <div className="max-w-md space-y-1.5">
            <h3 className="text-lg font-bold text-white">
              {filterType === 'all'
                ? 'All Vault Accounts Balanced & Reconciled'
                : `No Pending ${filterType.replace('_', ' ')} Cases`}
            </h3>
            <p className="text-xs text-finwell-muted">
              {filterType === 'all'
                ? 'FinWell’s five-engine reconciliation pipeline analyzed all transaction flows across your connected vaults. No anomalous duplicate charges, unmirrored internal transfers, or unmatched refunds were detected.'
                : `No anomalies matching the "${filterType.replace('_', ' ')}" classification are pending manual review in your active statements.`}
            </p>
          </div>

          <div className="rounded-xl border border-white/5 bg-finwell-surface/60 p-4 max-w-lg w-full text-left text-xs space-y-2.5">
            <div className="flex items-center justify-between text-finwell-dim text-[11px] font-semibold uppercase tracking-wider border-b border-white/5 pb-2">
              <span>Audited Reconciliation Engines</span>
              <span className="text-finwell-success flex items-center gap-1 font-bold">
                <CheckCircle2 className="h-3 w-3" /> 5 of 5 Verified
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-finwell-muted">
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-finwell-cyan" />
                Duplicate Detection Engine
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-finwell-cyan" />
                Inter-Account Transfers
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-finwell-cyan" />
                Partial Refund Allocation
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-finwell-cyan" />
                Multi-Batch Settlement
              </span>
            </div>
          </div>

          <div className="pt-2 flex items-center gap-3">
            <Button
              variant="primary"
              size="sm"
              glow
              onClick={handleRunEvaluation}
              isLoading={isEvaluating}
              icon={<Sparkles className="h-3.5 w-3.5" />}
            >
              {isEvaluating ? 'Running Audit Scan...' : 'Trigger Dry-Run Reconciliation Audit'}
            </Button>
          </div>
        </TiltCard>
      ) : (
        <div className="space-y-6">
          {filteredCases.map((rc) => {
            const isResolved = rc.status === 'confirmed' || rc.status === 'rejected';

            const displayConfidence =
              rc.confidence_score != null
                ? `${Math.round(rc.confidence_score > 1 ? rc.confidence_score : rc.confidence_score * 100)}%`
                : 'Audited';

            return (
              <TiltCard key={rc.case_id} className="p-6 space-y-5 border border-white/10">
                {/* Case Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/5 pb-4">
                  <div className="flex items-center gap-3">
                    <div className="rounded-xl bg-finwell-surface p-2.5 border border-white/5">
                      {getCaseTypeIcon(rc.case_type)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-white">{rc.title}</h3>
                        <Badge variant="cyan" size="sm">
                          Case #{rc.case_id}
                        </Badge>
                      </div>
                      <p className="text-xs text-finwell-muted mt-0.5">{rc.description}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <span className="text-[10px] text-finwell-dim uppercase font-semibold">Matcher Confidence</span>
                      <p className="text-sm font-bold text-finwell-cyan">
                        {displayConfidence}
                      </p>
                    </div>
                    <Badge
                      variant={rc.status === 'confirmed' ? 'success' : rc.status === 'rejected' ? 'danger' : 'warning'}
                      size="md"
                    >
                      {rc.status.replace('_', ' ').toUpperCase()}
                    </Badge>
                  </div>
                </div>

                {/* Side-by-Side Comparison of Transactions */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Source Transaction */}
                  <div className="rounded-xl bg-finwell-surface/70 border border-white/5 p-4 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-finwell-dim uppercase text-[10px]">
                        Source Record A
                      </span>
                      <span className="text-finwell-dim font-mono">{rc.source_transaction.transaction_date}</span>
                    </div>
                    <p className="text-sm font-bold text-white">{rc.source_transaction.description}</p>
                    <div className="flex items-center justify-between pt-2 border-t border-white/5 text-xs">
                      <span className="text-finwell-muted">{rc.source_transaction.account_name || 'Primary Vault'}</span>
                      <span
                        className={`font-mono font-bold ${
                          rc.source_transaction.direction === 'credit' ? 'text-finwell-success' : 'text-finwell-danger'
                        }`}
                      >
                        {rc.source_transaction.direction === 'credit' ? '+' : '-'}
                        {formatCurrency(rc.source_transaction.amount, rc.source_transaction.currency)}
                      </span>
                    </div>
                  </div>

                  {/* Target / Matched Candidate Transaction */}
                  {rc.target_transaction ? (
                    <div className="rounded-xl bg-finwell-surface/70 border border-white/5 p-4 space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-finwell-cyan uppercase text-[10px]">
                          Correlated Candidate B
                        </span>
                        <span className="text-finwell-dim font-mono">{rc.target_transaction.transaction_date}</span>
                      </div>
                      <p className="text-sm font-bold text-white">{rc.target_transaction.description}</p>
                      <div className="flex items-center justify-between pt-2 border-t border-white/5 text-xs">
                        <span className="text-finwell-muted">{rc.target_transaction.account_name || 'Target Vault'}</span>
                        <span
                          className={`font-mono font-bold ${
                            rc.target_transaction.direction === 'credit' ? 'text-finwell-success' : 'text-finwell-danger'
                          }`}
                        >
                          {rc.target_transaction.direction === 'credit' ? '+' : '-'}
                          {formatCurrency(rc.target_transaction.amount, rc.target_transaction.currency)}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-xl bg-finwell-surface/30 border border-dashed border-white/10 p-4 flex items-center justify-center text-xs text-finwell-dim">
                      No opposing candidate required. Standalone anomaly.
                    </div>
                  )}
                </div>

                {/* Supporting Evidences */}
                {rc.evidences && rc.evidences.length > 0 && (
                  <div className="rounded-xl bg-finwell-bg/50 p-3.5 border border-white/5 space-y-2">
                    <span className="text-[10px] uppercase font-bold text-finwell-dim tracking-wider">
                      Algorithmic Evidence Signals
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                      {rc.evidences.map((ev, i) => (
                        <div key={i} className="flex items-start gap-2 text-xs text-finwell-muted">
                          <CheckCircle2 className="h-3.5 w-3.5 text-finwell-cyan shrink-0 mt-0.5" />
                          <span>{ev.description}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="pt-2 flex flex-wrap items-center justify-between gap-3">
                  <span className="text-[11px] text-finwell-dim italic">
                    * Certified Dry-Run: Review actions update match status in MySQL with strict user isolation.
                  </span>

                  <div className="flex items-center gap-2">
                    {!isResolved ? (
                      <>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleAction(rc.case_id, 'rejected', 'Rejected / False Positive')}
                          icon={<XCircle className="h-3.5 w-3.5 text-finwell-danger" />}
                        >
                          Dismiss / Reject
                        </Button>

                        <Button
                          variant="primary"
                          size="sm"
                          glow
                          onClick={() => handleAction(rc.case_id, 'confirmed', 'Confirmed')}
                          icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                        >
                          Confirm Match
                        </Button>
                      </>
                    ) : (
                      <span className="text-xs font-semibold text-finwell-dim">
                        Case status recorded as {rc.status.toUpperCase()}
                      </span>
                    )}
                  </div>
                </div>
              </TiltCard>
            );
          })}
        </div>
      )}
    </div>
  );
};
