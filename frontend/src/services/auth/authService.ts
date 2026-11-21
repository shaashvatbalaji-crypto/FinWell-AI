import { apiClient } from '../api/apiClient';
import { User } from '../../types';
import { MOCK_USER } from '../../mock/mockData';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}

export interface AuthResponse {
  success: boolean;
  message?: string;
  access_token?: string;
  token_type?: string;
  expires_in?: number;
  user: User;
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    if (apiClient.isMockMode()) {
      // Simulate realistic API delay
      await new Promise((r) => setTimeout(r, 600));

      if (!credentials.email || !credentials.password) {
        throw new Error('Please enter both email and password.');
      }

      // Allow any mock login or specific demo credential
      const mockToken = 'mock_jwt_finwell_demo_token_123456';
      apiClient.setToken(mockToken);
      
      return {
        success: true,
        access_token: mockToken,
        token_type: 'bearer',
        expires_in: 86400,
        user: {
          ...MOCK_USER,
          email: credentials.email,
        },
      };
    }

    // Real FastAPI endpoint: POST /api/auth/login
    const data = await apiClient.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email: credentials.email,
        password: credentials.password,
      }),
    });

    if (data.access_token) {
      apiClient.setToken(data.access_token);
    }
    return data;
  },

  async register(credentials: RegisterCredentials): Promise<AuthResponse> {
    if (apiClient.isMockMode()) {
      await new Promise((r) => setTimeout(r, 700));

      if (credentials.password.length < 8) {
        throw new Error('Password must be at least 8 characters long.');
      }

      const mockToken = 'mock_jwt_finwell_registered_token_789';
      apiClient.setToken(mockToken);

      return {
        success: true,
        message: 'Account created successfully in demo mode.',
        access_token: mockToken,
        user: {
          user_id: 102,
          username: credentials.username,
          email: credentials.email,
          full_name: credentials.full_name || credentials.username,
          avatar: MOCK_USER.avatar,
        },
      };
    }

    // Real FastAPI endpoint: POST /api/auth/register
    return await apiClient.request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        username: credentials.username,
        email: credentials.email,
        password: credentials.password,
      }),
    });
  },

  async forgotPassword(email: string): Promise<{ success: boolean; message: string }> {
    await new Promise((r) => setTimeout(r, 500));
    return {
      success: true,
      message: `Password reset instructions sent to ${email} (Demo interaction).`,
    };
  },

  logout(): void {
    apiClient.setToken(null);
  },

  getCurrentUser(): User | null {
    if (apiClient.getToken()) {
      return MOCK_USER;
    }
    return null;
  },
};
