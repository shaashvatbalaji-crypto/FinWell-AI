import React, { useState, useEffect } from 'react';
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  AlertCircle,
  FileCheck2,
  Calendar,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  CreditCard,
  Building,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { StatCard } from '../../components/common/StatCard';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { TiltCard } from '../../components/3d/TiltCard';
import { analyticsService } from '../../services/analytics/analyticsService';
import { accountService } from '../../services/accounts/accountService';
import { transactionService } from '../../services/transactions/transactionService';
import { Account, AnalyticsSummary, MonthlyTrend, CategorySpending, Transaction } from '../../types';
import { NavigationPage } from '../../components/layout/LeftSidebar';

interface DashboardPageProps {
  onNavigate: (page: NavigationPage) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [trends, setTrends] = useState<MonthlyTrend[]>([]);
  const [categories, setCategories] = useState<CategorySpending[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [recentTransactions, setRecentTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    Promise.all([
      analyticsService.getSummary(),
      analyticsService.getMonthlyTrends(),
      analyticsService.getCategorySpending(),
      accountService.getAccounts(),
      transactionService.getTransactions({ sortBy: 'date_desc' }),
    ]).then(([sum, tr, cat, acc, txn]) => {
      setSummary(sum);
      setTrends(tr);
      setCategories(cat);
      setAccounts(acc);
      setRecentTransactions(txn.transactions.slice(0, 5));
      setIsLoading(false);
    });
  }, []);

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header with Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold tracking-tight text-white">
              Financial Command Centre
            </h1>
            <Badge variant="cyan" size="sm">
              Q1 FY26
            </Badge>
          </div>
          <p className="text-xs text-finwell-muted mt-1">
            Real-time multi-account aggregation & neural reconciliation overview.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            icon={<Calendar className="h-3.5 w-3.5 text-finwell-cyan" />}
          >
            March 2026
          </Button>

          <Button
            variant="primary"
            size="sm"
            glow
            onClick={() => onNavigate('ai-chat')}
            icon={<Sparkles className="h-3.5 w-3.5" />}
          >
            Ask FinWell AI
          </Button>
        </div>
      </div>

