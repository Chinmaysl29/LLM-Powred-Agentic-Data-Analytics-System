/**
 * Phase 12.8.1 — React Native Redux Store
 * Configured with Redux Toolkit for feature-based state management.
 */

import { configureStore, createSlice, PayloadAction } from '@reduxjs/toolkit';

// Auth Slice
interface AuthState {
  isAuthenticated: boolean;
  accessToken: string | null;
  refreshToken: string | null;
  userId: string | null;
  biometricsEnabled: boolean;
}

const initialAuthState: AuthState = {
  isAuthenticated: false,
  accessToken: null,
  refreshToken: null,
  userId: null,
  biometricsEnabled: false,
};

const authSlice = createSlice({
  name: 'auth',
  initialState: initialAuthState,
  reducers: {
    setCredentials: (
      state,
      action: PayloadAction<{ accessToken: string; refreshToken: string; userId: string }>
    ) => {
      state.isAuthenticated = true;
      state.accessToken = action.payload.accessToken;
      state.refreshToken = action.payload.refreshToken;
      state.userId = action.payload.userId;
    },
    logout: (state) => {
      state.isAuthenticated = false;
      state.accessToken = null;
      state.refreshToken = null;
      state.userId = null;
    },
    setBiometrics: (state, action: PayloadAction<boolean>) => {
      state.biometricsEnabled = action.payload;
    },
  },
});

// Dashboard Slice
interface DashboardState {
  kpis: Array<{ id: string; title: string; value: string }>;
  alerts: Array<{ id: string; title: string; severity: string }>;
  loading: boolean;
}

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState: { kpis: [], alerts: [], loading: false } as DashboardState,
  reducers: {
    setDashboardData: (state, action: PayloadAction<{ kpis: any[]; alerts: any[] }>) => {
      state.kpis = action.payload.kpis;
      state.alerts = action.payload.alerts;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
  },
});

// Root Redux Store
export const store = configureStore({
  reducer: {
    auth: authSlice.reducer,
    dashboard: dashboardSlice.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export const { setCredentials, logout, setBiometrics } = authSlice.actions;
export const { setDashboardData, setLoading } = dashboardSlice.actions;
