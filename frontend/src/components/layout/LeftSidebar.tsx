import React from 'react';
import {
  LayoutDashboard,
  Sparkles,
  Wallet,
  ArrowLeftRight,
  LineChart,
  FileCheck2,
  FileText,
  Files,
  Settings,
  Moon,
  Sun,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';

export type NavigationPage =
  | 'dashboard'
  | 'ai-chat'
  | 'accounts'
  | 'transactions'
  | 'analytics'
  | 'reconciliation'
  | 'documents'
  | 'reports'
  | 'settings';

interface LeftSidebarProps {
  currentPage: NavigationPage;
  onSelectPage: (page: NavigationPage) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export const LeftSidebar: React.FC<LeftSidebarProps> = ({
  currentPage,
  onSelectPage,
  isCollapsed,
  onToggleCollapse,
}) => {
  const { mode, toggleMode } = useTheme();
  const { user } = useAuth();

  const navItems: { id: NavigationPage; label: string; icon: React.ReactNode; isAI?: boolean }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="h-5 w-5" /> },
    { id: 'ai-chat', label: 'FinWell AI', icon: <Sparkles className="h-5 w-5" />, isAI: true },
    { id: 'accounts', label: 'Accounts', icon: <Wallet className="h-5 w-5" /> },
    { id: 'transactions', label: 'Transactions', icon: <ArrowLeftRight className="h-5 w-5" /> },
    { id: 'analytics', label: 'Analytics', icon: <LineChart className="h-5 w-5" /> },
    { id: 'reconciliation', label: 'Reconciliation', icon: <FileCheck2 className="h-5 w-5" /> },
    { id: 'documents', label: 'Documents', icon: <Files className="h-5 w-5" /> },
    { id: 'reports', label: 'Reports', icon: <FileText className="h-5 w-5" /> },
    { id: 'settings', label: 'Settings', icon: <Settings className="h-5 w-5" /> },
  ];

  return (
    <aside
      className={`relative z-20 flex flex-col justify-between border-r border-white/5 bg-finwell-sidebar transition-all duration-300 select-none ${
        isCollapsed ? 'w-20' : 'w-72'
      } min-h-screen p-4`}
    >
      {/* Top Section */}
      <div className="flex flex-col gap-6">
        {/* Brand Logo & Collapse Toggle */}
        <div className="flex items-center justify-between px-2">
          <div
            onClick={() => onSelectPage('dashboard')}
            className="flex items-center gap-3 cursor-pointer group"
          >
            {/* Glowing Logo Icon */}
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-finwell-primary via-finwell-cyan to-finwell-violet p-0.5 shadow-glow-sm">
              <div className="flex h-full w-full items-center justify-center rounded-[10px] bg-finwell-sidebar">
                <Sparkles className="h-5 w-5 text-finwell-cyan group-hover:scale-110 transition-transform" />
              </div>
            </div>

            {!isCollapsed && (
              <div>
                <span className="text-lg font-extrabold tracking-tight text-white flex items-center gap-1.5">
                  FinWell <span className="text-finwell-primary">AI</span>
                </span>
                <span className="block text-[10px] font-medium tracking-widest text-finwell-dim uppercase">
                  FINANCIAL INTELLIGENCE
                </span>
              </div>
            )}
          </div>

          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex h-7 w-7 items-center justify-center rounded-lg border border-white/5 bg-finwell-card text-finwell-muted hover:border-finwell-primary/40 hover:text-white"
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>

        {/* User Profile Card (Faithful to NeuroBank Reference) */}
        {!isCollapsed ? (
          <div className="relative overflow-hidden rounded-2xl border border-white/5 bg-finwell-card/90 p-3.5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="relative">
                <img
                  src={user?.avatar || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=256&q=80'}
                  alt="User Avatar"
                  className="h-10 w-10 rounded-xl object-cover ring-2 ring-finwell-primary/30"
                />
                <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full bg-finwell-success ring-2 ring-finwell-card" />
              </div>

              {/* Theme Toggle Pill */}
              <button
                onClick={toggleMode}
                className="flex items-center gap-1 rounded-full border border-white/10 bg-finwell-surface p-1 text-xs text-finwell-muted hover:text-white transition-colors"
                title="Toggle Theme"
              >
                <div
                  className={`rounded-full p-1 ${
                    mode === 'dark' ? 'bg-finwell-primary text-white shadow-glow-sm' : 'text-finwell-dim'
                  }`}
                >
                  <Moon className="h-3 w-3" />
                </div>
                <div
                  className={`rounded-full p-1 ${
                    mode === 'light' ? 'bg-finwell-primary text-white shadow-glow-sm' : 'text-finwell-dim'
                  }`}
                >
                  <Sun className="h-3 w-3" />
                </div>
              </button>
            </div>

            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-finwell-dim">
                MONDAY, MARCH 24
              </p>
              <h4 className="text-sm font-bold text-white mt-0.5">
                Welcome back, {user?.full_name?.split(' ')[0] || 'George'}!
              </h4>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <div className="relative">
              <img
                src={user?.avatar || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=256&q=80'}
                alt="User Avatar"
                className="h-10 w-10 rounded-xl object-cover ring-2 ring-finwell-primary/30"
              />
              <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full bg-finwell-success ring-2 ring-finwell-card" />
            </div>
          </div>
        )}

        {/* Navigation Items */}
        <nav className="flex flex-col gap-1.5">
          {navItems.map((item) => {
            const isActive = currentPage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectPage(item.id)}
                className={`group relative flex items-center gap-3.5 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'border border-finwell-primary/40 bg-gradient-to-r from-finwell-primary/25 to-finwell-violet/15 text-white shadow-glow-sm'
                    : 'text-finwell-muted hover:bg-white/[0.04] hover:text-white'
                } ${isCollapsed ? 'justify-center px-2' : ''}`}
                title={isCollapsed ? item.label : undefined}
              >
                <span
                  className={`${
                    isActive ? 'text-finwell-cyan' : 'text-finwell-muted group-hover:text-white'
                  }`}
                >
                  {item.icon}
                </span>

                {!isCollapsed && (
                  <span className="flex-1 text-left tracking-wide">{item.label}</span>
                )}

                {/* Subtle active indicator pill */}
                {isActive && !isCollapsed && (
                  <span className="h-1.5 w-1.5 rounded-full bg-finwell-cyan shadow-[0_0_8px_#20D9F2]" />
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Promo Card (Inspired by reference "Activate NeuroBank Pro") */}
      {!isCollapsed ? (
        <div className="relative mt-6 overflow-hidden rounded-2xl border border-finwell-primary/30 bg-gradient-to-br from-finwell-primary/30 via-finwell-surface to-finwell-card p-4 shadow-glow-sm">
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-finwell-primary/20 p-2 text-finwell-cyan">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h5 className="text-xs font-bold text-white flex items-center gap-1.5">
                FinWell Pro AI
                <span className="rounded bg-finwell-cyan/20 px-1 py-0.5 text-[9px] font-semibold text-finwell-cyan">
                  ACTIVE
                </span>
              </h5>
              <p className="mt-1 text-[11px] text-finwell-muted leading-relaxed">
                Elevate personal finance with autonomous reconciliation & Qwen 2.5 intelligence.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex justify-center py-2">
          <button
            onClick={() => onSelectPage('settings')}
            className="rounded-xl p-2.5 text-finwell-cyan hover:bg-white/5"
            title="FinWell Pro Active"
          >
            <ShieldCheck className="h-5 w-5" />
          </button>
        </div>
      )}
    </aside>
  );
};