      {/* Top 4 Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          title="Total Balance"
          value={`$${summary?.total_balance.toLocaleString('en-US', { minimumFractionDigits: 2 }) || '122,330.65'}`}
          change="+8.7%"
          isPositive={true}
          subtitle="across 4 institutions"
          icon={<Wallet className="h-5 w-5" />}
          accentColor="blue"
        />

        <StatCard
          title="Total Income"
          value={`$${summary?.total_income.toLocaleString('en-US', { minimumFractionDigits: 2 }) || '24,800.00'}`}
          change="+12.4%"
          isPositive={true}
          subtitle="vs prior month"
          icon={<TrendingUp className="h-5 w-5" />}
          accentColor="cyan"
        />

        <StatCard
          title="Total Expenses"
          value={`$${summary?.total_expenses.toLocaleString('en-US', { minimumFractionDigits: 2 }) || '9,420.50'}`}
          change="-3.8%"
          isPositive={true}
          subtitle="controlled burn rate"
          icon={<TrendingDown className="h-5 w-5" />}
          accentColor="violet"
        />

        <StatCard
          title="Net Cash Flow"
          value={`+$${summary?.net_cash_flow.toLocaleString('en-US', { minimumFractionDigits: 2 }) || '15,379.50'}`}
          change="62.0% rate"
          isPositive={true}
          subtitle="surplus liquidity"
          icon={<ArrowUpRight className="h-5 w-5" />}
          accentColor="emerald"
        />
      </div>

      {/* Smart Alerts & Reconciliation Banner */}
      <div className="rounded-2xl border border-finwell-warning/30 bg-gradient-to-r from-finwell-warning/10 via-finwell-card to-finwell-surface p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-finwell-warning/20 p-2 text-finwell-warning">
            <AlertCircle className="h-5 w-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              Action Required: 1 Suspected Duplicate Transaction Identified
              <Badge variant="warning" size="sm">
                96% Match
              </Badge>
            </h4>
            <p className="text-xs text-finwell-muted mt-0.5">
              GitHub Copilot Enterprise charged twice ($180.00 × 2) within 4 minutes on Executive Platinum Card.
            </p>
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => onNavigate('reconciliation')}
          className="border-finwell-warning/40 text-finwell-warning hover:bg-finwell-warning/10"
        >
          Review in Reconciliation Centre
        </Button>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Monthly Income vs Expenditure Chart */}
        <TiltCard className="lg:col-span-2 p-6 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-base font-bold text-white">Monthly Cash Flow Trends</h3>
              <p className="text-xs text-finwell-dim mt-0.5">
                Audited monthly inflow versus operational expenditures (USD)
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5 text-finwell-muted">
                <span className="h-2.5 w-2.5 rounded-sm bg-finwell-primary" />
                Income
              </span>
              <span className="flex items-center gap-1.5 text-finwell-muted">
                <span className="h-2.5 w-2.5 rounded-sm bg-finwell-cyan" />
                Expenses
              </span>
            </div>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="incomeGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4263FF" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#4263FF" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="expenseGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#20D9F2" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#20D9F2" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="month" stroke="#656B8A" fontSize={11} tickLine={false} />
                <YAxis stroke="#656B8A" fontSize={11} tickLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#121426',
                    borderColor: 'rgba(66,99,255,0.3)',
                    borderRadius: '8px',
                    color: '#F5F6FF',
                    fontSize: '12px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="income"
                  name="Income"
                  stroke="#4263FF"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#incomeGrad)"
                />
                <Area
                  type="monotone"
                  dataKey="expense"
                  name="Expenses"
                  stroke="#20D9F2"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#expenseGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </TiltCard>

        {/* Category Breakdown Donut */}
        <TiltCard className="p-6 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-white">Spending by Category</h3>
              <p className="text-xs text-finwell-dim mt-0.5">March 2026 Outflows</p>
            </div>
            <Badge variant="primary" size="sm">
              6 Categories
            </Badge>
          </div>

          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categories}
                  dataKey="amount"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={4}
                >
                  {categories.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#121426',
                    borderColor: 'rgba(66,99,255,0.3)',
                    borderRadius: '8px',
                    color: '#F5F6FF',
                    fontSize: '12px',
                  }}
                  formatter={(val: any) => [`$${val.toLocaleString()}`, 'Spent']}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-4 space-y-2 max-h-36 overflow-y-auto pr-1">
            {categories.map((c) => (
              <div key={c.category} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 truncate">
                  <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: c.color }} />
                  <span className="text-finwell-muted truncate">{c.category}</span>
                </div>
                <span className="font-semibold text-white">${c.amount.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </TiltCard>
      </div>

      {/* Account Overview Cards & Recent Transactions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Connected Accounts */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-finwell-cyan" />
              Connected Vaults
            </h3>
            <button
              onClick={() => onNavigate('accounts')}
              className="text-xs text-finwell-primary hover:text-finwell-cyan font-semibold flex items-center gap-1"
            >
              Manage <ArrowRight className="h-3 w-3" />
            </button>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {accounts.map((acc) => (
              <TiltCard key={acc.account_id} className="p-4 bg-finwell-card/80">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-bold text-white">{acc.account_name}</h4>
                    <p className="text-[11px] text-finwell-dim mt-0.5">
                      {acc.institution_name} • {acc.masked_account_number}
                    </p>
                  </div>
                  <span className="text-sm font-extrabold text-white">
                    ${acc.current_balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </span>
                </div>
              </TiltCard>
            ))}
          </div>
        </div>

        {/* Recent Transactions Table */}
        <TiltCard className="lg:col-span-2 p-6 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-white">Recent Transactions</h3>
              <p className="text-xs text-finwell-dim mt-0.5">Audited records synchronized across banks</p>
            </div>
            <button
              onClick={() => onNavigate('transactions')}
              className="text-xs text-finwell-primary hover:text-finwell-cyan font-semibold flex items-center gap-1"
            >
              View All ({recentTransactions.length}+) <ArrowRight className="h-3 w-3" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/5 text-finwell-dim">
                  <th className="pb-3 font-semibold">Date</th>
                  <th className="pb-3 font-semibold">Description</th>
                  <th className="pb-3 font-semibold">Category</th>
                  <th className="pb-3 font-semibold text-right">Amount</th>
                  <th className="pb-3 font-semibold text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {recentTransactions.map((t) => (
                  <tr key={t.transaction_id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 text-finwell-dim font-mono text-[11px]">{t.transaction_date}</td>
                    <td className="py-3 font-medium text-white max-w-[200px] truncate">{t.description}</td>
                    <td className="py-3 text-finwell-muted">{t.category}</td>
                    <td
                      className={`py-3 text-right font-bold ${
                        t.direction === 'credit' ? 'text-finwell-success' : 'text-white'
                      }`}
                    >
                      {t.direction === 'credit' ? '+' : '-'}${t.amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 text-center">
                      <Badge
                        variant={t.status === 'posted' ? 'neutral' : t.status === 'flagged' ? 'warning' : 'cyan'}
                        size="sm"
                      >
                        {t.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TiltCard>
      </div>
    </div>
  );
};
