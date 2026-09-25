/* eslint-disable react-refresh/only-export-components */
/**
 * AuthContext — Frontend authentication state boundary.
 *
 * Manages authentication state, user session, and token persistence
 * connected to the real backend authentication contract.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { clearAuthToken, getAuthToken } from '../api/client';
import { authService } from '../services/authService';
import type { LoginRequest, SignupRequest, User } from '../types/auth';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AuthContextValue {
  /** True when the user has passed the authentication boundary. */
  isAuthenticated: boolean;

  /** Current authenticated user profile or null if not authenticated. */
  user: User | null;

  /** Authenticate with email & password against the backend. */
  login: (data: LoginRequest) => Promise<User>;

  /** Register a new user with the backend. */
  signup: (data: SignupRequest) => Promise<User>;

  /**
   * DEV-MODE fallback — advance the user past the auth boundary.
   * Preserved for backward compatibility.
   */
  devSignIn: () => void;

  /**
   * Clear the authentication state, revoke backend token, and navigate out.
   */
  signOut: () => void;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => Boolean(getAuthToken()));
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      authService
        .getCurrentUser()
        .then((fetchedUser) => {
          setUser(fetchedUser);
          setIsAuthenticated(true);
        })
        .catch(() => {
          clearAuthToken();
          setUser(null);
          setIsAuthenticated(false);
        });
    }
  }, []);

  const login = useCallback(async (data: LoginRequest) => {
    const loggedInUser = await authService.login(data);
    setUser(loggedInUser);
    setIsAuthenticated(true);
    return loggedInUser;
  }, []);

  const signup = useCallback(async (data: SignupRequest) => {
    return await authService.signup(data);
  }, []);

  const devSignIn = useCallback(() => {
    setIsAuthenticated(true);
  }, []);

  const signOut = useCallback(() => {
    authService.logout().finally(() => {
      setUser(null);
      setIsAuthenticated(false);
    });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ isAuthenticated, user, devSignIn, signOut, login, signup }),
    [isAuthenticated, user, devSignIn, signOut, login, signup],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
