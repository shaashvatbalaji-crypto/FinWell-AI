import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import { authService, LoginCredentials, RegisterCredentials } from '../services/auth/authService';
import { apiClient } from '../services/api/apiClient';
import { MOCK_USER } from '../mock/mockData';

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  isMockMode: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => void;
  setMockMode: (enabled: boolean) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    return !!apiClient.getToken() || apiClient.isMockMode();
  });
  const [user, setUser] = useState<User | null>(() => {
    return authService.getCurrentUser() || (apiClient.isMockMode() ? MOCK_USER : null);
  });
  const [isMockMode, setIsMockModeState] = useState<boolean>(apiClient.isMockMode());
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    const token = apiClient.getToken();
    const currentUser = authService.getCurrentUser();
    if (token && currentUser) {
      setIsAuthenticated(true);
      setUser(currentUser);
    } else if (apiClient.isMockMode()) {
      setIsAuthenticated(true);
      setUser(MOCK_USER);
    }

    const handleAuthExpired = () => {
      setIsAuthenticated(false);
      setUser(null);
    };

    window.addEventListener('finwell:auth-expired', handleAuthExpired);
    return () => window.removeEventListener('finwell:auth-expired', handleAuthExpired);
  }, []);

  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true);
    try {
      const res = await authService.login(credentials);
      setUser(res.user);
      setIsAuthenticated(true);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (credentials: RegisterCredentials) => {
    setIsLoading(true);
    try {
      const res = await authService.register(credentials);
      setUser(res.user);
      setIsAuthenticated(true);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    authService.logout();
    apiClient.setMockMode(false);
    setIsAuthenticated(false);
    setUser(null);
  };

  const setMockMode = (enabled: boolean) => {
    apiClient.setMockMode(enabled);
    setIsMockModeState(enabled);
    if (enabled && !user) {
      setUser(MOCK_USER);
      setIsAuthenticated(true);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        user,
        isMockMode,
        isLoading,
        login,
        register,
        logout,
        setMockMode,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
