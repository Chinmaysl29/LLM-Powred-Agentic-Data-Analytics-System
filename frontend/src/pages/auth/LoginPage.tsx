import { type FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'motion/react';
import { useAuth } from '../../context/AuthContext';

// ---------------------------------------------------------------------------
// Validation helpers (unchanged from original)
// ---------------------------------------------------------------------------

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 8;

function validateEmail(email: string): string | null {
  if (!email.trim()) return 'Email is required.';
  if (!EMAIL_REGEX.test(email)) return 'Enter a valid email address.';
  return null;
}

function validatePassword(password: string): string | null {
  if (!password) return 'Password is required.';
  if (password.length < MIN_PASSWORD_LENGTH)
    return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  return null;
}

// ---------------------------------------------------------------------------
// Motion variants
// ---------------------------------------------------------------------------

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  exit:    { opacity: 0, y: -10 },
};

const TRANSITION = { duration: 0.28, ease: [0.22, 1, 0.36, 1] as const };

// ---------------------------------------------------------------------------
// Google "G" SVG icon (monochrome, fits dark theme)
// ---------------------------------------------------------------------------
function GoogleIcon() {
  return (
    <svg
      aria-hidden="true"
      className="av2-google-icon"
      viewBox="0 0 18 18"
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
    >
      <path
        d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"
        fill="rgba(255,255,255,0.9)"
      />
      <path
        d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"
        fill="rgba(255,255,255,0.75)"
      />
      <path
        d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"
        fill="rgba(255,255,255,0.6)"
      />
      <path
        d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"
        fill="rgba(255,255,255,0.85)"
      />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

type Step = 'email' | 'password';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

  // Two-step flow state
  const [step, setStep] = useState<Step>('email');

  // Form fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Validation
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [touched, setTouched] = useState<{ email?: boolean; password?: boolean }>({});

  // Submission state

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Step 1 — validate email and proceed
  // -------------------------------------------------------------------------
  function handleEmailContinue(e?: FormEvent) {
    e?.preventDefault();
    const emailError = validateEmail(email);
    setErrors({ email: emailError ?? undefined });
    setTouched({ email: true });
    if (!emailError) {
      setSubmitError(null);
      setStep('password');
    }
  }

  // -------------------------------------------------------------------------
  // Step 2 — validate password on blur
  // -------------------------------------------------------------------------
  function handlePasswordBlur() {
    setTouched((prev) => ({ ...prev, password: true }));
    setErrors((prev) => ({
      ...prev,
      password: validatePassword(password) ?? undefined,
    }));
  }

  // -------------------------------------------------------------------------
  // Step 2 — submit
  // -------------------------------------------------------------------------
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitError(null);

    const passwordError = validatePassword(password);
    if (passwordError) {
      setErrors((prev) => ({ ...prev, password: passwordError }));
      setTouched((prev) => ({ ...prev, password: true }));
      return;
    }
    if (isSubmitting) return;

    setIsSubmitting(true);
    try {
      await login({ email, password });
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
      {/* ------------------------------------------------------------------ */}
      {/* Heading (always visible)                                             */}
      {/* ------------------------------------------------------------------ */}
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
        Sign in to continue to AI Data Analyst
      </motion.p>

      {/* ------------------------------------------------------------------ */}
      {/* Step-based content (animates between email / password steps)         */}
      {/* ------------------------------------------------------------------ */}
      <AnimatePresence mode="wait" initial={false}>
        {step === 'email' ? (
          <motion.div
            key="email-step"
            className="av2-form"
            variants={fadeUp}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={TRANSITION}
          >
            {/* Google Sign-In */}
            <button
              type="button"
              className="av2-google-btn"
              disabled
              aria-label="Sign in with Google (coming soon)"
              title="Google sign-in will be available once backend authentication is configured"
            >
              <GoogleIcon />
              Sign in with Google
            </button>

            {/* Divider */}
            <div className="av2-divider" aria-hidden="true">or</div>

            {/* Email input */}
            <form onSubmit={handleEmailContinue} noValidate>
              <div className="av2-input-row">
                <label htmlFor="login-email" className="sr-only">
                  Email address
                </label>
                <input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  required
                  className={`av2-input${touched.email && errors.email ? ' av2-input--error' : ''}`}
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (touched.email) {
                      setErrors((prev) => ({
                        ...prev,
                        email: validateEmail(e.target.value) ?? undefined,
                      }));
                    }
                  }}
                  onBlur={() => {
                    setTouched((prev) => ({ ...prev, email: true }));
                    setErrors((prev) => ({
                      ...prev,
                      email: validateEmail(email) ?? undefined,
                    }));
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleEmailContinue();
                  }}
                  aria-invalid={touched.email && !!errors.email}
                  aria-describedby={
                    touched.email && errors.email ? 'login-email-error' : undefined
                  }
                />
                <button
                  type="submit"
                  className="av2-arrow-btn"
                  aria-label="Continue with email"
                >
                  →
                </button>
              </div>
              {touched.email && errors.email && (
                <p id="login-email-error" className="av2-field-error" role="alert">
                  {errors.email}
                </p>
              )}
            </form>
          </motion.div>
        ) : (
          <motion.div
            key="password-step"
            className="av2-form"
            variants={fadeUp}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={TRANSITION}
          >
            {/* Back button + email chip */}
            <button
              type="button"
              className="av2-back-btn"
              onClick={() => {
                setStep('email');
                setErrors({});
                setTouched({});
                setSubmitError(null);
              }}
              aria-label="Go back to email step"
            >
              ← Back
            </button>
            <span className="av2-email-chip" aria-label={`Signing in as ${email}`}>
              {email}
            </span>

            {/* Submit error */}
            {submitError && (
              <p className="av2-error-banner" role="alert">
                {submitError}
              </p>
            )}

            {/* Password form */}
            <form onSubmit={handleSubmit} noValidate className="av2-form">
              <div className="av2-input-row">
                <label htmlFor="login-password" className="sr-only">
                  Password
                </label>
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  autoFocus
                  className={`av2-input${touched.password && errors.password ? ' av2-input--error' : ''}`}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (touched.password) {
                      setErrors((prev) => ({
                        ...prev,
                        password: validatePassword(e.target.value) ?? undefined,
                      }));
                    }
                  }}
                  onBlur={handlePasswordBlur}
                  aria-invalid={touched.password && !!errors.password}
                  aria-describedby={
                    touched.password && errors.password
                      ? 'login-password-error'
                      : undefined
                  }
                  disabled={isSubmitting}
                />
                <button
                  type="button"
                  className="av2-pw-toggle"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  tabIndex={0}
                >
                  {showPassword ? 'Hide' : 'Show'}
                </button>
                <button
                  type="submit"
                  className="av2-arrow-btn"
                  aria-label="Sign in"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <span className="av2-spinner" aria-hidden="true" />
                  ) : (
                    '→'
                  )}
                </button>
              </div>
              {touched.password && errors.password && (
                <p id="login-password-error" className="av2-field-error" role="alert">
                  {errors.password}
                </p>
              )}

              {/* Forgot password */}
              <div className="av2-forgot-row">
                <Link
                  to="/forgot-password"
                  className="av2-link av2-link--sm"
                  aria-label="Forgot your password?"
                >
                  Forgot password?
                </Link>
              </div>

              {/* Sign in button */}
              <button
                type="submit"
                className="av2-submit-btn"
                disabled={isSubmitting}
              >
                {isSubmitting && (
                  <span className="av2-spinner" aria-hidden="true" />
                )}
                {isSubmitting ? 'Signing in…' : 'Sign in'}
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ------------------------------------------------------------------ */}
      {/* Signup prompt (always visible)                                        */}
      {/* ------------------------------------------------------------------ */}
      <motion.p
        className="av2-footer"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ ...TRANSITION, delay: 0.25 }}
      >
        Don&apos;t have an account?{' '}
        <Link to="/signup" className="av2-link">
          Sign Up
        </Link>
      </motion.p>
    </div>
  );
}
