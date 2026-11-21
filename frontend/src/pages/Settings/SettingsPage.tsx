import React, { useState } from 'react';
import {
  User,
  Shield,
  Palette,
  Bell,
  Globe,
  Server,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  Lock,
  LogOut,
  UserPlus,
} from 'lucide-react';
import { TiltCard } from '../../components/3d/TiltCard';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { apiClient } from '../../services/api/apiClient';

interface SettingsPageProps {
  onRegisterNewUser?: () => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ onRegisterNewUser }) => {
  const { user, isMockMode, setMockMode, logout } = useAuth();
  const { mode, toggleMode, reducedMotion, setReducedMotion } = useTheme();

  // Settings State
  const [profileName, setProfileName] = useState(user?.full_name || 'George Henderson');
  const [profileEmail, setProfileEmail] = useState(user?.email || 'george.dev@finwell.ai');
  const [currency, setCurrency] = useState('USD');
  const [backendUrl, setBackendUrl] = useState(apiClient.getBaseURL());
  const [healthStatus, setHealthStatus] = useState<'unchecked' | 'healthy' | 'unreachable'>('unchecked');
  const [isTestingHealth, setIsTestingHealth] = useState(false);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  // Notification toggles
  const [notifyDuplicates, setNotifyDuplicates] = useState(true);
  const [notifyLargeTxn, setNotifyLargeTxn] = useState(true);
  const [notifyWeeklyReport, setNotifyWeeklyReport] = useState(false);

  const handleTestHealth = async () => {
    setIsTestingHealth(true);
    try {
      const response = await fetch(`${backendUrl.replace(/\/api\/?$/, '')}/health`, {
        method: 'GET',
      });
      if (response.ok) {
        setHealthStatus('healthy');
      } else {
        setHealthStatus('unreachable');
      }
    } catch (e) {
      setHealthStatus('unreachable');
    } finally {
      setIsTestingHealth(false);
    }
  };

  const handleSaveSettings = () => {
    apiClient.setBaseURL(backendUrl);
    setSavedMessage('Settings successfully saved to local configuration.');
    setTimeout(() => setSavedMessage(null), 3000);
  };

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white flex items-center gap-2">
            System & Account Settings
            <Badge variant="cyan" size="sm">
              v1.0.0
            </Badge>
          </h1>
          <p className="text-xs text-finwell-muted mt-1">
            Configure profile credentials, AI thresholds, visual themes, and FastAPI connectivity.
          </p>
        </div>

        <Button
          variant="primary"
          glow
          onClick={handleSaveSettings}
        >
          Save Changes
        </Button>
      </div>

      {savedMessage && (
        <div className="rounded-xl border border-finwell-success/30 bg-finwell-success/10 p-3.5 text-xs text-finwell-success flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4" />
          <span>{savedMessage}</span>
        </div>
      )}

      {/* User Session & Account Switching Card */}
      <TiltCard className="p-6 border-white/10 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-finwell-surface p-2.5 text-finwell-cyan border border-white/5">
              <User className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">Active Account & Session</h3>
                <Badge variant="cyan" size="sm">
                  User ID: #{user?.user_id || '3'}
                </Badge>
              </div>
              <p className="text-xs text-finwell-muted mt-0.5">
                Authenticated as <span className="text-white font-mono font-semibold">{user?.email || 'ram@gmail.com'}</span> ({user?.full_name || user?.username || 'Ram'})
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            {onRegisterNewUser && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRegisterNewUser}
                icon={<UserPlus className="h-3.5 w-3.5 text-finwell-cyan" />}
              >
                Create New User
              </Button>
            )}

            <Button
              variant="secondary"
              size="sm"
              onClick={logout}
              icon={<LogOut className="h-3.5 w-3.5 text-finwell-danger" />}
              className="hover:border-finwell-danger/50 hover:text-finwell-danger"
            >
              Log Out
            </Button>
          </div>
        </div>

        <p className="text-xs text-finwell-dim">
          Logging out terminates the active JWT session and returns you to the login screen where you can sign in with other credentials or register a new account.
        </p>
      </TiltCard>

      {/* 1. Backend Connectivity & Mock Mode Control (Crucial Requirement) */}
      <TiltCard className="p-6 border-finwell-primary/40 space-y-5">
        <div className="flex items-center justify-between border-b border-white/5 pb-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-finwell-primary/20 p-2.5 text-finwell-cyan">
              <Server className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                FastAPI Backend Integration Layer
                <Badge variant={isMockMode ? 'warning' : 'success'} size="sm">
                  {isMockMode ? 'Mock Engine Active' : 'Live API Connected'}
                </Badge>
              </h3>
              <p className="text-xs text-finwell-muted mt-0.5">
                Centralized gateway bridging the frontend to your existing FastAPI, MySQL, ChromaDB & Qwen services.
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Mock Mode Switch */}
          <div className="rounded-xl bg-finwell-surface p-4 border border-white/5 flex flex-col justify-between">
            <div>
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                Operation Mode
              </h4>
              <p className="text-xs text-finwell-muted mt-1 leading-relaxed">
                When enabled, FinWell AI operates with realistic synthetic datasets without requiring a local database or server.
              </p>
            </div>

            <div className="mt-4 flex items-center justify-between pt-3 border-t border-white/5">
              <span className="text-xs font-semibold text-white">
                {isMockMode ? 'Mock Data Simulation' : 'Live API Direct'}
              </span>
              <button
                type="button"
                onClick={() => setMockMode(!isMockMode)}
                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  isMockMode ? 'bg-finwell-primary' : 'bg-finwell-success'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    isMockMode ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          </div>

          {/* Backend API Endpoint Configuration */}
          <div className="rounded-xl bg-finwell-surface p-4 border border-white/5 space-y-3">
            <div>
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                FastAPI Gateway URL
              </h4>
              <p className="text-xs text-finwell-dim mt-0.5">
                Configures target host for /api/auth, /api/transactions, etc.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="text"
                value={backendUrl}
                onChange={(e) => setBackendUrl(e.target.value)}
                className="flex-1 rounded-xl border border-white/10 bg-finwell-card px-3 py-2 text-xs text-white font-mono focus:border-finwell-primary focus:outline-none"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={handleTestHealth}
                isLoading={isTestingHealth}
              >
                Ping Health
              </Button>
            </div>

            {healthStatus !== 'unchecked' && (
              <div className="flex items-center gap-2 text-xs pt-1">
                {healthStatus === 'healthy' ? (
                  <span className="text-finwell-success flex items-center gap-1 font-semibold">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Backend is healthy & responding (200 OK)
                  </span>
                ) : (
                  <span className="text-finwell-danger flex items-center gap-1 font-semibold">
                    <AlertTriangle className="h-3.5 w-3.5" /> Connection failed — ensure FastAPI server is running on {backendUrl}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </TiltCard>

      {/* 2. User Profile Credentials */}
      <TiltCard className="p-6 space-y-4">
        <div className="flex items-center gap-3 border-b border-white/5 pb-4">
          <User className="h-5 w-5 text-finwell-cyan" />
          <h3 className="text-base font-bold text-white">Profile Credentials</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-finwell-muted mb-1">
              Full Legal Name
            </label>
            <input
              type="text"
              value={profileName}
              onChange={(e) => setProfileName(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-finwell-surface px-3.5 py-2.5 text-xs text-white focus:border-finwell-primary focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-finwell-muted mb-1">
              Primary Financial Email
            </label>
            <input
              type="email"
              value={profileEmail}
              onChange={(e) => setProfileEmail(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-finwell-surface px-3.5 py-2.5 text-xs text-white focus:border-finwell-primary focus:outline-none"
            />
          </div>
        </div>
      </TiltCard>

      {/* 3. Security & Access */}
      <TiltCard className="p-6 space-y-4">
        <div className="flex items-center gap-3 border-b border-white/5 pb-4">
          <Shield className="h-5 w-5 text-finwell-violet" />
          <h3 className="text-base font-bold text-white">Security & Audit Policies</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="rounded-xl bg-finwell-surface p-4 border border-white/5 flex items-center justify-between">
            <div>
              <p className="font-bold text-white">Two-Factor Authentication (2FA)</p>
              <p className="text-[11px] text-finwell-muted mt-0.5">Enforce TOTP hardware token verification</p>
            </div>
            <Badge variant="success" size="sm">Enabled</Badge>
          </div>

          <div className="rounded-xl bg-finwell-surface p-4 border border-white/5 flex items-center justify-between">
            <div>
              <p className="font-bold text-white">Active Session Expiry</p>
              <p className="text-[11px] text-finwell-muted mt-0.5">FastAPI JWT Token: 30 minutes TTL</p>
            </div>
            <Badge variant="primary" size="sm">Strict</Badge>
          </div>
        </div>
      </TiltCard>

      {/* 4. Appearance & Reduced Motion */}
      <TiltCard className="p-6 space-y-4">
        <div className="flex items-center gap-3 border-b border-white/5 pb-4">
          <Palette className="h-5 w-5 text-finwell-cyan" />
          <h3 className="text-base font-bold text-white">Visual Experience & Accessibility</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="rounded-xl bg-finwell-surface p-4 border border-white/5 flex items-center justify-between">
            <div>
              <p className="font-bold text-white">Respect Reduced Motion</p>
              <p className="text-[11px] text-finwell-muted mt-0.5">
                Disables 3D orb tilt, particles & continuous rotations for accessibility
              </p>
            </div>
            <button
              onClick={() => setReducedMotion(!reducedMotion)}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
                reducedMotion ? 'bg-finwell-primary' : 'bg-white/10'
              }`}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white transition ${
                  reducedMotion ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          <div className="rounded-xl bg-finwell-surface p-4 border border-white/5 flex items-center justify-between">
            <div>
              <p className="font-bold text-white">Default Display Currency</p>
              <p className="text-[11px] text-finwell-muted mt-0.5">Currency symbol used across summary cards</p>
            </div>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="rounded-lg border border-white/10 bg-finwell-card px-2.5 py-1 text-xs text-white focus:outline-none"
            >
              <option value="USD">USD ($)</option>
              <option value="INR">INR (₹)</option>
              <option value="EUR">EUR (€)</option>
              <option value="GBP">GBP (£)</option>
            </select>
          </div>
        </div>
      </TiltCard>

      {/* 5. Notification Preferences */}
      <TiltCard className="p-6 space-y-4">
        <div className="flex items-center gap-3 border-b border-white/5 pb-4">
          <Bell className="h-5 w-5 text-finwell-warning" />
          <h3 className="text-base font-bold text-white">Autonomous Alerts</h3>
        </div>

        <div className="space-y-3 text-xs">
          <label className="flex items-center justify-between rounded-xl bg-finwell-surface p-3.5 border border-white/5 cursor-pointer">
            <div>
              <p className="font-semibold text-white">Duplicate Charge Detection</p>
              <p className="text-[11px] text-finwell-dim mt-0.5">Notify instantly when transactions match &gt; 90% confidence</p>
            </div>
            <input
              type="checkbox"
              checked={notifyDuplicates}
              onChange={(e) => setNotifyDuplicates(e.target.checked)}
              className="rounded border-white/20 bg-finwell-card text-finwell-primary focus:ring-0 h-4 w-4"
            />
          </label>

          <label className="flex items-center justify-between rounded-xl bg-finwell-surface p-3.5 border border-white/5 cursor-pointer">
            <div>
              <p className="font-semibold text-white">High Outflow Warnings</p>
              <p className="text-[11px] text-finwell-dim mt-0.5">Trigger alert when single debit exceeds $1,000.00</p>
            </div>
            <input
              type="checkbox"
              checked={notifyLargeTxn}
              onChange={(e) => setNotifyLargeTxn(e.target.checked)}
              className="rounded border-white/20 bg-finwell-card text-finwell-primary focus:ring-0 h-4 w-4"
            />
          </label>
        </div>
      </TiltCard>
    </div>
  );
};
