import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { ChatProvider } from './context/ChatContext';
import { AppLayout } from './components/layout/AppLayout';
import { NavigationPage } from './components/layout/LeftSidebar';

// Pages
import { DashboardPage } from './pages/Dashboard/DashboardPage';
import { AIChatPage } from './pages/AIChat/AIChatPage';
import { AccountsPage } from './pages/Accounts/AccountsPage';
import { TransactionsPage } from './pages/Transactions/TransactionsPage';
import { AnalyticsPage } from './pages/Analytics/AnalyticsPage';
import { ReconciliationPage } from './pages/Reconciliation/ReconciliationPage';
import { DocumentsPage } from './pages/Documents/DocumentsPage';
import { ReportsPage } from './pages/Reports/ReportsPage';
import { SettingsPage } from './pages/Settings/SettingsPage';

// Auth Pages
import { LoginPage } from './pages/Login/LoginPage';
import { RegisterPage } from './pages/Register/RegisterPage';
import { ForgotPasswordPage } from './pages/ForgotPassword/ForgotPasswordPage';

type AuthView = 'login' | 'register' | 'forgot-password';

const MainAppContent: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [currentPage, setCurrentPage] = useState<NavigationPage>('dashboard');
  const [authView, setAuthView] = useState<AuthView>('login');

  // If unauthenticated, show auth flow
  if (!isAuthenticated) {
    if (authView === 'register') {
      return <RegisterPage onNavigateToLogin={() => setAuthView('login')} />;
    }
    if (authView === 'forgot-password') {
      return <ForgotPasswordPage onNavigateToLogin={() => setAuthView('login')} />;
    }
    return (
      <LoginPage
        onNavigateToRegister={() => setAuthView('register')}
        onNavigateToForgotPassword={() => setAuthView('forgot-password')}
      />
    );
  }

  // Render current dashboard page inside AppLayout
  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <DashboardPage onNavigate={setCurrentPage} />;
      case 'ai-chat':
        return <AIChatPage />;
      case 'accounts':
        return <AccountsPage />;
      case 'transactions':
        return <TransactionsPage />;
      case 'analytics':
        return <AnalyticsPage />;
      case 'reconciliation':
        return <ReconciliationPage />;
      case 'documents':
        return <DocumentsPage />;
      case 'reports':
        return <ReportsPage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <DashboardPage onNavigate={setCurrentPage} />;
    }
  };

  return (
    <AppLayout currentPage={currentPage} onSelectPage={setCurrentPage}>
      {renderCurrentPage()}
    </AppLayout>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ChatProvider>
          <MainAppContent />
        </ChatProvider>
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;
