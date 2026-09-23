import { type FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validateEmail(email: string): string | null {
  if (!email.trim()) return 'Email is required.';
  if (!EMAIL_REGEX.test(email)) return 'Enter a valid email address.';
  return null;
}

// ---------------------------------------------------------------------------
// Motion config
// ---------------------------------------------------------------------------

const TRANSITION = { duration: 0.30, ease: [0.22, 1, 0.36, 1] as const };

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  exit:    { opacity: 0, y: -8 },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

type ForgotState = 'idle' | 'submitting' | 'sent';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [emailError, setEmailError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);
  const [state, setState] = useState<ForgotState>('idle');
  const [submitError, setSubmitError] = useState<string | null>(null);

  function handleBlur() {
    setTouched(true);
    setEmailError(validateEmail(email));
  }

  // -------------------------------------------------------------------------
  // Submit
  // BACKEND DEPENDENCY: authService.forgotPassword() will be called here
  // once the backend endpoint is implemented.
  // -------------------------------------------------------------------------
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    setTouched(true);

    const err = validateEmail(email);
    setEmailError(err);
    if (err) return;
    if (state === 'submitting') return;

    setState('submitting');
    try {
      // Real HTTP call via authService.forgotPassword({ email }) goes here
      // once backend /api/auth/forgot-password is implemented.
      await new Promise<void>((_, reject) => {
        setTimeout(() => {
          reject(new Error('Backend authentication is not yet available.'));
        }, 600);
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'An unexpected error occurred.';
      setSubmitError(message);
      setState('idle');
    }
  }

  return (
    <div className="av2-card">
      {/* Heading */}
      <motion.h1
        className="av2-heading"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...TRANSITION, delay: 0.05 }}
      >
        Reset Password
      </motion.h1>
      <motion.p
        className="av2-subtext"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...TRANSITION, delay: 0.12 }}
      >
        Enter your email and we&apos;ll send a reset link
      </motion.p>

      {/* Animated form / success state */}
      <AnimatePresence mode="wait" initial={false}>
        {state === 'sent' ? (
          <motion.div
            key="sent"
            className="av2-form"
            variants={fadeUp}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={TRANSITION}
          >
            <p className="av2-success-banner" role="status">
              If an account exists for <strong>{email}</strong>, a reset link has been sent.
              Check your inbox.
            </p>
          </motion.div>
        ) : (
          <motion.form
            key="form"
            onSubmit={handleSubmit}
            noValidate
            className="av2-form"
            variants={fadeUp}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={TRANSITION}
            aria-label="Password reset form"
          >
            {/* Submit error */}
            {submitError && (
              <p className="av2-error-banner" role="alert">
                {submitError}
              </p>
            )}

            {/* Email input */}
            <div>
              <div className="av2-input-row">
                <label htmlFor="forgot-email" className="sr-only">
                  Email address
                </label>
                <input
                  id="forgot-email"
                  type="email"
                  autoComplete="email"
                  required
                  className={`av2-input${touched && emailError ? ' av2-input--error' : ''}`}
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (touched) setEmailError(validateEmail(e.target.value));
                  }}
                  onBlur={handleBlur}
                  aria-invalid={touched && !!emailError}
                  aria-describedby={
                    touched && emailError ? 'forgot-email-error' : undefined
                  }
                  disabled={state === 'submitting'}
                />
                <button
                  type="submit"
                  className="av2-arrow-btn"
                  aria-label="Send reset link"
                  disabled={state === 'submitting'}
                >
                  {state === 'submitting' ? (
                    <span className="av2-spinner" aria-hidden="true" />
                  ) : (
                    '→'
                  )}
                </button>
              </div>
              {touched && emailError && (
                <p id="forgot-email-error" className="av2-field-error" role="alert">
                  {emailError}
                </p>
              )}
            </div>

            {/* Submit button */}
            <button
              type="submit"
              className="av2-submit-btn"
              disabled={state === 'submitting'}
            >
              {state === 'submitting' && (
                <span className="av2-spinner" aria-hidden="true" />
              )}
              {state === 'submitting' ? 'Sending…' : 'Send reset link'}
            </button>
          </motion.form>
        )}
      </AnimatePresence>

      {/* Back to login */}
      <motion.p
        className="av2-footer"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ ...TRANSITION, delay: 0.28 }}
      >
        <Link to="/login" className="av2-link av2-link--sm">
          ← Back to login
        </Link>
      </motion.p>
    </div>
  );
}
