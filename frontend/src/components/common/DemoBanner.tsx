import React, { useState } from 'react';
import { Sparkles, Server, CheckCircle2, X, LogOut, UserPlus, User } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface DemoBannerProps {
  onRegisterNewUser?: () => void;
}

export const DemoBanner: React.FC<DemoBannerProps> = ({ onRegisterNewUser }) => {
  const { isMockMode, user, logout } = useAuth();
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
          <Sparkles className="h-3.5 w-3.5" /> FINWELL
        </span>
        <span className="text-white/20">|</span>
        <span className="hidden sm:inline">
          {isMockMode
            ? 'Interactive Mock Engine Active'
            : 'Live FastAPI Backend Mode'}
        </span>
        {user?.email && (
          <span className="inline-flex items-center gap-1 rounded bg-white/5 px-2 py-0.5 text-[11px] text-white font-medium">
            <User className="h-3 w-3 text-finwell-cyan" />
            <span className="truncate max-w-[160px]">{user.email}</span>
          </span>
        )}
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {onRegisterNewUser && (
          <button
            onClick={onRegisterNewUser}
            className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-finwell-surface px-2 py-0.5 text-[11px] font-semibold text-finwell-cyan hover:border-finwell-cyan/40 hover:text-white transition-colors"
            title="Create New User Account"
          >
            <UserPlus className="h-3 w-3" />
            <span>New User</span>
          </button>
        )}

        <button
          onClick={logout}
          className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-finwell-surface px-2 py-0.5 text-[11px] font-semibold text-finwell-muted hover:border-finwell-danger/40 hover:text-finwell-danger transition-colors"
          title="Sign Out of Session"
        >
          <LogOut className="h-3 w-3" />
          <span>Log Out</span>
        </button>

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
