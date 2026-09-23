/**
 * profileService.ts
 *
 * Centralized service boundary for Profile, Account Security, Preferences,
 * and AI Experience settings.
 *
 * BACKEND INTEGRATION POINT:
 * Backend endpoints for user profile and preferences are not implemented yet.
 * This module manages in-memory development state and contract-ready stubs.
 * When real endpoints (e.g. GET/PUT /api/users/me, PUT /api/users/preferences)
 * are available, update these functions to execute API requests without
 * changing the component interface.
 */

import type {
  UserProfile,
  UserPreferences,
  AIPreferences,
  ActiveSession,
  UpdateProfilePayload,
  ChangePasswordPayload,
} from '../types/profile';

// In-memory development data store
let mockProfile: UserProfile = {
  id: 'usr_89201',
  name: 'Alex Morgan',
  email: 'alex.morgan@enterprise.ai',
  initials: 'AM',
  phone: '+1 (555) 234-5678',
  organization: 'Apex Global Analytics',
  role: 'AI Data Analyst User',
  accountStatus: 'Active',
  emailVerified: true,
  memberSince: 'September 2026',
};

let mockPreferences: UserPreferences = {
  theme: 'dark',
  language: 'en',
  dateFormat: 'DD/MM/YYYY',
  notifications: {
    analysisCompleted: true,
    reportGenerated: true,
    datasetProcessing: true,
    systemUpdates: false,
  },
};

let mockAIPreferences: AIPreferences = {
  defaultModel: 'Automatic',
  responseStyle: 'Detailed',
  explainEvidence: true,
  showAssumptions: true,
  explainAnomalies: true,
  includeRecommendations: true,
  showConfidence: true,
};

let mockSessions: ActiveSession[] = [
  {
    id: 'sess_1',
    browser: 'Chrome 128',
    os: 'Windows 11',
    location: 'Bangalore, IN',
    isCurrent: true,
    lastActive: 'Active now',
  },
  {
    id: 'sess_2',
    browser: 'Safari 18',
    os: 'macOS Sonoma',
    location: 'Mumbai, IN',
    isCurrent: false,
    lastActive: '2 days ago',
  },
];

// Helper to compute initials
function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return (name[0] || 'U').toUpperCase();
}

export const profileService = {
  /**
   * Fetch current user profile.
   * Future: GET /api/users/me
   */
  async getProfile(): Promise<UserProfile> {
    await new Promise((resolve) => setTimeout(resolve, 150));
    return { ...mockProfile };
  },

  /**
   * Update personal profile information.
   * Future: PUT /api/users/me
   */
  async updateProfile(payload: UpdateProfilePayload): Promise<UserProfile> {
    await new Promise((resolve) => setTimeout(resolve, 300));

    if (!payload.name || payload.name.trim().length === 0) {
      throw new Error('Full Name is required.');
    }
    if (!payload.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.email)) {
      throw new Error('A valid email address is required.');
    }

    mockProfile = {
      ...mockProfile,
      name: payload.name.trim(),
      email: payload.email.trim(),
      initials: getInitials(payload.name),
      phone: payload.phone?.trim() || '',
      organization: payload.organization?.trim() || '',
    };

    return { ...mockProfile };
  },

  /**
   * Fetch user preferences.
   * Future: GET /api/users/preferences
   */
  async getPreferences(): Promise<UserPreferences> {
    await new Promise((resolve) => setTimeout(resolve, 100));
    return { ...mockPreferences };
  },

  /**
   * Update user preferences.
   * Future: PUT /api/users/preferences
   */
  async updatePreferences(payload: Partial<UserPreferences>): Promise<UserPreferences> {
    await new Promise((resolve) => setTimeout(resolve, 200));
    mockPreferences = {
      ...mockPreferences,
      ...payload,
      notifications: {
        ...mockPreferences.notifications,
        ...(payload.notifications || {}),
      },
    };
    return { ...mockPreferences };
  },

  /**
   * Fetch AI experience preferences.
   * Future: GET /api/users/ai-preferences
   */
  async getAIPreferences(): Promise<AIPreferences> {
    await new Promise((resolve) => setTimeout(resolve, 100));
    return { ...mockAIPreferences };
  },

  /**
   * Update AI experience preferences.
   * Future: PUT /api/users/ai-preferences
   */
  async updateAIPreferences(payload: Partial<AIPreferences>): Promise<AIPreferences> {
    await new Promise((resolve) => setTimeout(resolve, 200));
    mockAIPreferences = {
      ...mockAIPreferences,
      ...payload,
    };
    return { ...mockAIPreferences };
  },

  /**
   * Fetch active sessions.
   * Future: GET /api/users/sessions
   */
  async getActiveSessions(): Promise<ActiveSession[]> {
    await new Promise((resolve) => setTimeout(resolve, 150));
    return [...mockSessions];
  },

  /**
   * Sign out other sessions.
   * Future: POST /api/users/sessions/revoke-others
   */
  async revokeOtherSessions(): Promise<ActiveSession[]> {
    await new Promise((resolve) => setTimeout(resolve, 300));
    mockSessions = mockSessions.filter((s) => s.isCurrent);
    return [...mockSessions];
  },

  /**
   * Change user password.
   * Future: POST /api/users/change-password
   */
  async changePassword(payload: ChangePasswordPayload): Promise<{ success: boolean; message: string }> {
    await new Promise((resolve) => setTimeout(resolve, 400));

    if (!payload.currentPassword) {
      throw new Error('Current password is required.');
    }
    if (!payload.newPassword || payload.newPassword.length < 8) {
      throw new Error('New password must be at least 8 characters.');
    }
    if (payload.newPassword !== payload.confirmPassword) {
      throw new Error('New passwords do not match.');
    }

    return { success: true, message: 'Password updated successfully.' };
  },

  /**
   * Contract-ready resend email verification.
   * Future: POST /api/users/resend-verification
   */
  async resendVerificationEmail(): Promise<{ sent: boolean }> {
    await new Promise((resolve) => setTimeout(resolve, 300));
    return { sent: true };
  },

  /**
   * Contract-ready request account data export.
   * Future: POST /api/users/export-data
   */
  async requestDataExport(): Promise<{ requested: boolean; estimatedMinutes: number }> {
    await new Promise((resolve) => setTimeout(resolve, 350));
    return { requested: true, estimatedMinutes: 10 };
  },

  /**
   * Contract-ready delete account request.
   * Future: DELETE /api/users/me
   */
  async deleteAccount(): Promise<{ scheduled: boolean }> {
    await new Promise((resolve) => setTimeout(resolve, 500));
    return { scheduled: true };
  },
};
