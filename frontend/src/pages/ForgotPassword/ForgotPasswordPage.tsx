import React, { useState } from 'react';
import { Sparkles, Mail, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { Button } from '../../components/common/Button';
import { authService } from '../../services/auth/authService';

interface ForgotPasswordPageProps {
  onNavigateToLogin: () => void;
}

export const ForgotPasswordPage: React.FC<ForgotPasswordPageProps> = ({
  onNavigateToLogin,
}) => {
  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await authService.forgotPassword(email);
      setIsSubmitted(true);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center p-4 bg-finwell-bg overflow-hidden select-none">
      <div className="pointer-events-none absolute -top-40 -left-40 h-[600px] w-[600px] rounded-full bg-finwell-primary/15 blur-[140px]" />
      <div className="pointer-events-none absolute -bottom-40 -right-40 h-[600px] w-[600px] rounded-full bg-finwell-violet/15 blur-[140px]" />

      <div className="relative z-10 w-full max-w-md rounded-3xl border border-white/10 bg-finwell-card/90 backdrop-blur-2xl p-8 sm:p-10 shadow-glow-lg">
        {isSubmitted ? (
          <div className="text-center space-y-4">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-finwell-success/20 text-finwell-success">
              <CheckCircle2 className="h-8 w-8" />
            </div>
            <h3 className="text-xl font-bold text-white">Reset Instructions Sent</h3>
            <p className="text-xs text-finwell-muted leading-relaxed">
              We have dispatched recovery instructions to <strong className="text-white">{email}</strong>. Please check your inbox or spam directory.
            </p>

            <Button
              variant="outline"
              size="md"
              className="w-full mt-4"
              onClick={onNavigateToLogin}
              icon={<ArrowLeft className="h-4 w-4" />}
            >
              Return to Login
            </Button>
          </div>
        ) : (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-finwell-primary via-finwell-cyan to-finwell-violet p-0.5 shadow-glow-sm">
                <div className="flex h-full w-full items-center justify-center rounded-[10px] bg-finwell-sidebar">
                  <Sparkles className="h-5 w-5 text-finwell-cyan" />
                </div>
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Password Recovery</h2>
                <p className="text-xs text-finwell-muted">Reset your FinWell AI credentials</p>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-finwell-muted mb-1.5">
                  Your Account Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-3.5 h-4 w-4 text-finwell-dim" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="george.dev@finwell.ai"
                    className="w-full rounded-xl border border-white/10 bg-finwell-surface pl-10 pr-4 py-2.5 text-xs text-white placeholder-finwell-dim focus:border-finwell-primary focus:outline-none"
                  />
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                size="md"
                glow
                isLoading={isLoading}
                className="w-full mt-2"
              >
                Send Recovery Link
              </Button>
            </form>

            <div className="mt-6 pt-4 border-t border-white/5 text-center">
              <button
                onClick={onNavigateToLogin}
                className="inline-flex items-center gap-1.5 text-xs text-finwell-muted hover:text-white transition-colors"
              >
                <ArrowLeft className="h-3.5 w-3.5" /> Back to Sign In
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
