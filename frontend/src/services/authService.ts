/**
 * Authentication service boundary.
 *
 * The backend authentication contract is not implemented yet, so this module
 * intentionally avoids endpoint paths, fake tokens, and simulated HTTP
 * successes. Auth screens currently use AuthContext.devSignIn() for the
 * frontend-only navigation boundary.
 */

import type {
  ForgotPasswordRequest,
  LoginRequest,
  ResetPasswordRequest,
  SignupRequest,
  UpdateProfileRequest,
  User,
} from '../types/auth';

function authContractUnavailable(): Promise<never> {
  return Promise.reject(
    new Error('Authentication is not connected yet. Please try again later.'),
  );
}

export const authService = {
  login(_data: LoginRequest): Promise<unknown> {
    void _data;
    return authContractUnavailable();
  },

  signup(_data: SignupRequest): Promise<unknown> {
    void _data;
    return authContractUnavailable();
  },

  logout(): Promise<void> {
    return authContractUnavailable();
  },

  getCurrentUser(): Promise<User> {
    return authContractUnavailable();
  },

  forgotPassword(_data: ForgotPasswordRequest): Promise<void> {
    void _data;
    return authContractUnavailable();
  },

  resetPassword(_data: ResetPasswordRequest): Promise<void> {
    void _data;
    return authContractUnavailable();
  },

  getProfile(): Promise<User> {
    return authContractUnavailable();
  },

  updateProfile(_data: UpdateProfileRequest): Promise<User> {
    void _data;
    return authContractUnavailable();
  },
};
