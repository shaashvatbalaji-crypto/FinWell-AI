import React, { useState, useEffect } from 'react';
import {
  Wallet,
  Plus,
  Building,
  CreditCard,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  ExternalLink,
  History,
  CheckCircle2,
} from 'lucide-react';
import { TiltCard } from '../../components/3d/TiltCard';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { Modal } from '../../components/common/Modal';
import { accountService, CreateAccountDTO } from '../../services/accounts/accountService';
import { Account, AccountType, Transaction } from '../../types';
import { transactionService } from '../../services/transactions/transactionService';
import { formatCurrency } from '../../utils/formatters';

export const AccountsPage: React.FC = () => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [accountTransactions, setAccountTransactions] = useState<Transaction[]>([]);
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Form State
  const [formData, setFormData] = useState<CreateAccountDTO>({
    account_name: '',
    institution_name: '',
    account_type: 'savings',
    masked_account_number: '',
    currency: 'INR',
    initial_balance: 0,
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  const loadAccounts = async () => {
    const list = await accountService.getAccounts();
    setAccounts(list);
  };

  useEffect(() => {
    loadAccounts();
  }, []);

  const handleOpenDetails = async (acc: Account) => {
    setSelectedAccount(acc);
    setIsDetailsModalOpen(true);
    const txns = await transactionService.getTransactions({ accountId: acc.account_id });
    setAccountTransactions(txns.transactions);
  };

  const validateForm = () => {
    const errors: Record<string, string> = {};
    if (!formData.account_name.trim()) errors.account_name = 'Account name is required';
    if (!formData.institution_name.trim()) errors.institution_name = 'Bank or institution is required';
    if (!formData.masked_account_number.trim() || formData.masked_account_number.length < 4) {
      errors.masked_account_number = 'Enter at least the last 4 digits of the account number';
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      await accountService.createAccount(formData);
      await loadAccounts();
      setIsAddModalOpen(false);
      setFormData({
        account_name: '',
        institution_name: '',
        account_type: 'savings',
        masked_account_number: '',
        currency: 'USD',
        initial_balance: 0,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const getAccountBadge = (type: AccountType) => {
    switch (type) {
      case 'current':
        return <Badge variant="primary" size="sm">Checking / Current</Badge>;
      case 'savings':
        return <Badge variant="cyan" size="sm">High-Yield Savings</Badge>;
      case 'investment':
        return <Badge variant="violet" size="sm">Investment & Portfolio</Badge>;
      case 'credit_card':
        return <Badge variant="danger" size="sm">Credit Facility</Badge>;
      default:
        return <Badge variant="neutral" size="sm">{type}</Badge>;
    }
  };

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header & Add Button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white flex items-center gap-2">
            Connected Accounts & Vaults
            <Badge variant="cyan" size="sm">
              {accounts.length} Active
            </Badge>
          </h1>
          <p className="text-xs text-finwell-muted mt-1">
            Centralized multi-institution balances linked to FinWell transaction engine.
          </p>
        </div>

        <Button
          variant="primary"
          glow
          onClick={() => setIsAddModalOpen(true)}
          icon={<Plus className="h-4 w-4" />}
        >
          Add New Account
        </Button>
      </div>

      {/* Account Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6">
        {accounts.map((acc) => (
          <TiltCard
            key={acc.account_id}
            className="p-6 flex flex-col justify-between cursor-pointer border border-white/10 hover:border-finwell-primary/50 transition-all"
          >
            <div>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="flex h-12 w-12 items-center justify-center rounded-2xl shadow-sm"
                    style={{ backgroundColor: `${acc.color || '#4263FF'}20`, color: acc.color || '#4263FF' }}
                  >
                    {acc.account_type === 'credit_card' ? (
                      <CreditCard className="h-6 w-6" />
                    ) : (
                      <Building className="h-6 w-6" />
                    )}
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white">{acc.account_name}</h3>
                    <p className="text-xs text-finwell-dim mt-0.5">{acc.institution_name}</p>
                  </div>
                </div>

                {getAccountBadge(acc.account_type)}
              </div>

              {/* Account Number & Balance */}
              <div className="mt-6 flex items-baseline justify-between border-t border-white/5 pt-4">
                <div>
                  <span className="text-[11px] font-mono text-finwell-dim uppercase tracking-wider">
                    Account Reference
                  </span>
                  <p className="text-xs font-mono font-bold text-finwell-muted mt-0.5">
                    {acc.masked_account_number}
                  </p>
                </div>

                <div className="text-right">
                  <span className="text-[11px] font-semibold text-finwell-dim uppercase tracking-wider">
                    Recorded Balance
                  </span>
                  <p
                    className={`text-xl font-extrabold mt-0.5 ${
                      acc.current_balance < 0 ? 'text-finwell-danger' : 'text-white'
                    }`}
                  >
                    {formatCurrency(acc.current_balance, acc.currency)}
                  </p>
                </div>
              </div>
            </div>

            {/* Card Footer Actions */}
            <div className="mt-6 pt-4 border-t border-white/5 flex items-center justify-between text-xs">
              <span className="text-finwell-dim flex items-center gap-1.5 text-[11px]">
                <RefreshCw className="h-3 w-3 text-finwell-cyan" /> Synced {acc.last_synced || 'Recently'}
              </span>

              <button
                onClick={() => handleOpenDetails(acc)}
                className="font-semibold text-finwell-primary hover:text-finwell-cyan flex items-center gap-1 transition-colors"
              >
                <span>Audit Ledger</span>
                <History className="h-3.5 w-3.5" />
              </button>
            </div>
          </TiltCard>
        ))}
      </div>

      {/* Add Account Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Connect New Financial Account"
        subtitle="Registers an institutional vault in the FinWell MySQL schema."
      >
        <form onSubmit={handleCreateAccount} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-finwell-muted mb-1">
              Account Friendly Name
            </label>
            <input
              type="text"
              placeholder="e.g. Wealthfront Cash Reserve"
              value={formData.account_name}
              onChange={(e) => setFormData({ ...formData, account_name: e.target.value })}
              className="w-full rounded-xl border border-white/10 bg-finwell-surface px-3.5 py-2.5 text-xs text-white placeholder-finwell-dim focus:border-finwell-primary focus:outline-none"
            />
            {formErrors.account_name && (
              <p className="text-[11px] text-finwell-danger mt-1">{formErrors.account_name}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-finwell-muted mb-1">
                Banking Institution
              </label>
              <input
                type="text"
                placeholder="e.g. Citibank"
                value={formData.institution_name}
                onChange={(e) => setFormData({ ...formData, institution_name: e.target.value })}
                className="w-full rounded-xl border border-white/10 bg-finwell-surface px-3.5 py-2.5 text-xs text-white placeholder-finwell-dim focus:border-finwell-primary focus:outline-none"
              />
              {formErrors.institution_name && (
                <p className="text-[11px] text-finwell-danger mt-1">{formErrors.institution_name}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-finwell-muted mb-1">
                Account Classification
              </label>
              <select
                value={formData.account_type}
                onChange={(e) => setFormData({ ...formData, account_type: e.target.value as AccountType })}
                className="w-full rounded-xl border border-white/10 bg-finwell-surface px-3.5 py-2.5 text-xs text-white focus:border-finwell-primary focus:outline-none"
              >
                <option value="savings">Savings Account</option>
                <option value="current">Current / Checking</option>
                <option value="salary">Salary Account</option>
                <option value="credit_card">Credit Card</option>
                <option value="investment">Investment Portfolio</option>
                <option value="loan">Loan / Credit Line</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-finwell-muted mb-1">
                Masked Number (Last 4 Digits)
              </label>
              <input
                type="text"
                placeholder="•••• 1234"
                maxLength={9}
                value={formData.masked_account_number}
                onChange={(e) => setFormData({ ...formData, masked_account_number: e.target.value })}
                className="w-full rounded-xl border border-white/10 bg-finwell-surface px-3.5 py-2.5 text-xs text-white placeholder-finwell-dim focus:border-finwell-primary focus:outline-none font-mono"
              />
              {formErrors.masked_account_number && (
                <p className="text-[11px] text-finwell-danger mt-1">{formErrors.masked_account_number}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-finwell-muted mb-1">
                Opening Balance ($)
              </label>
              <input
                type="number"
                step="0.01"
                placeholder="0.00"
                value={formData.initial_balance || ''}
                onChange={(e) => setFormData({ ...formData, initial_balance: parseFloat(e.target.value) || 0 })}
                className="w-full rounded-xl border border-white/10 bg-finwell-surface px-3.5 py-2.5 text-xs text-white placeholder-finwell-dim focus:border-finwell-primary focus:outline-none font-mono"
              />
            </div>
          </div>

          <div className="pt-4 flex justify-end gap-3 border-t border-white/5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsAddModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              glow
              isLoading={isSubmitting}
            >
              Register Account
            </Button>
          </div>
        </form>
      </Modal>

      {/* Account Details & Transaction History Modal */}
      {selectedAccount && (
        <Modal
          isOpen={isDetailsModalOpen}
          onClose={() => setIsDetailsModalOpen(false)}
          title={selectedAccount.account_name}
          subtitle={`${selectedAccount.institution_name} • ${selectedAccount.masked_account_number}`}
          maxWidth="lg"
        >
          <div className="space-y-4">
            <div className="rounded-xl bg-finwell-surface p-4 flex items-center justify-between border border-white/5">
              <div>
                <span className="text-[10px] text-finwell-dim uppercase font-semibold">Active Ledger Balance</span>
                <p className="text-xl font-bold text-white mt-0.5">
                  ${selectedAccount.current_balance.toLocaleString('en-US', { minimumFractionDigits: 2 })} {selectedAccount.currency}
                </p>
              </div>
              <Badge variant="success" size="md">
                Verified In MySQL
              </Badge>
            </div>

            <div className="space-y-2">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                <History className="h-4 w-4 text-finwell-cyan" />
                Ledger Entries for this Account
              </h4>

              {accountTransactions.length === 0 ? (
                <div className="py-8 text-center text-xs text-finwell-dim">
                  No direct transactions recorded for this account in demo state.
                </div>
              ) : (
                <div className="divide-y divide-white/5 max-h-60 overflow-y-auto pr-1">
                  {accountTransactions.map((t) => (
                    <div key={t.transaction_id} className="py-2.5 flex items-center justify-between text-xs">
                      <div>
                        <p className="font-semibold text-white">{t.description}</p>
                        <p className="text-[11px] text-finwell-dim">{t.transaction_date} • {t.category}</p>
                      </div>
                      <span
                        className={`font-bold font-mono ${
                          t.direction === 'credit' ? 'text-finwell-success' : 'text-white'
                        }`}
                      >
                        {t.direction === 'credit' ? '+' : '-'}${t.amount.toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
