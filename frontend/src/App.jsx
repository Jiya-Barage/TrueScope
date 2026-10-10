import { useState } from 'react';
import { TrueScopeProvider, useTrueScope } from './context/TrueScopeContext';
import { Sidebar } from './components/layout/Sidebar';
import { TopBar } from './components/layout/TopBar';
import { OverviewView } from './views/OverviewView';
import { InvoicesView } from './views/InvoicesView';
import { EmissionsView } from './views/EmissionsView';
import { ReportsView } from './views/ReportsView';
import { SettingsView } from './views/SettingsView';
import { InvoiceUploadModal } from './components/invoices/InvoiceUploadModal';
import { InvoiceDetailModal } from './components/invoices/InvoiceDetailModal';
import './App.css';

function MainContent() {
  const { activeScreen } = useTrueScope();
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  return (
    <div className="ts-app-layout">
      {/* Sidebar (Desktop + Mobile Drawer) */}
      <Sidebar
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="ts-main-panel">
        <TopBar onOpenMobileSidebar={() => setIsMobileSidebarOpen(true)} />

        <main className="ts-content-body">
          {activeScreen === 'overview' && <OverviewView />}
          {activeScreen === 'invoices' && <InvoicesView />}
          {activeScreen === 'emissions' && <EmissionsView />}
          {activeScreen === 'reports' && <ReportsView />}
          {activeScreen === 'settings' && <SettingsView />}
        </main>

        <footer className="ts-app-footer">
          <div className="footer-left">
            <span>TrueScope • AI-Powered Carbon Accounting for SMEs</span>
            <span className="footer-sep">•</span>
            <span className="footer-hackathon-tag">Hackathon Demonstration Prototype</span>
          </div>
          <div className="footer-right">
            <span>Demo calculations use simulated mock factors</span>
          </div>
        </footer>
      </div>

      {/* Modals */}
      <InvoiceUploadModal />
      <InvoiceDetailModal />
    </div>
  );
}

export default function App() {
  return (
    <TrueScopeProvider>
      <MainContent />
    </TrueScopeProvider>
  );
}
