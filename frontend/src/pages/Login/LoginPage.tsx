import React, { useState } from 'react';
import {
  Sparkles,
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';
import { FinancialOrb3D } from '../../components/3d/FinancialOrb3D';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { useAuth } from '../../context/AuthContext';

interface LoginPageProps {
  onNavigateToRegister: () => void;
  onNavigateToForgotPassword: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({
  onNavigateToRegister,
  onNavigateToForgotPassword,
}) => {
  const { login, isLoading } = useAuth();
  const [email, setEmail] = useState<string>('george.dev@finwell.ai');
  const [password, setPassword] = useState<string>('FinWell@2026Secure!');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [rememberMe, setRememberMe] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    try {
      await login({ email, password });
    } catch (err: any) {
      setErrorMsg(err.message || 'Login failed. Please verify credentials.');
    }
  };

  const handleQuickDemoFill = () => {
    setEmail('george.dev@finwell.ai');
    setPassword('FinWell@2026Secure!');
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center p-4 bg-finwell-bg overflow-hidden select-none">
      {/* Background Radial Glow */}
      <div className="pointer-events-none absolute -top-40 -left-40 h-[600px] w-[600px] rounded-full bg-finwell-primary/15 blur-[140px]" />
      <div className="pointer-events-none absolute -bottom-40 -right-40 h-[600px] w-[600px] rounded-full bg-finwell-violet/15 blur-[140px]" />

      <div className="relative z-10 w-full max-w-5xl grid grid-cols-1 lg:grid-cols-2 rounded-3xl border border-white/10 bg-finwell-card/80 backdrop-blur-2xl shadow-glow-lg overflow-hidden">
        {/* Left Side: 3D Visual Experience */}
        <div className="relative hidden lg:flex flex-col justify-between p-10 bg-gradient-to-b from-finwell-sidebar/80 via-finwell-surface/50 to-finwell-card/90 border-r border-white/5">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-finwell-primary via-finwell-cyan to-finwell-violet p-0.5 shadow-glow-sm">
              <div className="flex h-full w-full items-center justify-center rounded-[10px] bg-finwell-sidebar">
                <Sparkles className="h-5 w-5 text-finwell-cyan" />
              </div>
            </div>
            <div>
              <span className="text-xl font-extrabold text-white tracking-tight flex items-center gap-1">
                FinWell <span className="text-finwell-primary">AI</span>
              </span>
              <span className="block text-[10px] font-semibold text-finwell-dim uppercase tracking-widest">
                AUTONOMOUS FINANCIAL ORCHESTRATION
              </span>
            </div>
          </div>

          {/* 3D Financial Orb */}
          <div className="flex flex-col items-center justify-center py-6">
            <FinancialOrb3D size={290} />
            <div className="text-center mt-3">
              <h4 className="text-sm font-bold text-white tracking-wide">
                Neural Reconciliation Engine
              </h4>
              <p className="text-xs text-finwell-muted max-w-xs mt-1">
                Multimodal financial intelligence connecting MySQL ledger storage with vector embeddings.
              </p>
            </div>
          </div>

          {/* Feature Badge */}
          <div className="rounded-2xl border border-white/5 bg-finwell-surface/60 p-3.5 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 text-finwell-muted">
              <ShieldCheck className="h-4 w-4 text-finwell-cyan" />
              <span>FastAPI & Qwen 2.5:3B Ready</span>
            </div>
            <Badge variant="cyan" size="sm">
              Demo Sandbox
            </Badge>
          </div>
        </div>

        {/* Right Side: Form */}
        <div className="flex flex-col justify-between p-8 sm:p-12">
          {/* Top Brand on mobile */}
          <div className="flex lg:hidden items-center gap-2 mb-6">
            <div className="h-8 w-8 rounded-lg bg-finwell-primary/20 flex items-center justify-center text-finwell-cyan">
              <Sparkles className="h-4 w-4" />
            </div>
            <span className="text-lg font-bold text-white">FinWell AI</span>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-extrabold tracking-tight text-white">
                  Welcome back
                </h2>
                <p className="text-xs text-finwell-muted mt-1">
                  Access your personal wealth command centre
                </p>
              </div>

              {/* Demo Fill Helper */}
              <button
                type="button"
                onClick={handleQuickDemoFill}
                className="text-[11px] font-semibold text-finwell-cyan hover:underline flex items-center gap-1"
                title="Fill demo credentials"
              >
                <Sparkles className="h-3 w-3" /> Auto-fill Demo
              </button>
            </div>

            {errorMsg && (
              <div className="mt-4 rounded-xl border border-finwell-danger/30 bg-finwell-danger/10 p-3 text-xs text-finwell-danger">
                {errorMsg}
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              {/* Email */}
              <div>
                <label className="block text-xs font-semibold text-finwell-muted mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-3.5 h-4 w-4 text-finwell-dim" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@finwell.ai"
                    className="w-full rounded-xl border border-white/10 bg-finwell-surface pl-10 pr-4 py-2.5 text-xs text-white placeholder-finwell-dim focus:border-finwell-primary focus:outline-none"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-xs font-semibold text-finwell-muted mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-3.5 h-4 w-4 text-finwell-dim" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your security password"
                    className="w-full rounded-xl border border-white/10 bg-finwell-surface pl-10 pr-10 py-2.5 text-xs text-white placeholder-finwell-dim focus:border-finwell-primary focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-3 text-finwell-dim hover:text-white"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Remember Me & Forgot Password */}
              <div className="flex items-center justify-between text-xs pt-1">
                <label className="flex items-center gap-2 text-finwell-muted cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="rounded border-white/10 bg-finwell-surface text-finwell-primary focus:ring-0 h-3.5 w-3.5"
                  />
                  <span>Remember me</span>
                </label>

                <button
                  type="button"
                  onClick={onNavigateToForgotPassword}
                  className="text-finwell-primary hover:text-finwell-cyan transition-colors"
                >
                  Forgot password?
                </button>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                variant="primary"
                size="lg"
                glow
                isLoading={isLoading}
                className="w-full mt-2"
                icon={<ArrowRight className="h-4 w-4" />}
              >
                Sign In to Dashboard
              </Button>
            </form>
          </div>

          {/* Footer Register Link */}
          <div className="mt-8 pt-4 border-t border-white/5 text-center text-xs text-finwell-muted">
            Don't have an account yet?{' '}
            <button
              onClick={onNavigateToRegister}
              className="font-bold text-finwell-cyan hover:underline ml-1"
            >
              Create account
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
