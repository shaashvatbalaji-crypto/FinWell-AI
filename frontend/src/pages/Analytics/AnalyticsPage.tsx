import React, { useState, useEffect } from 'react';
import {
  Calendar,
  Download,
  TrendingUp,
  TrendingDown,
  PieChart as PieChartIcon,
  BarChart3,
  Filter,
  DollarSign,
  ArrowUpRight,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { TiltCard } from '../../components/3d/TiltCard';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { analyticsService } from '../../services/analytics/analyticsService';
import { MonthlyTrend, CategorySpending, AnalyticsSummary } from '../../types';

export const AnalyticsPage: React.FC = () => {
  const [dateFilter, setDateFilter] = useState<'30d' | '3m' | '6m' | 'year' | 'custom'>('year');
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [trends, setTrends] = useState<MonthlyTrend[]>([]);
  const [categories, setCategories] = useState<CategorySpending[]>([]);
  const [metricTab, setMetricTab] = useState<'cashflow' | 'income_comparison' | 'category_breakdown'>('cashflow');

  useEffect(() => {
    Promise.all([
      analyticsService.getSummary(),
      analyticsService.getMonthlyTrends(),
      analyticsService.getCategorySpending(),
    ]).then(([sum, tr, cat]) => {
      setSummary(sum);
      setTrends(tr);
      setCategories(cat);
    });
  }, []);

  // Filter trends based on active date range
  const filteredTrends = React.useMemo(() => {
    if (dateFilter === '30d') return trends.slice(-1);
    if (dateFilter === '3m') return trends.slice(-3);
    if (dateFilter === '6m') return trends.slice(-6);
    return trends;
  }, [trends, dateFilter]);

  const incomeSources = [
    { name: 'Enterprise AI Consulting', amount: 165000, percentage: 61, color: '#4263FF' },
    { name: 'Index & Dividend Distributions', amount: 48200, percentage: 18, color: '#20D9F2' },
    { name: 'SaaS Software Royalties', amount: 35000, percentage: 13, color: '#875BFF' },
    { name: 'Treasury Yield & Staking', amount: 21600, percentage: 8, color: '#36D399' },
  ];

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-7xl mx-auto">
      {/* Top Header & Range Filters */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white flex items-center gap-2">
            Financial Analytics & Forecasting
            <Badge variant="cyan" size="sm">
              Audited
            </Badge>
          </h1>
          <p className="text-xs text-finwell-muted mt-1">
            Deep-dive multi-period liquidity velocity, category concentration, and cash margins.
          </p>
        </div>

        {/* Date Filter Pills */}
        <div className="flex items-center gap-1.5 rounded-xl border border-white/5 bg-finwell-surface p-1 text-xs">
          {(['30d', '3m', '6m', 'year', 'custom'] as const).map((filter) => {
            const labelMap = {
              '30d': 'Last 30 days',
              '3m': 'Last 3 months',
              '6m': 'Last 6 months',
              year: 'This year',
              custom: 'Custom',
            };
            const isActive = dateFilter === filter;
            return (
              <button
                key={filter}
                onClick={() => setDateFilter(filter)}
                className={`rounded-lg px-3 py-1.5 font-medium transition-colors ${
                  isActive
                    ? 'bg-finwell-primary text-white shadow-glow-sm'
                    : 'text-finwell-muted hover:text-white'
                }`}
              >
                {labelMap[filter]}
              </button>
            );
          })}
        </div>
      </div>

      {/* Analytics KPI Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-2xl border border-white/5 bg-finwell-card p-4">
          <span className="text-[11px] font-semibold text-finwell-dim uppercase tracking-wider">
            Gross Inflow (YTD)
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-xl font-bold text-white">$310,300.00</span>
            <span className="text-xs font-semibold text-finwell-success flex items-center">
              <ArrowUpRight className="h-3.5 w-3.5" /> +14.2%
            </span>
          </div>
        </div>

        <div className="rounded-2xl border border-white/5 bg-finwell-card p-4">
          <span className="text-[11px] font-semibold text-finwell-dim uppercase tracking-wider">
            Operational Outflow (YTD)
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-xl font-bold text-white">$123,520.50</span>
            <span className="text-xs font-semibold text-finwell-cyan flex items-center">
              <ArrowUpRight className="h-3.5 w-3.5" /> +3.1%
            </span>
          </div>
        </div>

        <div className="rounded-2xl border border-white/5 bg-finwell-card p-4">
          <span className="text-[11px] font-semibold text-finwell-dim uppercase tracking-wider">
            Net Operating Surplus
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-xl font-bold text-finwell-success">+$186,779.50</span>
            <span className="text-xs font-semibold text-finwell-dim">60.2% Net Margin</span>
          </div>
        </div>

        <div className="rounded-2xl border border-white/5 bg-finwell-card p-4">
          <span className="text-[11px] font-semibold text-finwell-dim uppercase tracking-wider">
            Monthly Volatility Index
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-xl font-bold text-white">4.2%</span>
            <span className="text-xs font-semibold text-finwell-success">Low Variance</span>
          </div>
        </div>
      </div>

      {/* Primary Analytics Section with Tab Switcher */}
      <TiltCard className="p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 border-b border-white/5 pb-4">
          <div>
            <h3 className="text-base font-bold text-white">Macro Cash Dynamics</h3>
            <p className="text-xs text-finwell-dim mt-0.5">
              Comprehensive trend evaluation with annual baseline overlay
            </p>
          </div>

          <div className="flex items-center gap-1.5 rounded-xl border border-white/5 bg-finwell-surface p-1 text-xs">
            <button
              onClick={() => setMetricTab('cashflow')}
              className={`rounded-lg px-3 py-1 font-medium ${
                metricTab === 'cashflow' ? 'bg-finwell-primary text-white shadow-glow-sm' : 'text-finwell-muted'
              }`}
            >
              Cash Flow
            </button>
            <button
              onClick={() => setMetricTab('income_comparison')}
              className={`rounded-lg px-3 py-1 font-medium ${
                metricTab === 'income_comparison' ? 'bg-finwell-primary text-white shadow-glow-sm' : 'text-finwell-muted'
              }`}
            >
              Year-over-Year Inflow
            </button>
          </div>
        </div>

        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            {metricTab === 'cashflow' ? (
              <BarChart data={filteredTrends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
                <Legend wrapperStyle={{ fontSize: '11px', color: '#9298B3' }} />
                <Bar dataKey="income" name="Monthly Inflow" fill="#4263FF" radius={[4, 4, 0, 0]} />
                <Bar dataKey="expense" name="Monthly Outflow" fill="#20D9F2" radius={[4, 4, 0, 0]} />
              </BarChart>
            ) : (
              <LineChart data={filteredTrends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
                <Legend wrapperStyle={{ fontSize: '11px', color: '#9298B3' }} />
                <Line
                  type="monotone"
                  dataKey="current_year_income"
                  name="Current Year (2026)"
                  stroke="#4263FF"
                  strokeWidth={3}
                  dot={{ r: 4, fill: '#4263FF' }}
                />
                <Line
                  type="monotone"
                  dataKey="last_year_income"
                  name="Prior Year (2025)"
                  stroke="#875BFF"
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  dot={{ r: 3, fill: '#875BFF' }}
                />
              </LineChart>
            )}
          </ResponsiveContainer>
        </div>
      </TiltCard>

      {/* Secondary Analytics Row: Income Sources & Spending Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Income Sources Breakdown */}
        <TiltCard className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-white">Inflow Capital Sources</h3>
              <p className="text-xs text-finwell-dim mt-0.5">Distribution of revenue pillars</p>
            </div>
            <Badge variant="cyan" size="sm">
              4 Verticals
            </Badge>
          </div>

          <div className="space-y-4">
            {incomeSources.map((source) => (
              <div key={source.name} className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-white">{source.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-finwell-muted font-mono">${source.amount.toLocaleString()}</span>
                    <span className="font-bold text-finwell-cyan">{source.percentage}%</span>
                  </div>
                </div>
                {/* Progress Bar */}
                <div className="h-2 w-full rounded-full bg-finwell-surface overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${source.percentage}%`, backgroundColor: source.color }}
                  />
                </div>
              </div>
            ))}
          </div>
        </TiltCard>

        {/* Daily Spending & Heatmap Insights */}
        <TiltCard className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-white">Daily Spending Velocity</h3>
              <p className="text-xs text-finwell-dim mt-0.5">Average daily capital burn rate</p>
            </div>
            <Badge variant="primary" size="sm">
              $314.01 / day
            </Badge>
          </div>

          <div className="rounded-xl bg-finwell-surface/60 border border-white/5 p-4 space-y-4">
            <div className="flex items-center justify-between text-xs">
              <span className="text-finwell-muted">Discretionary vs Non-Discretionary</span>
              <span className="font-bold text-white">28% / 72%</span>
            </div>
            <div className="h-2.5 w-full rounded-full bg-finwell-bg flex overflow-hidden">
              <div className="bg-finwell-primary h-full" style={{ width: '72%' }} title="Non-Discretionary 72%" />
              <div className="bg-finwell-cyan h-full" style={{ width: '28%' }} title="Discretionary 28%" />
            </div>

            <div className="grid grid-cols-2 gap-3 pt-2 text-xs">
              <div className="rounded-lg bg-finwell-card p-3 border border-white/5">
                <span className="text-finwell-dim text-[10px] uppercase">Peak Spending Day</span>
                <p className="text-sm font-bold text-white mt-1">Thursday ($1,420.50)</p>
                <span className="text-[10px] text-finwell-dim">Cloud server billing cycles</span>
              </div>
              <div className="rounded-lg bg-finwell-card p-3 border border-white/5">
                <span className="text-finwell-dim text-[10px] uppercase">Lowest Spending Day</span>
                <p className="text-sm font-bold text-white mt-1">Sunday ($42.10)</p>
                <span className="text-[10px] text-finwell-dim">Weekend minimal activity</span>
              </div>
            </div>
          </div>
        </TiltCard>
      </div>
    </div>
  );
};
