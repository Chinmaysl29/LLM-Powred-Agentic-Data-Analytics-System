/**
 * settingsService.ts
 *
 * Centralized service boundary for application settings and preferences.
 *
 * BACKEND INTEGRATION POINT:
 * When backend settings endpoints are implemented (e.g. GET/PUT /api/settings,
 * POST /api/settings/reset), update these methods to execute real API requests
 * without altering the frontend component contract.
 */

import type { AppSettings } from '../types/settings';

const DEFAULT_SETTINGS: AppSettings = {
  general: {
    language: 'en',
    dateFormat: 'DD/MM/YYYY',
    numberFormat: '1,234.56',
    defaultLandingPage: '/dashboard',
  },
  appearance: {
    theme: 'dark',
    density: 'comfortable',
    animations: true,
    reduceMotion: false,
  },
  ai: {
    defaultModel: 'Automatic',
    responseStyle: 'Detailed',
    analysisDepth: 'Balanced',
    explainReasoning: true,
    showEvidence: true,
    showAssumptions: true,
    showConfidence: true,
    generateRecommendations: true,
  },
  data: {
    previewRows: 100,
    autoDetectTypes: true,
    autoGenerateInsights: true,
    autoGenerateVisualizations: true,
    saveAnalysisHistory: true,
    retainDatasets: true,
  },
  notifications: {
    analysisCompleted: true,
    datasetProcessing: true,
    reportGenerated: true,
    reportGenerationFailed: true,
    systemNotifications: true,
    productUpdates: false,
  },
  privacy: {
    saveAnalysisHistory: true,
    saveConversationHistory: true,
    usePreviousAnalysisContext: true,
  },
  advanced: {
    optimizedRendering: true,
    experimentalFeatures: false,
  },
};

// In-memory development store
let currentSettings: AppSettings = JSON.parse(JSON.stringify(DEFAULT_SETTINGS));

export const settingsService = {
  /**
   * Fetch current application settings.
   * Future: GET /api/settings
   */
  async getSettings(): Promise<AppSettings> {
    await new Promise((resolve) => setTimeout(resolve, 120));
    return JSON.parse(JSON.stringify(currentSettings));
  },

  /**
   * Update category or full settings.
   * Future: PUT /api/settings
   */
  async updateSettings(partial: Partial<AppSettings>): Promise<AppSettings> {
    await new Promise((resolve) => setTimeout(resolve, 250));
    currentSettings = {
      ...currentSettings,
      ...partial,
      general: { ...currentSettings.general, ...(partial.general || {}) },
      appearance: { ...currentSettings.appearance, ...(partial.appearance || {}) },
      ai: { ...currentSettings.ai, ...(partial.ai || {}) },
      data: { ...currentSettings.data, ...(partial.data || {}) },
      notifications: { ...currentSettings.notifications, ...(partial.notifications || {}) },
      privacy: { ...currentSettings.privacy, ...(partial.privacy || {}) },
      advanced: { ...currentSettings.advanced, ...(partial.advanced || {}) },
    };
    return JSON.parse(JSON.stringify(currentSettings));
  },

  /**
   * Reset application settings to factory defaults.
   * Future: POST /api/settings/reset
   */
  async resetSettings(): Promise<AppSettings> {
    await new Promise((resolve) => setTimeout(resolve, 350));
    currentSettings = JSON.parse(JSON.stringify(DEFAULT_SETTINGS));
    return JSON.parse(JSON.stringify(currentSettings));
  },

  /**
   * Return default settings reference.
   */
  getDefaultSettings(): AppSettings {
    return JSON.parse(JSON.stringify(DEFAULT_SETTINGS));
  },
};
