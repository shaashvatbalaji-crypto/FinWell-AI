import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  ArrowUpDown,
  Download,
  Info,
  Calendar,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { TiltCard } from '../../components/3d/TiltCard';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { Modal } from '../../components/common/Modal';
import { transactionService, TransactionFilters } from '../../services/transactions/transactionService';
import { formatCurrency } from '../../utils/formatters';
import { Transaction } from '../../types';

export const TransactionsPage: React.FC = () => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [selectedTxn, setSelectedTxn] = useState<Transaction | null>(null);

  // Filters
  const [search, setSearch] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [directionFilter, setDirectionFilter] = useState<'all' | 'debit' | 'credit'>('all');
  const [sortBy, setSortBy] = useState<'date_desc' | 'date_asc' | 'amount_desc' | 'amount_asc'>('date_desc');

  // Pagination
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 8;

  const loadTransactions = async () => {
    const res = await transactionService.getTransactions({
      searchTerm: search,
      category: categoryFilter,
      direction: directionFilter,
      sortBy,
    });
    setTransactions(res.transactions);
    setTotalCount(res.count);
  };

  useEffect(() => {
    loadTransactions();
  }, [search, categoryFilter, directionFilter, sortBy]);

  // Derived paginated slice
  const totalPages = Math.max(1, Math.ceil(transactions.length / pageSize));
  const paginatedTransactions = transactions.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const categories = [
    'all',
    'Consulting Income',
    'Cloud Infrastructure & Tech',
    'Internal Transfer',
    'Software Subscriptions',
    'Investment Income',
    'Housing & Utilities',
    'Dining & Entertainment',
  ];

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header & Export */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white flex items-center gap-2">
            Verified Transaction Ledger
            <Badge variant="cyan" size="sm">
              {totalCount} Records
            </Badge>
          </h1>
          <p className="text-xs text-finwell-muted mt-1">
            Normalized double-entry financial events extracted from statements and bank feeds.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => alert('Exporting full ledger to CSV (Demo action)')}
          icon={<Download className="h-4 w-4 text-finwell-cyan" />}
        >
          Export CSV Ledger
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {/* Search Input */}
        <div className="relative md:col-span-2">
          <Search className="absolute left-3.5 top-3 h-4 w-4 text-finwell-dim" />
          <input
            type="text"
            placeholder="Search by description, category, or reference..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-finwell-surface pl-10 pr-4 py-2 text-xs text-white placeholder-finwell-dim focus:border-finwell-primary focus:outline-none"
          />
        </div>

        {/* Category Select */}
        <div>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-finwell-surface px-3 py-2 text-xs text-white focus:border-finwell-primary focus:outline-none"
          >
            {categories.map((c) => (
              <option key={c} value={c}>
                {c === 'all' ? 'All Categories' : c}
              </option>
            ))}
          </select>
        </div>

        {/* Direction & Sort */}
        <div className="flex items-center gap-2">
          <select
            value={directionFilter}
            onChange={(e) => setDirectionFilter(e.target.value as any)}
            className="w-1/2 rounded-xl border border-white/10 bg-finwell-surface px-3 py-2 text-xs text-white focus:border-finwell-primary focus:outline-none"
          >
            <option value="all">All Flows</option>
            <option value="debit">Debits (-)</option>
            <option value="credit">Credits (+)</option>
          </select>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="w-1/2 rounded-xl border border-white/10 bg-finwell-surface px-3 py-2 text-xs text-white focus:border-finwell-primary focus:outline-none"
          >
            <option value="date_desc">Latest Date</option>
            <option value="date_asc">Oldest Date</option>
            <option value="amount_desc">Highest $</option>
            <option value="amount_asc">Lowest $</option>
          </select>
        </div>
      </div>

      {/* Transaction Table */}
      <TiltCard className="p-4 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/10 text-finwell-dim text-[11px] uppercase tracking-wider">
                <th className="pb-3 px-3 font-semibold">Date</th>
                <th className="pb-3 px-3 font-semibold">Description</th>
                <th className="pb-3 px-3 font-semibold">Category</th>
                <th className="pb-3 px-3 font-semibold">Account</th>
                <th className="pb-3 px-3 font-semibold text-right">Debit (-)</th>
                <th className="pb-3 px-3 font-semibold text-right">Credit (+)</th>
                <th className="pb-3 px-3 font-semibold text-center">Status</th>
                <th className="pb-3 px-3 font-semibold text-center">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {paginatedTransactions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-xs text-finwell-dim">
                    No transactions match your query filters.
                  </td>
                </tr>
              ) : (
                paginatedTransactions.map((t) => (
                  <tr
                    key={t.transaction_id}
                    className="hover:bg-white/[0.02] transition-colors cursor-pointer group"
                    onClick={() => setSelectedTxn(t)}
                  >
                    <td className="py-3 px-3 font-mono text-[11px] text-finwell-dim whitespace-nowrap">
                      {t.transaction_date}
                    </td>
                    <td className="py-3 px-3 font-medium text-white max-w-[240px] truncate">
                      {t.description}
                    </td>
                    <td className="py-3 px-3 text-finwell-muted whitespace-nowrap">
                      <span className="inline-flex items-center gap-1.5">
                        <span className="h-1.5 w-1.5 rounded-full bg-finwell-primary" />
                        {t.category}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-finwell-dim whitespace-nowrap">
                      {t.account_name || 'Checking Vault'}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-finwell-danger font-medium whitespace-nowrap">
                      {t.debit ? `-${formatCurrency(t.debit, t.currency)}` : '—'}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-finwell-success font-bold whitespace-nowrap">
                      {t.credit ? `+${formatCurrency(t.credit, t.currency)}` : '—'}
                    </td>
                    <td className="py-3 px-3 text-center whitespace-nowrap">
                      <Badge
                        variant={t.status === 'posted' ? 'neutral' : t.status === 'flagged' ? 'warning' : 'cyan'}
                        size="sm"
                      >
                        {t.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-3 text-center whitespace-nowrap">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedTxn(t);
                        }}
                        className="rounded p-1 text-finwell-dim hover:text-finwell-cyan hover:bg-white/5"
                        title="View transaction metadata"
                      >
                        <Info className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="flex items-center justify-between pt-4 mt-2 border-t border-white/5 text-xs text-finwell-muted px-2">
          <span>
            Showing {(currentPage - 1) * pageSize + 1} to{' '}
            {Math.min(currentPage * pageSize, transactions.length)} of {transactions.length} entries
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="flex items-center gap-1 rounded-lg border border-white/10 px-2.5 py-1 text-xs text-finwell-muted hover:text-white disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="h-3.5 w-3.5" /> Prev
            </button>
            <span className="text-white font-semibold">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="flex items-center gap-1 rounded-lg border border-white/10 px-2.5 py-1 text-xs text-finwell-muted hover:text-white disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Next <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </TiltCard>

      {/* Transaction Details Modal */}
      {selectedTxn && (
        <Modal
          isOpen={!!selectedTxn}
          onClose={() => setSelectedTxn(null)}
          title="Transaction Detail & Ledger Proof"
          subtitle={`Reference ID: ${selectedTxn.reference_number || `TXN-${selectedTxn.transaction_id}`}`}
        >
          <div className="space-y-4">
            <div className="rounded-xl bg-finwell-surface p-4 flex items-center justify-between border border-white/5">
              <div>
                <span className="text-[10px] text-finwell-dim uppercase font-semibold">Processed Amount</span>
                <p
                  className={`text-2xl font-extrabold mt-0.5 font-mono ${
                    selectedTxn.direction === 'credit' ? 'text-finwell-success' : 'text-white'
                  }`}
                >
                  {selectedTxn.direction === 'credit' ? '+' : '-'}{formatCurrency(selectedTxn.amount, selectedTxn.currency)}
                </p>
              </div>
              <Badge variant={selectedTxn.is_reconciled ? 'success' : 'warning'} size="md">
                {selectedTxn.is_reconciled ? 'Reconciled & Sealed' : 'Pending Match'}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-lg bg-finwell-card p-3 border border-white/5">
                <span className="text-finwell-dim text-[10px] uppercase">Transaction Date</span>
                <p className="font-semibold text-white mt-1 font-mono">{selectedTxn.transaction_date}</p>
              </div>

              <div className="rounded-lg bg-finwell-card p-3 border border-white/5">
                <span className="text-finwell-dim text-[10px] uppercase">Account Source</span>
                <p className="font-semibold text-white mt-1">{selectedTxn.account_name || 'Primary Checking'}</p>
              </div>

              <div className="rounded-lg bg-finwell-card p-3 border border-white/5">
                <span className="text-finwell-dim text-[10px] uppercase">Category</span>
                <p className="font-semibold text-white mt-1">{selectedTxn.category}</p>
              </div>

              <div className="rounded-lg bg-finwell-card p-3 border border-white/5">
                <span className="text-finwell-dim text-[10px] uppercase">Balance After Posting</span>
                <p className="font-semibold text-white mt-1 font-mono">
                  {selectedTxn.balance_after ? formatCurrency(selectedTxn.balance_after, selectedTxn.currency) : 'Calculated'}
                </p>
              </div>
            </div>

            <div className="rounded-lg bg-finwell-bg/50 p-3 border border-white/5">
              <span className="text-finwell-dim text-[10px] uppercase">Full Description / Payee</span>
              <p className="text-xs text-white mt-1 font-mono">{selectedTxn.description}</p>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
