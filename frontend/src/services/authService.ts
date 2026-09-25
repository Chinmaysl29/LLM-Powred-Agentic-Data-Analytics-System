/**
 * Authentication service boundary connected to the real FastAPI backend.
 *
 * Implements:
 * - login: POST /api/v1/auth/login -> persist token -> GET /api/v1/auth/me
 * - signup: POST /api/v1/auth/register with { email, password, full_name }
 * - logout: POST /api/v1/auth/logout -> clear token
 * - getCurrentUser: GET /api/v1/auth/me
 */

import { apiClient, clearAuthToken, setAuthToken } from '../api/client';
import type {
  ForgotPasswordRequest,
  LoginRequest,
  ResetPasswordRequest,
  SignupRequest,
  UpdateProfileRequest,
  User,
} from '../types/auth';

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

interface BackendUserResponse {
  id: string;
  email: string;
  full_name: string;
  role?: string;
  is_active?: boolean;
}

function mapUserResponse(user: BackendUserResponse): User {
  return {
    id: user.id,
    email: user.email,
    full_name: user.full_name,
    created_at: new Date().toISOString(),
  };
}

export const authService = {
  async login(data: LoginRequest): Promise<User> {
    const res = await apiClient.post<AuthResponse>('/api/v1/auth/login', {
      email: data.email,
      password: data.password,
    });
    setAuthToken(res.access_token);
    const userRes = await apiClient.get<BackendUserResponse>('/api/v1/auth/me');
    return mapUserResponse(userRes);
  },

  async signup(data: SignupRequest): Promise<User> {
    const userRes = await apiClient.post<BackendUserResponse>('/api/v1/auth/register', {
      email: data.email,
      password: data.password,
      full_name: data.full_name,
    });
    return mapUserResponse(userRes);
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/api/v1/auth/logout', {});
    } catch {
      // Proceed with local token removal even if server revocation failed
    } finally {
      clearAuthToken();
    }
  },

  async getCurrentUser(): Promise<User> {
    const userRes = await apiClient.get<BackendUserResponse>('/api/v1/auth/me');
    return mapUserResponse(userRes);
  },

  forgotPassword(_data: ForgotPasswordRequest): Promise<void> {
    void _data;
    return Promise.reject(
      new Error('Forgot password is not supported by the backend yet.'),
    );
  },

  resetPassword(_data: ResetPasswordRequest): Promise<void> {
    void _data;
    return Promise.reject(
      new Error('Reset password is not supported by the backend yet.'),
    );
  },

  getProfile(): Promise<User> {
    return this.getCurrentUser();
  },

  updateProfile(_data: UpdateProfileRequest): Promise<User> {
    void _data;
    return Promise.reject(
      new Error('Profile update is not supported by the backend yet.'),
    );
  },
};
