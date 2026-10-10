import {
  LeafIcon,
  DashboardIcon,
  FileTextIcon,
  BarChartIcon,
  ReportIcon,
  SettingsIcon,
  XIcon,
  UploadCloudIcon,
} from '../common/Icons';
import { useTrueScope } from '../../context/TrueScopeContext';

export const Sidebar = ({ isMobileOpen, onCloseMobile }) => {
  const { activeScreen, setActiveScreen, openUploadModal, invoices } = useTrueScope();

  const navItems = [
    { id: 'overview', label: 'Overview', icon: DashboardIcon },
    { id: 'invoices', label: 'Invoices', icon: FileTextIcon, count: invoices.length },
    { id: 'emissions', label: 'Emissions', icon: BarChartIcon },
    { id: 'reports', label: 'Reports', icon: ReportIcon },
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
  ];

  const handleNavClick = (screenId) => {
    setActiveScreen(screenId);
    if (onCloseMobile) onCloseMobile();
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="sidebar-mobile-backdrop"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      <aside className={`ts-sidebar ${isMobileOpen ? 'open' : ''}`}>
        {/* Brand Header */}
        <div className="sidebar-brand">
          <div className="brand-logo-wrap">
            <LeafIcon size={24} className="brand-leaf-icon" />
          </div>
          <div className="brand-text-wrap">
            <span className="brand-name">TrueScope</span>
            <span className="brand-tagline">SME Carbon Accounting</span>
          </div>

          {/* Mobile close button */}
          <button
            type="button"
            className="sidebar-mobile-close"
            onClick={onCloseMobile}
            aria-label="Close menu"
          >
            <XIcon size={20} />
          </button>
        </div>

        {/* Demo Mode Notice */}
        <div className="sidebar-demo-notice">
          <span className="pulse-dot" />
          <span className="demo-notice-text">Demo Prototype Mode</span>
        </div>

        {/* Navigation Items */}
        <nav className="sidebar-nav">
          <div className="nav-section-title">Navigation</div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeScreen === item.id;
            return (
              <button
                key={item.id}
                type="button"
                className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                onClick={() => handleNavClick(item.id)}
              >
                <Icon size={19} className="nav-item-icon" />
                <span className="nav-item-label">{item.label}</span>
                {item.count !== undefined && (
                  <span className="nav-item-count">{item.count}</span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Quick Upload CTA */}
        <div className="sidebar-cta-card">
          <div className="cta-icon-wrap">
            <UploadCloudIcon size={20} />
          </div>
          <h4 className="cta-title">Upload SME Invoice</h4>
          <p className="cta-description">
            Simulate OCR extraction and GHG activity mapping.
          </p>
          <button
            type="button"
            className="btn-sidebar-upload"
            onClick={() => {
              openUploadModal();
              if (onCloseMobile) onCloseMobile();
            }}
          >
            + Process New Invoice
          </button>
        </div>

        {/* Bottom Sustainability Pledge Footer */}
        <div className="sidebar-footer">
          <div className="pledge-card">
            <span className="pledge-label">SME Climate Target</span>
            <strong className="pledge-target">Net Zero by 2035</strong>
            <span className="pledge-status">Tracked against baseline</span>
          </div>
        </div>
      </aside>
    </>
  );
};
