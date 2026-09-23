import { Link, Outlet } from 'react-router-dom';

// ---------------------------------------------------------------------------
// AuthNavbar — floating pill navigation rendered on all auth pages.
// Defined inline here because it is only used within the auth layout
// and is simpler than the full LandingNavbar (no scroll indicator, no mobile
// drawer, no hash-link handling).
// ---------------------------------------------------------------------------

function AuthNavbar() {
  return (
    <nav className="av2-navbar" aria-label="Site navigation">
      <div className="av2-navbar-inner">
        {/* Brand */}
        <Link to="/" className="av2-brand" aria-label="AI Data Analyst – home">
          <span className="av2-brand-dot" aria-hidden="true" />
          <span className="av2-brand-text">AI Data Analyst</span>
        </Link>

        {/* Center links */}
        <div className="av2-nav-links" role="list">
          <Link
            to="/#hero"
            className="av2-nav-link"
            role="listitem"
            aria-label="Features"
          >
            Features
          </Link>
          <Link
            to="/datasets"
            className="av2-nav-link"
            role="listitem"
            aria-label="Work"
          >
            Work
          </Link>
        </div>

        {/* Right actions */}
        <div className="av2-nav-actions">
          <Link to="/login" className="av2-nav-login" aria-label="Log in">
            Login
          </Link>
          <Link to="/signup" className="av2-nav-signup" aria-label="Sign up">
            Sign Up
          </Link>
        </div>
      </div>
    </nav>
  );
}

// ---------------------------------------------------------------------------
// AuthLayout
// ---------------------------------------------------------------------------

export default function AuthLayout() {
  return (
    <div className="av2-layout">
      {/* ── Layer 5: Navbar ── */}
      <AuthNavbar />

      {/* ── Layer 5: Centered auth content (Login / Signup) ── */}
      <main className="av2-content">
        <Outlet />
      </main>
    </div>
  );
}
