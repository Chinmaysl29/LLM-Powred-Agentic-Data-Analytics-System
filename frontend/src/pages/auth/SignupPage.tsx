import { type FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { useAuth } from '../../context/AuthContext';

// ---------------------------------------------------------------------------
// Validation helpers
// ---------------------------------------------------------------------------

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 8;

function validateEmail(email: string): string | null {
  if (!email.trim()) return 'Email is required.';
  if (!EMAIL_REGEX.test(email)) return 'Enter a valid email address.';
  return null;
}

function validateFullName(name: string): string | null {
  if (!name.trim()) return 'Full name is required.';
  if (name.trim().length < 2) return 'Full name must be at least 2 characters.';
  return null;
}

function validatePassword(password: string): string | null {
  if (!password) return 'Password is required.';
  if (password.length < MIN_PASSWORD_LENGTH)
    return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  return null;
}

function validateConfirmPassword(
  password: string,
  confirm: string,
): string | null {
  if (!confirm) return 'Please confirm your password.';
  if (confirm !== password) return 'Passwords do not match.';
  return null;
}

// ---------------------------------------------------------------------------
// Motion config
// ---------------------------------------------------------------------------

const TRANSITION = { duration: 0.32, ease: [0.22, 1, 0.36, 1] as const };

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SignupPage() {
  const navigate = useNavigate();
  const { devSignIn } = useAuth();

  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [errors, setErrors] = useState<{
    email?: string;
    fullName?: string;
    password?: string;
    confirmPassword?: string;
  }>({});
  const [touched, setTouched] = useState<{
    email?: boolean;
    fullName?: boolean;
    password?: boolean;
    confirmPassword?: boolean;
  }>({});

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Blur handlers
  // -------------------------------------------------------------------------
  function handleBlur(field: 'email' | 'fullName' | 'password' | 'confirmPassword') {
    setTouched((prev) => ({ ...prev, [field]: true }));
    setErrors((prev) => ({
      ...prev,
      email: field === 'email' ? (validateEmail(email) ?? undefined) : prev.email,
      fullName:
        field === 'fullName'
          ? (validateFullName(fullName) ?? undefined)
          : prev.fullName,
      password:
        field === 'password'
          ? (validatePassword(password) ?? undefined)
          : prev.password,
      confirmPassword:
        field === 'confirmPassword'
          ? (validateConfirmPassword(password, confirmPassword) ?? undefined)
          : prev.confirmPassword,
    }));
  }

  // -------------------------------------------------------------------------
  // Full validation on submit
  // -------------------------------------------------------------------------
  function validateForm(): boolean {
    const e = validateEmail(email);
    const n = validateFullName(fullName);
    const p = validatePassword(password);
    const c = validateConfirmPassword(password, confirmPassword);
    setErrors({
      email: e ?? undefined,
      fullName: n ?? undefined,
      password: p ?? undefined,
      confirmPassword: c ?? undefined,
    });
    setTouched({ email: true, fullName: true, password: true, confirmPassword: true });
    return !e && !n && !p && !c;
  }

  // -------------------------------------------------------------------------
  // Submit
  // DEV-MODE: Uses devSignIn() to advance past the auth boundary.
  //
  // BACKEND DEPENDENCY: Replace devSignIn() + navigate with:
  //   await authService.signup({ email, password, full_name: fullName });
  //   navigate('/dashboard');
  // -------------------------------------------------------------------------
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitError(null);

    if (!validateForm()) return;
    if (isSubmitting) return;

    setIsSubmitting(true);
    try {
      // DEV-MODE AUTH BOUNDARY
      // Simulates async then advances to workspace.
      // Replace with authService.signup() when backend is ready.
      await new Promise<void>((resolve) => setTimeout(resolve, 400));
      devSignIn();
      navigate('/dashboard');
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'An unexpected error occurred.';
      setSubmitError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  return (
    <div className="av2-card">
      {/* Heading */}
      <motion.h1
        className="av2-heading"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...TRANSITION, delay: 0.05 }}
      >
        Welcome
      </motion.h1>
      <motion.p
        className="av2-subtext"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...TRANSITION, delay: 0.12 }}
      >
        Create your AI Data Analyst account
      </motion.p>

      {/* Error banner */}
      {submitError && (
        <motion.p
          className="av2-error-banner"
          role="alert"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={TRANSITION}
        >
          {submitError}
        </motion.p>
      )}

      {/* Signup form */}
      <motion.form
        onSubmit={handleSubmit}
        noValidate
        className="av2-form"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...TRANSITION, delay: 0.18 }}
        aria-label="Create account form"
      >
        {/* Email */}
        <div>
          <div className="av2-input-row">
            <label htmlFor="signup-email" className="sr-only">
              Email address
            </label>
            <input
              id="signup-email"
              type="email"
              autoComplete="email"
              required
              className={`av2-input${touched.email && errors.email ? ' av2-input--error' : ''}`}
              placeholder="Email address"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (touched.email)
                  setErrors((prev) => ({
                    ...prev,
                    email: validateEmail(e.target.value) ?? undefined,
                  }));
              }}
              onBlur={() => handleBlur('email')}
              aria-invalid={touched.email && !!errors.email}
              aria-describedby={
                touched.email && errors.email ? 'signup-email-error' : undefined
              }
              disabled={isSubmitting}
            />
          </div>
          {touched.email && errors.email && (
            <p id="signup-email-error" className="av2-field-error" role="alert">
              {errors.email}
            </p>
          )}
        </div>

        {/* Full name */}
        <div>
          <div className="av2-input-row">
            <label htmlFor="signup-name" className="sr-only">
              Full name
            </label>
            <input
              id="signup-name"
              type="text"
              autoComplete="name"
              required
              className={`av2-input${touched.fullName && errors.fullName ? ' av2-input--error' : ''}`}
              placeholder="Full name"
              value={fullName}
              onChange={(e) => {
                setFullName(e.target.value);
                if (touched.fullName)
                  setErrors((prev) => ({
                    ...prev,
                    fullName: validateFullName(e.target.value) ?? undefined,
                  }));
              }}
              onBlur={() => handleBlur('fullName')}
              aria-invalid={touched.fullName && !!errors.fullName}
              aria-describedby={
                touched.fullName && errors.fullName ? 'signup-name-error' : undefined
              }
              disabled={isSubmitting}
            />
          </div>
          {touched.fullName && errors.fullName && (
            <p id="signup-name-error" className="av2-field-error" role="alert">
              {errors.fullName}
            </p>
          )}
        </div>

        {/* Password */}
        <div>
          <div className="av2-input-row">
            <label htmlFor="signup-password" className="sr-only">
              Password
            </label>
            <input
              id="signup-password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              required
              className={`av2-input${touched.password && errors.password ? ' av2-input--error' : ''}`}
              placeholder="Password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (touched.password)
                  setErrors((prev) => ({
                    ...prev,
                    password: validatePassword(e.target.value) ?? undefined,
                  }));
              }}
              onBlur={() => handleBlur('password')}
              aria-invalid={touched.password && !!errors.password}
              aria-describedby={
                touched.password && errors.password
                  ? 'signup-password-error'
                  : undefined
              }
              disabled={isSubmitting}
            />
            <button
              type="button"
              className="av2-pw-toggle"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </div>
          {touched.password && errors.password && (
            <p id="signup-password-error" className="av2-field-error" role="alert">
              {errors.password}
            </p>
          )}
        </div>

        {/* Confirm password */}
        <div>
          <div className="av2-input-row">
            <label htmlFor="signup-confirm" className="sr-only">
              Confirm password
            </label>
            <input
              id="signup-confirm"
              type={showConfirm ? 'text' : 'password'}
              autoComplete="new-password"
              required
              className={`av2-input${touched.confirmPassword && errors.confirmPassword ? ' av2-input--error' : ''}`}
              placeholder="Confirm password"
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value);
                if (touched.confirmPassword)
                  setErrors((prev) => ({
                    ...prev,
                    confirmPassword:
                      validateConfirmPassword(password, e.target.value) ?? undefined,
                  }));
              }}
              onBlur={() => handleBlur('confirmPassword')}
              aria-invalid={touched.confirmPassword && !!errors.confirmPassword}
              aria-describedby={
                touched.confirmPassword && errors.confirmPassword
                  ? 'signup-confirm-error'
                  : undefined
              }
              disabled={isSubmitting}
            />
            <button
              type="button"
              className="av2-pw-toggle"
              onClick={() => setShowConfirm((v) => !v)}
              aria-label={showConfirm ? 'Hide confirm password' : 'Show confirm password'}
            >
              {showConfirm ? 'Hide' : 'Show'}
            </button>
          </div>
          {touched.confirmPassword && errors.confirmPassword && (
            <p id="signup-confirm-error" className="av2-field-error" role="alert">
              {errors.confirmPassword}
            </p>
          )}
        </div>

        {/* Submit */}
        <button
          type="submit"
          className="av2-submit-btn"
          disabled={isSubmitting}
        >
          {isSubmitting && (
            <span className="av2-spinner" aria-hidden="true" />
          )}
          {isSubmitting ? 'Creating account…' : 'Create account'}
        </button>
      </motion.form>

      {/* Login prompt */}
      <motion.p
        className="av2-footer"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ ...TRANSITION, delay: 0.3 }}
      >
        Already have an account?{' '}
        <Link to="/login" className="av2-link">
          Login
        </Link>
      </motion.p>
    </div>
  );
}
