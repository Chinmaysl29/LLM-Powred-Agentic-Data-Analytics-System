import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { NavLink, Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { motion, useMotionValue, useSpring, useTransform } from 'motion/react';
import type { MotionValue } from 'motion/react';
import {
  LayoutDashboard,
  Database,
  MessageSquare,
  BarChart3,
  Lightbulb,
  FileText,
  User,
  Settings,
  Menu,
  X,
  LogOut,
  Plus,
  Sparkles,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

// ---------------------------------------------------------------------------
// Storage key for sidebar preference persistence
// ---------------------------------------------------------------------------
const SIDEBAR_STORAGE_KEY = 'ai_data_analyst_sidebar_collapsed';

// ---------------------------------------------------------------------------
// Navigation structure (Single source of truth)
// ---------------------------------------------------------------------------

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  subItems?: { to: string; label: string }[];
}

interface NavGroup {
  label?: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    items: [
      { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/datasets',  label: 'Datasets',  icon: Database },
    ],
  },
  {
    label: 'ANALYTICS',
    items: [
      { to: '/analysis',        label: 'AI Analysis',     icon: MessageSquare },
      { to: '/visualizations',  label: 'Visualizations',  icon: BarChart3 },
      { to: '/insights',        label: 'Insights',        icon: Lightbulb },
    ],
  },
  {
    label: 'OUTPUT',
    items: [
      { 
        to: '/reports', 
        label: 'Reports', 
        icon: FileText,
        subItems: [
          { to: '/reports', label: 'Generated Reports' },
          { to: '/reports/create', label: 'Create Report' },
        ],
      },
    ],
  },
  {
    label: 'ACCOUNT',
    items: [
      { to: '/profile',  label: 'Profile',  icon: User },
      { to: '/settings', label: 'Settings', icon: Settings },
    ],
  },
];

// ---------------------------------------------------------------------------
// Page title map
// ---------------------------------------------------------------------------

const PAGE_TITLES: Record<string, string> = {
  '/dashboard':       'Dashboard',
  '/datasets':        'Datasets',
  '/datasets/upload': 'Upload Dataset',
  '/analysis':        'AI Analysis',
  '/visualizations':  'Visualizations',
  '/insights':        'Insights',
  '/insights/what-if':'What-If Scenario Simulation',
  '/reports':         'Reports',
  '/reports/create':  'Create Report',
  '/profile':         'Profile',
  '/settings':        'Settings',
};

function usePageTitle(): string {
  const { pathname } = useLocation();
  if (pathname.startsWith('/datasets/') && pathname !== '/datasets/upload') {
    return 'Dataset Details';
  }
  if (pathname.startsWith('/reports/') && pathname !== '/reports/create') {
    if (pathname.endsWith('/edit')) {
      return 'Report Builder';
    }
    return 'Generated Report';
  }
  return PAGE_TITLES[pathname] ?? 'AI Data Analyst';
}

// ---------------------------------------------------------------------------
// DockIcon — dock-style magnification on cursor proximity.
// Tooltip is a plain span rendered only when sidebar is collapsed;
// its visibility is controlled entirely by CSS (no JS state needed).
// ---------------------------------------------------------------------------

const DOCK_DISTANCE = 86;
const DOCK_MAX_SCALE = 1.12;

interface DockIconProps {
  children: ReactNode;
  isActive?: boolean;
  isCollapsed: boolean;
  label: string;
  mouseY: MotionValue<number>;
}

function DockIcon({ children, isActive = false, isCollapsed, label, mouseY }: DockIconProps) {
  const itemRef = useRef<HTMLSpanElement>(null);

  const scale = useTransform(mouseY, (latestY) => {
    if (!isCollapsed || !itemRef.current) {
      return 1;
    }
    const rect = itemRef.current.getBoundingClientRect();
    const distance = Math.abs(latestY - (rect.top + rect.height / 2));
    if (Number.isNaN(distance) || distance > DOCK_DISTANCE) {
      return isActive ? 1.07 : 1;
    }
    const influence = 1 - distance / DOCK_DISTANCE;
    return (isActive ? 1.05 : 1) + influence * (DOCK_MAX_SCALE - 1);
  });

  const smoothScale = useSpring(scale, { stiffness: 360, damping: 28, mass: 0.45 });

  return (
    <>
      <motion.span
        ref={itemRef}
        className="ws-dock-icon"
        style={{ scale: smoothScale }}
        aria-hidden="true"
      >
        {children}
      </motion.span>
      {/* Tooltip: only rendered in DOM when collapsed; shown/hidden via CSS hover rules */}
      {isCollapsed && (
        <span className="ws-tooltip" role="tooltip">
          {label}
        </span>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Sidebar Component
// ---------------------------------------------------------------------------

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

function Sidebar({ isCollapsed, onToggleCollapse, mobileOpen, onMobileClose }: SidebarProps) {
  const { signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const mouseY = useMotionValue<number>(Number.POSITIVE_INFINITY);

  // Show labels when expanded OR when mobile drawer is open.
  // This ensures the mobile drawer always shows full labels even if the
  // desktop sidebar was collapsed.
  const showLabels = !isCollapsed || mobileOpen;
  // Only apply dock magnification when truly collapsed (not in mobile drawer mode).
  const effectivelyCollapsed = isCollapsed && !mobileOpen;

  function handleSignOut() {
    signOut();
    navigate('/login');
  }

  return (
    <>
      {/* Mobile backdrop */}
      <div
        className={`ws-sidebar-overlay${mobileOpen ? ' ws-sidebar-overlay--visible' : ''}`}
        aria-hidden="true"
        onClick={onMobileClose}
      />

      <aside
        className={`ws-sidebar ${isCollapsed ? 'ws-sidebar--collapsed' : 'ws-sidebar--expanded'} ${
          mobileOpen ? 'ws-sidebar--open' : ''
        }`}
        aria-label="Main navigation"
        onMouseMove={(event) => mouseY.set(event.clientY)}
        onMouseLeave={() => mouseY.set(Number.POSITIVE_INFINITY)}
      >
        {/* ── Brand header ── */}
        <div className="ws-sidebar-brand">
          <div className="ws-sidebar-brand-left">
            <div className="ws-sidebar-brand-dot" aria-hidden="true">
              <Sparkles size={14} color="rgba(255,255,255,0.85)" />
            </div>
            {/* Brand text: CSS hides it when collapsed */}
            <span className="ws-sidebar-brand-text">AI Data Analyst</span>
          </div>

          {/* Desktop collapse/expand toggle — ONE control for both states */}
          <button
            type="button"
            className="ws-collapse-toggle"
            onClick={onToggleCollapse}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-expanded={!isCollapsed}
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? (
              <PanelLeftOpen size={16} aria-hidden="true" />
            ) : (
              <PanelLeftClose size={16} aria-hidden="true" />
            )}
            {/* CSS tooltip for the toggle button when collapsed */}
            {isCollapsed && (
              <span className="ws-tooltip" role="tooltip">Expand sidebar</span>
            )}
          </button>

          {/* Mobile drawer close button */}
          <button
            type="button"
            className="ws-sidebar-mobile-close"
            onClick={onMobileClose}
            aria-label="Close navigation"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        {/* ── New Analysis CTA ── */}
        <div className="ws-new-analysis-wrapper">
          <Link
            to="/analysis"
            className="ws-new-analysis"
            onClick={onMobileClose}
            aria-label="New Analysis"
          >
            <DockIcon isCollapsed={effectivelyCollapsed} label="New Analysis" mouseY={mouseY}>
              <Plus size={20} strokeWidth={1.9} />
            </DockIcon>
            {/* Label rendered when sidebar is expanded OR mobile drawer is open */}
            {showLabels && (
              <span className="ws-new-analysis-label">New Analysis</span>
            )}
          </Link>
        </div>

        {/* ── Navigation groups — single source of truth: NAV_GROUPS ── */}
        <nav className="ws-sidebar-nav" aria-label="Main">
          {NAV_GROUPS.map((group, gi) => (
            <div key={gi} className="ws-nav-group">
              {gi > 0 && <div className="ws-nav-divider" aria-hidden="true" />}
              {/* Section label: not rendered when collapsed (unless mobile drawer is open) */}
              {group.label && showLabels && (
                <div className="ws-nav-section-label" aria-hidden="true">
                  {group.label}
                </div>
              )}
              {group.items.map((item) => {
                const { to, label, icon: Icon, subItems } = item;
                const isGroupActive = location.pathname.startsWith(to);
                return (
                  <div key={to} className="ws-nav-item-wrap">
                    <NavLink
                      to={to}
                      end={to === '/dashboard' || Boolean(subItems)}
                      className={({ isActive }) => `ws-nav-link${isActive || (Boolean(subItems) && isGroupActive) ? ' ws-nav-link--active' : ''}`}
                      aria-label={label}
                      onClick={onMobileClose}
                    >
                      {({ isActive }) => (
                        <>
                          <DockIcon
                            isActive={isActive || (Boolean(subItems) && isGroupActive)}
                            isCollapsed={effectivelyCollapsed}
                            label={label}
                            mouseY={mouseY}
                          >
                            <Icon size={20} strokeWidth={1.9} />
                          </DockIcon>
                          {showLabels && (
                            <span className="ws-nav-label">{label}</span>
                          )}
                        </>
                      )}
                    </NavLink>
                    {showLabels && subItems && isGroupActive && (
                      <div className="ws-nav-subitems">
                        {subItems.map((sub) => (
                          <NavLink
                            key={sub.to}
                            to={sub.to}
                            end={sub.to === '/reports'}
                            className={({ isActive }) => `ws-nav-sublink${isActive ? ' ws-nav-sublink--active' : ''}`}
                            onClick={onMobileClose}
                          >
                            <span className="ws-nav-sublink-dot" aria-hidden="true" />
                            <span>{sub.label}</span>
                          </NavLink>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </nav>

        {/* ── Footer: Sign out ── */}
        <div className="ws-sidebar-footer">
          <button
            type="button"
            className="ws-nav-link ws-signout-btn"
            onClick={handleSignOut}
            aria-label="Sign out"
          >
            <DockIcon isCollapsed={effectivelyCollapsed} label="Sign out" mouseY={mouseY}>
              <LogOut size={20} strokeWidth={1.9} />
            </DockIcon>
            {showLabels && (
              <span className="ws-nav-label">Sign out</span>
            )}
          </button>
        </div>
      </aside>
    </>
  );
}

// ---------------------------------------------------------------------------
// AppLayout Component
// ---------------------------------------------------------------------------

export default function AppLayout() {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(SIDEBAR_STORAGE_KEY) === 'true';
    } catch {
      return false;
    }
  });
  const [mobileOpen, setMobileOpen] = useState(false);
  const pageTitle = usePageTitle();

  const toggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(SIDEBAR_STORAGE_KEY, String(next));
      } catch {
        // LocalStorage may be unavailable or disabled
      }
      return next;
    });
  };

  const closeMobile = () => setMobileOpen(false);
  const toggleMobile = () => setMobileOpen((prev) => !prev);

  // Close mobile drawer on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && mobileOpen) {
        setMobileOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mobileOpen]);

  return (
    <div className={`ws-shell ${isCollapsed ? 'ws-shell--collapsed' : 'ws-shell--expanded'}`}>
      <div className="ws-app-frame">
        {/* Mobile hamburger button */}
        <button
          type="button"
          className="ws-sidebar-toggle"
          aria-label={mobileOpen ? 'Close navigation' : 'Open navigation'}
          aria-expanded={mobileOpen}
          onClick={toggleMobile}
        >
          {mobileOpen ? <X size={18} aria-hidden="true" /> : <Menu size={18} aria-hidden="true" />}
        </button>

        {/* Collapsible Sidebar */}
        <Sidebar
          isCollapsed={isCollapsed}
          onToggleCollapse={toggleCollapse}
          mobileOpen={mobileOpen}
          onMobileClose={closeMobile}
        />

        {/* Main Content Area */}
        <div className={`ws-main ${isCollapsed ? 'ws-main--collapsed' : 'ws-main--expanded'}`}>
          {/* Topbar */}
          <header className="ws-topbar">
            <span className="ws-topbar-title">{pageTitle}</span>
            <div className="ws-topbar-actions">
              <Link
                to="/settings"
                className="ws-topbar-btn"
                aria-label="Settings"
              >
                <Settings size={16} aria-hidden="true" />
              </Link>
              <Link
                to="/profile"
                className="ws-topbar-avatar"
                aria-label="Profile"
              >
                U
              </Link>
            </div>
          </header>

          {/* Routed page */}
          <main id="main-content">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
