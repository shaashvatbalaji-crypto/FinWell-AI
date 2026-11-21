// ==========================================
// FINWELL AI — CENTRALIZED API CLIENT
// Routes requests to real FastAPI endpoints or mock data
// ==========================================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

class ApiClient {
  private baseURL: string;
  private token: string | null = null;
  private mockMode: boolean = true;

  constructor() {
    this.baseURL = API_BASE_URL;
    // Check localStorage for saved preferences
    const savedToken = localStorage.getItem('finwell_token');
    const savedMockPref = localStorage.getItem('finwell_mock_mode');
    
    if (savedToken) {
      this.token = savedToken;
    }
    
    // Default to mockMode = true for standalone evaluation
    this.mockMode = savedMockPref !== null ? savedMockPref === 'true' : true;
  }

  public getBaseURL(): string {
    return this.baseURL;
  }

  public setBaseURL(url: string): void {
    this.baseURL = url;
  }

  public setToken(token: string | null): void {
    this.token = token;
    if (token) {
      localStorage.setItem('finwell_token', token);
    } else {
      localStorage.removeItem('finwell_token');
    }
  }

  public getToken(): string | null {
    return this.token;
  }

  public isMockMode(): boolean {
    return this.mockMode;
  }

  public setMockMode(enabled: boolean): void {
    this.mockMode = enabled;
    localStorage.setItem('finwell_mock_mode', String(enabled));
  }

  // Base HTTP request handler for real FastAPI connection
  public async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Request failed with status ${response.status}`);
      }

      return (await response.json()) as T;
    } catch (err: any) {
      console.warn(`[FinWell API] Network request to ${url} failed:`, err.message);
      throw err;
    }
  }
}

export const apiClient = new ApiClient();
