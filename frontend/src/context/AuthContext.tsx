/* eslint-disable react-refresh/only-export-components */
/**
 * AuthContext — Frontend authentication state boundary.
 *
 * ARCHITECTURE NOTE:
 * This context manages the in-memory authentication state for the frontend.
 * It currently uses a dev-mode sign-in mechanism (devSignIn) that sets an
 * in-memory flag without making any real API call.
 *
 * BACKEND INTEGRATION POINT:
 * When backend authentication endpoints are implemented, replace `devSignIn()`
 * with a call to `authService.login()` / `authService.signup()`.
 * The context interface (isAuthenticated, signOut) does not need to change.
 *
 * The context is intentionally minimal. Token storage, session refresh, and
 * user profile caching will be added once the backend auth contract is defined.
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AuthContextValue {
  /** True when the user has passed the authentication boundary. */
  isAuthenticated: boolean;

  /**
   * DEV-MODE ONLY — advance the user past the auth boundary without making
   * a real API call. This simulates a successful login/signup for frontend
   * development purposes.
   *
   * BACKEND DEPENDENCY: Replace this call with authService.login() /
   * authService.signup() once backend authentication endpoints are live.
   */
  devSignIn: () => void;

  /**
   * Clear the authentication state and navigate the user out of the app.
   * Future: will also call authService.logout() to invalidate the session.
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
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const devSignIn = useCallback(() => {
    // BACKEND DEPENDENCY: Replace with real auth token/session storage.
    setIsAuthenticated(true);
  }, []);

  const signOut = useCallback(() => {
    // BACKEND DEPENDENCY: Call authService.logout() here.
    setIsAuthenticated(false);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ isAuthenticated, devSignIn, signOut }),
    [isAuthenticated, devSignIn, signOut],
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
