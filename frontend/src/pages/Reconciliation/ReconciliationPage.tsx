import React, { useState, useEffect } from 'react';
import {
  FileCheck2,
  AlertTriangle,
  ArrowRightLeft,
  RotateCcw,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ShieldAlert,
  ArrowRight,
  Filter,
} from 'lucide-react';
import { TiltCard } from '../../components/3d/TiltCard';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { reconciliationService } from '../../services/reconciliation/reconciliationService';
import { ReconciliationCase } from '../../types';

export const ReconciliationPage: React.FC = () => {
  const [cases, setCases] = useState<ReconciliationCase[]>([]);
  const [filterType, setFilterType] = useState<string>('all');
  const [actionSuccessMessage, setActionSuccessMessage] = useState<string | null>(null);

  const loadCases = async () => {
    const list = await reconciliationService.getCases();
    setCases(list);
  };

  useEffect(() => {
    loadCases();
  }, []);

  const handleAction = async (caseId: number, newStatus: ReconciliationCase['status'], actionLabel: string) => {
    await reconciliationService.updateCaseStatus(caseId, newStatus);
    await loadCases();
    setActionSuccessMessage(`Case #${caseId} marked as ${actionLabel} (Simulated state change).`);
    setTimeout(() => setActionSuccessMessage(null), 3000);
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

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header & Disclaimer */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white flex items-center gap-2">
            Reconciliation & Audit Command
            <Badge variant="warning" size="sm">
              {cases.filter((c) => c.status === 'needs_review' || c.status === 'suggested').length} Pending Review
            </Badge>
          </h1>
          <p className="text-xs text-finwell-muted mt-1">
            Autonomous heuristic matcher detecting duplicates, mirror inter-account transfers, and refunds.
          </p>
        </div>

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

      {/* Action Notification Alert */}
      {actionSuccessMessage && (
        <div className="rounded-xl border border-finwell-success/30 bg-finwell-success/10 p-3.5 text-xs text-finwell-success flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4" />
          <span>{actionSuccessMessage}</span>
        </div>
      )}

      {/* Cases List */}
      <div className="space-y-6">
        {filteredCases.map((rc) => {
          const isResolved = rc.status === 'confirmed' || rc.status === 'rejected';

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
                    <p className="text-sm font-bold text-finwell-cyan">{rc.confidence_score}%</p>
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
                    <span className="text-finwell-muted">{rc.source_transaction.account_name}</span>
                    <span
                      className={`font-mono font-bold ${
                        rc.source_transaction.direction === 'credit' ? 'text-finwell-success' : 'text-finwell-danger'
                      }`}
                    >
                      {rc.source_transaction.direction === 'credit' ? '+' : '-'}${rc.source_transaction.amount.toFixed(2)}
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
                      <span className="text-finwell-muted">{rc.target_transaction.account_name}</span>
                      <span
                        className={`font-mono font-bold ${
                          rc.target_transaction.direction === 'credit' ? 'text-finwell-success' : 'text-finwell-danger'
                        }`}
                      >
                        {rc.target_transaction.direction === 'credit' ? '+' : '-'}${rc.target_transaction.amount.toFixed(2)}
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

              {/* Action Buttons */}
              <div className="pt-2 flex flex-wrap items-center justify-between gap-3">
                <span className="text-[11px] text-finwell-dim italic">
                  * Note: Review actions run on simulated state. Ready for integration with backend reconciliation storage.
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
                        Dismiss Flag
                      </Button>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleAction(rc.case_id, 'needs_review', 'Flagged for CPA Audit')}
                        icon={<HelpCircle className="h-3.5 w-3.5 text-finwell-warning" />}
                      >
                        Mark for Manual Audit
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
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleAction(rc.case_id, 'needs_review', 'Reopened')}
                    >
                      Reopen Case
                    </Button>
                  )}
                </div>
              </div>
            </TiltCard>
          );
        })}
      </div>
    </div>
  );
};
