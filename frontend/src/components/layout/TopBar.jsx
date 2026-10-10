import { useState, useRef, useEffect } from 'react';
import {
  MenuIcon,
  BellIcon,
  UploadCloudIcon,
  BuildingIcon,
  CheckCircleIcon,
  InfoIcon,
} from '../common/Icons';
import { useTrueScope } from '../../context/TrueScopeContext';

export const TopBar = ({ onOpenMobileSidebar }) => {
  const {
    activeScreen,
    company,
    openUploadModal,
    notifications,
    unreadNotifCount,
    markNotificationsAsRead,
  } = useTrueScope();

  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const notifRef = useRef(null);

  // Close notifications when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (notifRef.current && !notifRef.current.contains(event.target)) {
        setIsNotifOpen(false);
      }
    };
    if (isNotifOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isNotifOpen]);

  const titles = {
    overview: {
      title: 'Carbon Accounting Dashboard',
      subtitle: 'Real-time overview of estimated greenhouse gas emissions across Scopes 1, 2 & 3.',
    },
    invoices: {
      title: 'Invoices & Activity Data',
      subtitle: 'Uploaded business invoices, OCR extracted line items, and emission mappings.',
    },
    emissions: {
      title: 'Emissions Analysis by Scope',
      subtitle: 'Detailed breakdown aligned with the Greenhouse Gas (GHG) Protocol corporate standard.',
    },
    reports: {
      title: 'Carbon Reporting & Export',
      subtitle: 'Audit-ready summary reports and local CSV data export for SME stakeholders.',
    },
    settings: {
      title: 'Platform & Organization Settings',
      subtitle: 'Manage demo SME profile, reporting parameters, and factor databases.',
    },
  };

  const currentMeta = titles[activeScreen] || titles.overview;

  const handleToggleNotif = () => {
    if (!isNotifOpen && unreadNotifCount > 0) {
      markNotificationsAsRead();
    }
    setIsNotifOpen(!isNotifOpen);
  };

  return (
    <header className="ts-topbar">
      <div className="topbar-left">
        <button
          type="button"
          className="topbar-menu-btn"
          onClick={onOpenMobileSidebar}
          aria-label="Open mobile menu"
        >
          <MenuIcon size={22} />
        </button>

        <div className="topbar-heading">
          <div className="topbar-title-row">
            <h1 className="topbar-title">{currentMeta.title}</h1>
            <span className="demo-badge">DEMO DATA</span>
          </div>
          <p className="topbar-subtitle">{currentMeta.subtitle}</p>
        </div>
      </div>

      <div className="topbar-right">
        {/* Quick Upload Action */}
        <button
          type="button"
          className="btn-topbar-action"
          onClick={openUploadModal}
        >
          <UploadCloudIcon size={18} />
          <span>Upload Invoice</span>
        </button>

        {/* Notification Bell */}
        <div className="topbar-notif-wrap" ref={notifRef}>
          <button
            type="button"
            className="topbar-icon-btn"
            onClick={handleToggleNotif}
            aria-label="Notifications"
          >
            <BellIcon size={19} />
            {unreadNotifCount > 0 && (
              <span className="topbar-notif-pill">{unreadNotifCount}</span>
            )}
          </button>

          {isNotifOpen && (
            <div className="notif-dropdown">
              <div className="notif-dropdown-header">
                <div>
                  <h4 className="notif-title">Activity Alerts</h4>
                  <span className="notif-subtitle">Simulated engine events</span>
                </div>
                {unreadNotifCount > 0 && (
                  <button
                    type="button"
                    className="notif-mark-read"
                    onClick={markNotificationsAsRead}
                  >
                    Mark read
                  </button>
                )}
              </div>

              <div className="notif-dropdown-list">
                {notifications.length === 0 ? (
                  <div className="notif-empty">No alerts at this time</div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      className={`notif-item ${n.read ? 'read' : 'unread'}`}
                    >
                      <div className="notif-icon">
                        {n.type === 'success' ? (
                          <CheckCircleIcon size={16} />
                        ) : (
                          <InfoIcon size={16} />
                        )}
                      </div>
                      <div className="notif-content">
                        <strong className="notif-item-title">{n.title}</strong>
                        <p className="notif-item-message">{n.message}</p>
                        <span className="notif-item-time">{n.time}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Company Profile Card */}
        <div className="topbar-company-pill" title="Demo SME Profile">
          <div className="company-avatar">
            <BuildingIcon size={16} />
          </div>
          <div className="company-info-text">
            <span className="company-name">{company.name}</span>
            <span className="company-badge">{company.size}</span>
          </div>
        </div>
      </div>
    </header>
  );
};
