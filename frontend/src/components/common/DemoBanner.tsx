import React, { useState } from 'react';
import { Sparkles, Server, CheckCircle2, X } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const DemoBanner: React.FC = () => {
  const { isMockMode } = useAuth();
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="relative z-30 flex items-center justify-between border-b border-white/5 bg-finwell-sidebar/80 px-4 py-1.5 text-xs text-finwell-muted backdrop-blur-md">
      <div className="flex items-center gap-2 overflow-x-auto">
        <span className="flex h-2 w-2 relative">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-finwell-cyan opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-finwell-cyan"></span>
        </span>
        <span className="font-semibold text-finwell-cyan flex items-center gap-1">
          <Sparkles className="h-3.5 w-3.5" /> FINWELL DEMO MODE
        </span>
        <span className="text-white/20">|</span>
        <span className="hidden sm:inline">
          {isMockMode
            ? 'Interactive Mock Engine Active — All numbers and reconciliation cases are synthetic demo data.'
            : 'Live FastAPI Backend Mode Selected'}
        </span>
        <span className="inline-flex items-center gap-1 rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-finwell-muted">
          <Server className="h-3 w-3 text-finwell-primary" /> API Ready: /api/auth, /api/analytics, /api/accounts
        </span>
      </div>

      <div className="flex items-center gap-2">
        <span className="hidden md:inline-flex items-center gap-1 text-[11px] text-finwell-success">
          <CheckCircle2 className="h-3 w-3" /> Architecture Aligned
        </span>
        <button
          onClick={() => setDismissed(true)}
          className="rounded p-0.5 text-finwell-dim hover:bg-white/5 hover:text-white"
          title="Dismiss banner"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
};
