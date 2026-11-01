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
import { CompanyModal } from './components/company/CompanyModal';
import './App.css';

function MainContent() {
  const { activeScreen, company } = useTrueScope();
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
          {activeScreen === 'settings' && <SettingsView key={company.id} />}
        </main>

        <footer className="ts-app-footer">
          <div className="footer-left">
            <span>TrueScope • AI-Powered Carbon Accounting for SMEs</span>
          </div>
          <div className="footer-right">
            <span>Estimates = activity data × emission factor · factor and confidence shown per line</span>
          </div>
        </footer>
      </div>

      {/* Modals */}
      <InvoiceUploadModal />
      <InvoiceDetailModal />
      <CompanyModal />
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
