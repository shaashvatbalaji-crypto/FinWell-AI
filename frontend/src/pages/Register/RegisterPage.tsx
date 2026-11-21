import React, { useState } from 'react';
import {
  Sparkles,
  User,
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { useAuth } from '../../context/AuthContext';

interface RegisterPageProps {
  onNavigateToLogin: () => void;
}

export const RegisterPage: React.FC<RegisterPageProps> = ({ onNavigateToLogin }) => {
  const { register, isLoading } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [agreeTerms, setAgreeTerms] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Password strength calculation
  const getPasswordStrength = (pass: string) => {
    if (!pass) return { score: 0, label: 'Empty', color: 'bg-white/10' };
    let score = 0;
    if (pass.length >= 8) score++;
    if (/[A-Z]/.test(pass)) score++;
    if (/[0-9]/.test(pass)) score++;
    if (/[^A-Za-z0-9]/.test(pass)) score++;

    if (score <= 1) return { score: 25, label: 'Weak', color: 'bg-finwell-danger' };
    if (score === 2) return { score: 50, label: 'Fair', color: 'bg-finwell-warning' };
    if (score === 3) return { score: 75, label: 'Good', color: 'bg-finwell-cyan' };
    return { score: 100, label: 'Strong', color: 'bg-finwell-success' };
  };

  const strength = getPasswordStrength(password);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (password !== confirmPassword) {
      setErrorMsg('Passwords do not match.');
      return;
    }

    if (!agreeTerms) {
      setErrorMsg('You must agree to the Terms of Service to create an account.');
      return;
    }

    try {
      const username = email.split('@')[0] || 'finwell_user';
      await register({
        username,
        email,
        password,
        full_name: fullName,
      });
    } catch (err: any) {
      setErrorMsg(err.message || 'Registration failed.');
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center p-4 bg-finwell-bg overflow-hidden select-none">
      <div className="pointer-events-none absolute -top-40 -right-40 h-[600px] w-[600px] rounded-full bg-finwell-primary/15 blur-[140px]" />
      <div className="pointer-events-none absolute -bottom-40 -left-40 h-[600px] w-[600px] rounded-full bg-finwell-violet/15 blur-[140px]" />

      <div className="relative z-10 w-full max-w-lg rounded-3xl border border-white/10 bg-finwell-card/90 backdrop-blur-2xl p-8 sm:p-10 shadow-glow-lg">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-finwell-primary via-finwell-cyan to-finwell-violet p-0.5 shadow-glow-sm">
              <div className="flex h-full w-full items-center justify-center rounded-[10px] bg-finwell-sidebar">
                <Sparkles className="h-5 w-5 text-finwell-cyan" />
              </div>
            </div>
            <div>
              <span className="text-lg font-bold text-white tracking-tight flex items-center gap-1">
                FinWell <span className="text-finwell-primary">AI</span>
              </span>
              <span className="block text-[10px] text-finwell-dim uppercase tracking-wider">
                Create Institutional Account
              </span>
            </div>
          </div>

          <Badge variant="cyan" size="sm">
            Mock / Demo Auth
          </Badge>
        </div>

        {errorMsg && (
          <div className="mb-4 rounded-xl border border-finwell-danger/30 bg-finwell-danger/10 p-3 text-xs text-finwell-danger">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Full Name */}
          <div>
            <label className="block text-xs font-semibold text-finwell-muted mb-1">
              Full Legal Name
            </label>
            <div className="relative">
              <User className="absolute left-3.5 top-3.5 h-4 w-4 text-finwell-dim" />
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="George Henderson"
                className="w-full rounded-xl border border-white/10 bg-finwell-surface pl-10 pr-4 py-2 text-xs text-white placeholder-finwell-dim focus:border-finwell-primary focus:outline-none"
              />
            </div>
          </div>

          {/* Email */}
          <div>
            <label className="block text-xs font-semibold text-finwell-muted mb-1">
              Financial Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-3.5 h-4 w-4 text-finwell-dim" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="george.dev@finwell.ai"
                className="w-full rounded-xl border border-white/10 bg-finwell-surface pl-10 pr-4 py-2 text-xs text-white placeholder-finwell-dim focus:border-finwell-primary focus:outline-none"
              />
            </div>
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs font-semibold text-finwell-muted mb-1">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-3.5 h-4 w-4 text-finwell-dim" />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                className="w-full rounded-xl border border-white/10 bg-finwell-surface pl-10 pr-10 py-2 text-xs text-white placeholder-finwell-dim focus:border-finwell-primary focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-2.5 text-finwell-dim hover:text-white"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>

            {/* Password Strength Indicator */}
            {password && (
              <div className="mt-2 space-y-1">
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-finwell-dim">Password Strength</span>
                  <span className="font-semibold text-white">{strength.label}</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-finwell-surface overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${strength.color}`}
                    style={{ width: `${strength.score}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Confirm Password */}
          <div>
            <label className="block text-xs font-semibold text-finwell-muted mb-1">
              Confirm Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-3.5 h-4 w-4 text-finwell-dim" />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repeat password"
                className="w-full rounded-xl border border-white/10 bg-finwell-surface pl-10 pr-4 py-2 text-xs text-white placeholder-finwell-dim focus:border-finwell-primary focus:outline-none"
              />
            </div>
          </div>

          {/* Terms and Conditions Checkbox */}
          <div className="pt-2">
            <label className="flex items-start gap-2.5 text-xs text-finwell-muted cursor-pointer">
              <input
                type="checkbox"
                checked={agreeTerms}
                onChange={(e) => setAgreeTerms(e.target.checked)}
                className="mt-0.5 rounded border-white/10 bg-finwell-surface text-finwell-primary focus:ring-0 h-3.5 w-3.5"
              />
              <span className="leading-relaxed text-[11px]">
                I agree to the <span className="text-finwell-cyan hover:underline">Terms of Service</span> and acknowledge that this frontend is ready for local FastAPI integration.
              </span>
            </label>
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
            Create FinWell Account
          </Button>
        </form>

        {/* Back to Login */}
        <div className="mt-6 pt-4 border-t border-white/5 text-center text-xs text-finwell-muted">
          Already registered?{' '}
          <button
            onClick={onNavigateToLogin}
            className="font-bold text-finwell-cyan hover:underline ml-1"
          >
            Sign in
          </button>
        </div>
      </div>
    </div>
  );
};
