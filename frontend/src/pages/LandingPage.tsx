import { Link } from 'react-router-dom';
import LandingNavbar from '../components/LandingNavbar';
import FeaturesSection from '../components/FeaturesSection';

// ---------------------------------------------------------------------------
// Landing Page
// ---------------------------------------------------------------------------

export default function LandingPage() {
  return (
    <div className="landing-page">
      {/* Skip to main content for keyboard users */}
      <a href="#hero" className="landing-skip-link">
        Skip to main content
      </a>

      {/* ------------------------------------------------------------------ */}
      {/* Background layers — aria-hidden, purely decorative                  */}
      {/* ------------------------------------------------------------------ */}

      {/* Layer 1: Subtle architectural grid */}
      <div className="lp-grid" aria-hidden="true" />

      {/* Layer 2: Grayscale atmospheric gradient layers */}
      <div className="lp-atmosphere" aria-hidden="true" />

      {/* Layer 3: Central soft volumetric glow above ellipse */}
      <div className="lp-glow" aria-hidden="true" />

      {/* Layer 4: Giant glowing dark ellipse */}
      <div className="lp-sphere" aria-hidden="true" />

      {/* Floating pill navbar */}
      <LandingNavbar />

      {/* ------------------------------------------------------------------ */}
      {/* Hero section                                                         */}
      {/* ------------------------------------------------------------------ */}
      <main id="hero" className="landing-hero" tabIndex={-1}>
        {/* Eyebrow tag */}
        <div className="landing-eyebrow landing-anim landing-anim--0">
          <span className="landing-eyebrow-dot" aria-hidden="true" />
          Agentic Analytics Platform
        </div>

        {/* Heading */}
        <h1 className="landing-heading landing-anim landing-anim--1">
          Turn Data Into{' '}
          <span className="landing-heading-accent">Decisions</span>
          {' '}with AI
        </h1>

        {/* Subheading */}
        <p className="landing-subheading landing-anim landing-anim--2">
          An autonomous agentic analytics platform that lets you analyze your
          data using natural language, uncovers insights, generates interactive
          visualizations, and delivers actionable intelligence.
        </p>

        {/* CTA */}
        <div className="landing-cta-row landing-anim landing-anim--3">
          <Link to="/datasets" className="landing-cta-primary">
            Get Started
          </Link>
        </div>
      </main>

      {/* ------------------------------------------------------------------ */}
      {/* Features section — scrolls into view naturally below hero           */}
      {/* ------------------------------------------------------------------ */}
      <FeaturesSection />
    </div>
  );
}
