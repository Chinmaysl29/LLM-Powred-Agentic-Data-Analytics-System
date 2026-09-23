/**
 * Profile and account domain types.
 *
 * BACKEND INTEGRATION POINT:
 * When user profile, account, security, and preferences endpoints are
 * implemented on the backend (e.g. GET/PUT /api/users/me, PUT /api/users/preferences),
 * reconcile these types with the backend schema.
 */

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
  initials: string;
  phone?: string;
  organization?: string;
  role: string;
  accountStatus: 'Active' | 'Pending' | 'Suspended';
  emailVerified: boolean;
  memberSince: string;
}

export interface NotificationPreferences {
  analysisCompleted: boolean;
  reportGenerated: boolean;
  datasetProcessing: boolean;
  systemUpdates: boolean;
}

export type ThemePreference = 'dark';
export type LanguagePreference = 'en' | 'es' | 'fr' | 'de';
export type DateFormatPreference = 'DD/MM/YYYY' | 'MM/DD/YYYY' | 'YYYY-MM-DD';

export interface UserPreferences {
  theme: ThemePreference;
  language: LanguagePreference;
  dateFormat: DateFormatPreference;
  notifications: NotificationPreferences;
}

export type AIModelPreference = 'Automatic';
export type AIResponseStyle = 'Concise' | 'Balanced' | 'Detailed';

export interface AIPreferences {
  defaultModel: AIModelPreference;
  responseStyle: AIResponseStyle;
  explainEvidence: boolean;
  showAssumptions: boolean;
  explainAnomalies: boolean;
  includeRecommendations: boolean;
  showConfidence: boolean;
}

export interface ActiveSession {
  id: string;
  browser: string;
  os: string;
  ipAddress?: string;
  location: string;
  isCurrent: boolean;
  lastActive: string;
}

export interface UpdateProfilePayload {
  name: string;
  email: string;
  phone?: string;
  organization?: string;
}

export interface ChangePasswordPayload {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}
