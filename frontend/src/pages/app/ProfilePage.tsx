import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  User,
  Mail,
  Phone,
  Building,
  Shield,
  ShieldCheck,
  CheckCircle2,
  Lock,
  Smartphone,
  Laptop,
  LogOut,
  Moon,
  Globe,
  Calendar,
  Bell,
  Sparkles,
  Sliders,
  Database,
  Download,
  AlertTriangle,
  Edit3,
  Save,
  X,
  Loader2,
  RotateCw,
  Camera,
  Check,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { profileService } from '../../services/profileService';
import type {
  UserProfile,
  UserPreferences,
  AIPreferences,
  ActiveSession,
  DateFormatPreference,
  AIResponseStyle,
} from '../../types/profile';
import { ChangePasswordModal } from '../../components/profile/ChangePasswordModal';
import { DeleteAccountModal } from '../../components/profile/DeleteAccountModal';

export default function ProfilePage() {
  const { signOut } = useAuth();
  const navigate = useNavigate();

  // Primary data states
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [aiPreferences, setAiPreferences] = useState<AIPreferences | null>(null);
  const [sessions, setSessions] = useState<ActiveSession[]>([]);

  // Loading & error states
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Edit Personal Information state
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [editFormData, setEditFormData] = useState({
    name: '',
    email: '',
    phone: '',
    organization: '',
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileSaveSuccess, setProfileSaveSuccess] = useState(false);

  // Modals state
  const [isChangePasswordOpen, setIsChangePasswordOpen] = useState(false);
  const [isDeleteAccountOpen, setIsDeleteAccountOpen] = useState(false);

  // Transient feedback toast
  const [feedbackToast, setFeedbackToast] = useState<{ message: string; type: 'success' | 'info' } | null>(null);

  const showToast = (message: string, type: 'success' | 'info' = 'success') => {
    setFeedbackToast({ message, type });
    setTimeout(() => {
      setFeedbackToast(null);
    }, 3000);
  };

  // Load all profile data
  const loadData = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [profData, prefData, aiPrefData, sessData] = await Promise.all([
        profileService.getProfile(),
        profileService.getPreferences(),
        profileService.getAIPreferences(),
        profileService.getActiveSessions(),
      ]);

      setProfile(profData);
      setPreferences(prefData);
      setAiPreferences(aiPrefData);
      setSessions(sessData);

      setEditFormData({
        name: profData.name,
        email: profData.email,
        phone: profData.phone || '',
        organization: profData.organization || '',
      });
    } catch {
      setLoadError('Unable to load profile. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle Edit mode toggle
  const handleStartEdit = () => {
    if (profile) {
      setEditFormData({
        name: profile.name,
        email: profile.email,
        phone: profile.phone || '',
        organization: profile.organization || '',
      });
      setFormErrors({});
      setIsEditingProfile(true);
    }
  };

  const handleCancelEdit = () => {
    if (profile) {
      setEditFormData({
        name: profile.name,
        email: profile.email,
        phone: profile.phone || '',
        organization: profile.organization || '',
      });
    }
    setFormErrors({});
    setIsEditingProfile(false);
  };

  // Handle Profile Save
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    const errors: Record<string, string> = {};

    if (!editFormData.name.trim()) {
      errors.name = 'Full name is required.';
    }
    if (!editFormData.email.trim()) {
      errors.email = 'Email address is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(editFormData.email.trim())) {
      errors.email = 'Please provide a valid email address.';
    }

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    setFormErrors({});
    setIsSavingProfile(true);
    try {
      const updated = await profileService.updateProfile({
        name: editFormData.name,
        email: editFormData.email,
        phone: editFormData.phone,
        organization: editFormData.organization,
      });
      setProfile(updated);
      setProfileSaveSuccess(true);
      setIsEditingProfile(false);
      showToast('Personal information updated successfully.');
      setTimeout(() => setProfileSaveSuccess(false), 2000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unable to save profile changes.';
      setFormErrors({ general: msg });
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Handle Resend Verification
  const handleResendVerification = async () => {
    try {
      await profileService.resendVerificationEmail();
      showToast('Verification email sent to your inbox.');
    } catch {
      showToast('Failed to resend verification email.', 'info');
    }
  };

  // Handle Revoke Other Sessions
  const handleRevokeOtherSessions = async () => {
    try {
      const remaining = await profileService.revokeOtherSessions();
      setSessions(remaining);
      showToast('All other active sessions have been terminated.');
    } catch {
      showToast('Failed to revoke sessions.', 'info');
    }
  };

  // Handle Preferences updates
  const handleUpdateDateFormat = async (dateFormat: DateFormatPreference) => {
    if (!preferences) return;
    try {
      const updated = await profileService.updatePreferences({ dateFormat });
      setPreferences(updated);
      showToast(`Date format updated to ${dateFormat}`);
    } catch {
      showToast('Failed to update date format', 'info');
    }
  };

  const handleToggleNotification = async (key: keyof UserPreferences['notifications']) => {
    if (!preferences) return;
    const nextVal = !preferences.notifications[key];
    const updatedNotifications = {
      ...preferences.notifications,
      [key]: nextVal,
    };
    try {
      const updated = await profileService.updatePreferences({ notifications: updatedNotifications });
      setPreferences(updated);
      showToast('Notification preference updated.');
    } catch {
      showToast('Failed to update notification setting.', 'info');
    }
  };

  // Handle AI Preferences updates
  const handleUpdateResponseStyle = async (responseStyle: AIResponseStyle) => {
    if (!aiPreferences) return;
    try {
      const updated = await profileService.updateAIPreferences({ responseStyle });
      setAiPreferences(updated);
      showToast(`AI Response style set to ${responseStyle}`);
    } catch {
      showToast('Failed to update AI response style.', 'info');
    }
  };

  const handleToggleAIPreference = async (key: keyof AIPreferences) => {
    if (!aiPreferences) return;
    if (key === 'defaultModel' || key === 'responseStyle') return;

    const nextVal = !aiPreferences[key];
    try {
      const updated = await profileService.updateAIPreferences({ [key]: nextVal });
      setAiPreferences(updated);
      showToast('AI analysis preference updated.');
    } catch {
      showToast('Failed to update AI preference.', 'info');
    }
  };

  // Handle Data Export Request
  const handleRequestDataExport = async () => {
    try {
      const res = await profileService.requestDataExport();
      showToast(`Account export initiated. Estimated preparation time: ~${res.estimatedMinutes} minutes.`);
    } catch {
      showToast('Failed to initiate data export.', 'info');
    }
  };

  // Render Loading State
  if (loading) {
    return (
      <div className="ws-page profile-page-container">
        <div className="profile-loading-skeleton">
          <Loader2 size={32} className="profile-spinner" />
          <p>Loading profile and preferences...</p>
        </div>
      </div>
    );
  }

  // Render Error State
  if (loadError || !profile) {
    return (
      <div className="ws-page profile-page-container">
        <div className="profile-error-container">
          <AlertTriangle size={36} className="profile-danger-text" />
          <h2>Unable to load profile</h2>
          <p>{loadError || 'Something went wrong while loading your account information.'}</p>
          <button type="button" className="profile-btn-primary" onClick={loadData}>
            <RotateCw size={15} />
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="ws-page profile-page-container">
      {/* Toast Notification */}
      {feedbackToast && (
        <div className="profile-toast" role="status" aria-live="polite">
          <CheckCircle2 size={16} />
          <span>{feedbackToast.message}</span>
        </div>
      )}

      {/* Page Header */}
      <header className="profile-page-header">
        <div>
          <h1 className="ws-page-heading">Profile</h1>
          <p className="ws-page-sub">Manage your account, preferences and AI experience.</p>
        </div>
      </header>

      {/* ── 1. Profile Overview Card ── */}
      <section className="profile-card profile-overview-card" aria-label="Profile Overview">
        <div className="profile-overview-content">
          <div className="profile-avatar-container">
            <div className="profile-avatar-large" aria-label={`Avatar for ${profile.name}`}>
              {profile.initials}
            </div>
            <button
              type="button"
              className="profile-avatar-upload-boundary"
              title="Profile photo upload (Available when cloud storage is connected)"
              onClick={() => showToast('Photo upload will be enabled when cloud storage is connected.', 'info')}
              aria-label="Upload profile photo"
            >
              <Camera size={14} />
            </button>
          </div>

          <div className="profile-overview-info">
            <div className="profile-overview-title-row">
              <h2 className="profile-user-fullname">{profile.name}</h2>
              <span className="profile-status-pill profile-status-pill--active">
                <span className="profile-status-dot" />
                {profile.accountStatus}
              </span>
            </div>
            <p className="profile-user-email">{profile.email}</p>
            <div className="profile-overview-tags">
              <span className="profile-role-badge">
                <Shield size={12} />
                {profile.role}
              </span>
              <span className="profile-joined-text">Member since {profile.memberSince}</span>
            </div>
          </div>
        </div>

        <div className="profile-overview-actions">
          {!isEditingProfile ? (
            <button
              type="button"
              className="profile-btn-secondary"
              onClick={handleStartEdit}
            >
              <Edit3 size={15} />
              Edit Profile
            </button>
          ) : (
            <span className="profile-editing-badge">Editing Profile</span>
          )}
        </div>
      </section>

      {/* ── 2. Two-Column Layout: Personal Information & Account Security ── */}
      <div className="profile-grid-2col">
        {/* Personal Information */}
        <section className="profile-card" aria-label="Personal Information">
          <div className="profile-card-header">
            <div className="profile-card-header-left">
              <User size={18} className="profile-header-icon" />
              <h3>Personal Information</h3>
            </div>
            {profileSaveSuccess && (
              <span className="profile-saved-indicator">
                <Check size={14} />
                Saved
              </span>
            )}
          </div>

          {!isEditingProfile ? (
            /* Read-Only View Mode */
            <div className="profile-fields-list">
              <div className="profile-field-row">
                <span className="profile-field-label">Full Name</span>
                <span className="profile-field-value">{profile.name}</span>
              </div>
              <div className="profile-field-row">
                <span className="profile-field-label">Email</span>
                <span className="profile-field-value">{profile.email}</span>
              </div>
              <div className="profile-field-row">
                <span className="profile-field-label">Phone Number</span>
                <span className="profile-field-value">{profile.phone || 'Not provided'}</span>
              </div>
              <div className="profile-field-row">
                <span className="profile-field-label">Organization</span>
                <span className="profile-field-value">{profile.organization || 'Not provided'}</span>
              </div>
              <div className="profile-field-row">
                <span className="profile-field-label">Role</span>
                <span className="profile-field-value">{profile.role}</span>
              </div>
            </div>
          ) : (
            /* Interactive Edit Mode Form */
            <form onSubmit={handleSaveProfile} className="profile-edit-form">
              {formErrors.general && (
                <div className="profile-modal-error-banner" role="alert">
                  <AlertTriangle size={15} />
                  <span>{formErrors.general}</span>
                </div>
              )}

              <div className="profile-form-group">
                <label htmlFor="field-fullname">
                  Full Name <span className="profile-required-mark">*</span>
                </label>
                <div className="profile-input-with-icon">
                  <User size={15} className="profile-input-icon" />
                  <input
                    id="field-fullname"
                    type="text"
                    className={`profile-input ${formErrors.name ? 'profile-input--error' : ''}`}
                    value={editFormData.name}
                    onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                    disabled={isSavingProfile}
                  />
                </div>
                {formErrors.name && <p className="profile-field-error">{formErrors.name}</p>}
              </div>

              <div className="profile-form-group">
                <label htmlFor="field-email">
                  Email Address <span className="profile-required-mark">*</span>
                </label>
                <div className="profile-input-with-icon">
                  <Mail size={15} className="profile-input-icon" />
                  <input
                    id="field-email"
                    type="email"
                    className={`profile-input ${formErrors.email ? 'profile-input--error' : ''}`}
                    value={editFormData.email}
                    onChange={(e) => setEditFormData({ ...editFormData, email: e.target.value })}
                    disabled={isSavingProfile}
                  />
                </div>
                {formErrors.email && <p className="profile-field-error">{formErrors.email}</p>}
              </div>

              <div className="profile-form-group">
                <label htmlFor="field-phone">Phone Number</label>
                <div className="profile-input-with-icon">
                  <Phone size={15} className="profile-input-icon" />
                  <input
                    id="field-phone"
                    type="text"
                    className="profile-input"
                    value={editFormData.phone}
                    onChange={(e) => setEditFormData({ ...editFormData, phone: e.target.value })}
                    placeholder="+1 (555) 000-0000"
                    disabled={isSavingProfile}
                  />
                </div>
              </div>

              <div className="profile-form-group">
                <label htmlFor="field-organization">Organization</label>
                <div className="profile-input-with-icon">
                  <Building size={15} className="profile-input-icon" />
                  <input
                    id="field-organization"
                    type="text"
                    className="profile-input"
                    value={editFormData.organization}
                    onChange={(e) => setEditFormData({ ...editFormData, organization: e.target.value })}
                    placeholder="Company or Team name"
                    disabled={isSavingProfile}
                  />
                </div>
              </div>

              <div className="profile-edit-actions">
                <button
                  type="button"
                  className="profile-btn-secondary"
                  onClick={handleCancelEdit}
                  disabled={isSavingProfile}
                >
                  <X size={15} />
                  Cancel
                </button>
                <button
                  type="submit"
                  className="profile-btn-primary"
                  disabled={isSavingProfile}
                >
                  {isSavingProfile ? (
                    <>
                      <Loader2 size={15} className="profile-spinner" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save size={15} />
                      Save Changes
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </section>

        {/* Account & Security */}
        <section className="profile-card" aria-label="Account and Security">
          <div className="profile-card-header">
            <div className="profile-card-header-left">
              <ShieldCheck size={18} className="profile-header-icon" />
              <h3>Account & Security</h3>
            </div>
          </div>

          <div className="profile-security-items">
            {/* Email Verification */}
            <div className="profile-security-row">
              <div>
                <span className="profile-item-title">Email Verification</span>
                <p className="profile-item-desc">{profile.email}</p>
              </div>
              <div className="profile-security-action-group">
                {profile.emailVerified ? (
                  <span className="profile-verified-badge">
                    <CheckCircle2 size={14} />
                    Verified
                  </span>
                ) : (
                  <button
                    type="button"
                    className="profile-btn-ghost"
                    onClick={handleResendVerification}
                  >
                    Resend Verification
                  </button>
                )}
              </div>
            </div>

            {/* Password */}
            <div className="profile-security-row">
              <div>
                <span className="profile-item-title">Password</span>
                <p className="profile-item-desc">Last updated recently</p>
              </div>
              <button
                type="button"
                className="profile-btn-secondary"
                onClick={() => setIsChangePasswordOpen(true)}
              >
                <Lock size={14} />
                Change Password
              </button>
            </div>

            {/* Active Sessions */}
            <div className="profile-sessions-block">
              <div className="profile-sessions-header">
                <div>
                  <span className="profile-item-title">Active Sessions</span>
                  <p className="profile-item-desc">Devices currently logged into your account</p>
                </div>
                {sessions.length > 1 && (
                  <button
                    type="button"
                    className="profile-btn-ghost profile-btn-ghost--danger"
                    onClick={handleRevokeOtherSessions}
                  >
                    Sign Out Other Sessions
                  </button>
                )}
              </div>

              <div className="profile-sessions-list">
                {sessions.map((sess) => (
                  <div key={sess.id} className="profile-session-item">
                    <div className="profile-session-icon">
                      {sess.os.toLowerCase().includes('windows') || sess.os.toLowerCase().includes('mac') ? (
                        <Laptop size={16} />
                      ) : (
                        <Smartphone size={16} />
                      )}
                    </div>
                    <div className="profile-session-details">
                      <div className="profile-session-device">
                        <span>{sess.browser} · {sess.os}</span>
                        {sess.isCurrent && (
                          <span className="profile-current-session-pill">Current session</span>
                        )}
                      </div>
                      <span className="profile-session-time">
                        {sess.location} · {sess.lastActive}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Sign Out Button */}
            <div className="profile-signout-row">
              <button
                type="button"
                className="profile-btn-ghost profile-btn-ghost--danger"
                onClick={signOut}
              >
                <LogOut size={16} />
                Sign Out
              </button>
            </div>
          </div>
        </section>
      </div>

      {/* ── 3. Two-Column Layout: Preferences & AI Preferences ── */}
      <div className="profile-grid-2col">
        {/* Application Preferences */}
        <section className="profile-card" aria-label="Preferences">
          <div className="profile-card-header">
            <div className="profile-card-header-left">
              <Sliders size={18} className="profile-header-icon" />
              <h3>Preferences</h3>
            </div>
          </div>

          <div className="profile-pref-items">
            {/* Theme */}
            <div className="profile-pref-row">
              <div className="profile-pref-meta">
                <Moon size={16} className="profile-pref-icon" />
                <div>
                  <span className="profile-item-title">Theme</span>
                  <p className="profile-item-desc">Dark workspace theme (Standard)</p>
                </div>
              </div>
              <div className="profile-locked-pill">
                Dark (Default)
              </div>
            </div>

            {/* Language */}
            <div className="profile-pref-row">
              <div className="profile-pref-meta">
                <Globe size={16} className="profile-pref-icon" />
                <div>
                  <span className="profile-item-title">Language</span>
                  <p className="profile-item-desc">Interface display language</p>
                </div>
              </div>
              <select
                className="profile-select"
                value={preferences?.language || 'en'}
                onChange={() => showToast('English is the active platform language.', 'info')}
                aria-label="Language selection"
              >
                <option value="en">English (US)</option>
              </select>
            </div>

            {/* Date Format */}
            <div className="profile-pref-row">
              <div className="profile-pref-meta">
                <Calendar size={16} className="profile-pref-icon" />
                <div>
                  <span className="profile-item-title">Date Format</span>
                  <p className="profile-item-desc">Visual timestamp representation</p>
                </div>
              </div>
              <select
                className="profile-select"
                value={preferences?.dateFormat || 'DD/MM/YYYY'}
                onChange={(e) => handleUpdateDateFormat(e.target.value as DateFormatPreference)}
                aria-label="Date format selection"
              >
                <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                <option value="YYYY-MM-DD">YYYY-MM-DD</option>
              </select>
            </div>

            {/* Notifications */}
            <div className="profile-notifications-block">
              <div className="profile-notifications-header">
                <Bell size={16} className="profile-pref-icon" />
                <div>
                  <span className="profile-item-title">Notifications</span>
                  <p className="profile-item-desc">In-app notifications and trigger alerts</p>
                </div>
              </div>

              <div className="profile-toggles-list">
                <label className="profile-toggle-row">
                  <span>Analysis completed</span>
                  <input
                    type="checkbox"
                    className="profile-toggle-input"
                    checked={preferences?.notifications.analysisCompleted ?? true}
                    onChange={() => handleToggleNotification('analysisCompleted')}
                  />
                  <span className="profile-toggle-switch" aria-hidden="true" />
                </label>

                <label className="profile-toggle-row">
                  <span>Report generated</span>
                  <input
                    type="checkbox"
                    className="profile-toggle-input"
                    checked={preferences?.notifications.reportGenerated ?? true}
                    onChange={() => handleToggleNotification('reportGenerated')}
                  />
                  <span className="profile-toggle-switch" aria-hidden="true" />
                </label>

                <label className="profile-toggle-row">
                  <span>Dataset processing</span>
                  <input
                    type="checkbox"
                    className="profile-toggle-input"
                    checked={preferences?.notifications.datasetProcessing ?? true}
                    onChange={() => handleToggleNotification('datasetProcessing')}
                  />
                  <span className="profile-toggle-switch" aria-hidden="true" />
                </label>

                <label className="profile-toggle-row">
                  <span>System updates</span>
                  <input
                    type="checkbox"
                    className="profile-toggle-input"
                    checked={preferences?.notifications.systemUpdates ?? false}
                    onChange={() => handleToggleNotification('systemUpdates')}
                  />
                  <span className="profile-toggle-switch" aria-hidden="true" />
                </label>
              </div>
            </div>
          </div>
        </section>

        {/* AI Preferences */}
        <section className="profile-card" aria-label="AI Preferences">
          <div className="profile-card-header">
            <div className="profile-card-header-left">
              <Sparkles size={18} className="profile-header-icon" />
              <h3>AI Preferences</h3>
            </div>
          </div>

          <div className="profile-pref-items">
            {/* Default AI Model */}
            <div className="profile-pref-row">
              <div>
                <span className="profile-item-title">Default AI Model</span>
                <p className="profile-item-desc">Model used for analytical tasks</p>
              </div>
              <div className="profile-locked-pill">
                Automatic
              </div>
            </div>

            {/* Response Style */}
            <div className="profile-pref-row">
              <div>
                <span className="profile-item-title">Response Style</span>
                <p className="profile-item-desc">Verbosity of AI summaries</p>
              </div>
              <select
                className="profile-select"
                value={aiPreferences?.responseStyle || 'Detailed'}
                onChange={(e) => handleUpdateResponseStyle(e.target.value as AIResponseStyle)}
                aria-label="AI response style selection"
              >
                <option value="Concise">Concise</option>
                <option value="Balanced">Balanced</option>
                <option value="Detailed">Detailed</option>
              </select>
            </div>

            {/* Analysis Preferences */}
            <div className="profile-ai-options-block">
              <span className="profile-item-title">Analysis Preferences</span>
              <p className="profile-item-desc">Controls how insights and decision forecasts are generated</p>

              <div className="profile-checkbox-list">
                <label className="profile-checkbox-row">
                  <input
                    type="checkbox"
                    checked={aiPreferences?.explainEvidence ?? true}
                    onChange={() => handleToggleAIPreference('explainEvidence')}
                  />
                  <span>Explain insights with supporting evidence</span>
                </label>

                <label className="profile-checkbox-row">
                  <input
                    type="checkbox"
                    checked={aiPreferences?.showAssumptions ?? true}
                    onChange={() => handleToggleAIPreference('showAssumptions')}
                  />
                  <span>Show assumptions</span>
                </label>

                <label className="profile-checkbox-row">
                  <input
                    type="checkbox"
                    checked={aiPreferences?.explainAnomalies ?? true}
                    onChange={() => handleToggleAIPreference('explainAnomalies')}
                  />
                  <span>Explain detected anomalies</span>
                </label>

                <label className="profile-checkbox-row">
                  <input
                    type="checkbox"
                    checked={aiPreferences?.includeRecommendations ?? true}
                    onChange={() => handleToggleAIPreference('includeRecommendations')}
                  />
                  <span>Include recommendations</span>
                </label>

                <label className="profile-checkbox-row">
                  <input
                    type="checkbox"
                    checked={aiPreferences?.showConfidence ?? true}
                    onChange={() => handleToggleAIPreference('showConfidence')}
                  />
                  <span>Show confidence when available</span>
                </label>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* ── 4. Data & Privacy Section ── */}
      <section className="profile-card" aria-label="Data and Privacy">
        <div className="profile-card-header">
          <div className="profile-card-header-left">
            <Database size={18} className="profile-header-icon" />
            <h3>Data & Privacy</h3>
          </div>
        </div>

        <div className="profile-data-privacy-list">
          <div className="profile-data-row">
            <div>
              <span className="profile-item-title">Your Data</span>
              <p className="profile-item-desc">Manage your uploaded datasets and analysis history.</p>
            </div>
            <button
              type="button"
              className="profile-btn-secondary"
              onClick={() => navigate('/datasets')}
            >
              Manage Data
            </button>
          </div>

          <div className="profile-data-row">
            <div>
              <span className="profile-item-title">Download My Data</span>
              <p className="profile-item-desc">Request a copy of your account data and analytical history.</p>
            </div>
            <button
              type="button"
              className="profile-btn-secondary"
              onClick={handleRequestDataExport}
            >
              <Download size={14} />
              Request Export
            </button>
          </div>

          <div className="profile-data-row">
            <div>
              <span className="profile-item-title">Privacy</span>
              <p className="profile-item-desc">Review how your workspace datasets and accounts are governed.</p>
            </div>
            <button
              type="button"
              className="profile-btn-ghost"
              onClick={() => showToast('Privacy settings are managed under organization workspace policy.', 'info')}
            >
              View Privacy Settings
            </button>
          </div>
        </div>
      </section>

      {/* ── 5. Danger Zone ── */}
      <section className="profile-card profile-danger-card" aria-label="Danger Zone">
        <div className="profile-card-header">
          <div className="profile-card-header-left">
            <AlertTriangle size={18} className="profile-danger-icon" />
            <h3 className="profile-danger-title">Danger Zone</h3>
          </div>
        </div>

        <div className="profile-danger-content">
          <div>
            <span className="profile-item-title profile-danger-title">Delete Account</span>
            <p className="profile-item-desc">
              Permanently delete your account and associated data. This action is irreversible.
            </p>
          </div>
          <button
            type="button"
            className="profile-btn-danger"
            onClick={() => setIsDeleteAccountOpen(true)}
          >
            Delete Account
          </button>
        </div>
      </section>

      {/* Change Password Dialog Modal */}
      <ChangePasswordModal
        isOpen={isChangePasswordOpen}
        onClose={() => setIsChangePasswordOpen(false)}
      />

      {/* Delete Account Confirmation Dialog Modal */}
      <DeleteAccountModal
        isOpen={isDeleteAccountOpen}
        onClose={() => setIsDeleteAccountOpen(false)}
        onAccountDeleted={() => {
          signOut();
          navigate('/login');
        }}
      />
    </div>
  );
}
