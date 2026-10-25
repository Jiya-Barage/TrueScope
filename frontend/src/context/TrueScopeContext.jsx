import { createContext, useContext, useState, useMemo, useEffect } from 'react';
import {
  INITIAL_COMPANY,
  INITIAL_INVOICES,
  MONTHLY_TREND_DATA,
  CATEGORY_COLORS,
  NOTIFICATIONS,
} from '../data/mockData';
import { adaptUploadedInvoice } from '../utils/invoiceAdapter';
import { apiRequest } from '../services/api';
import { calculateInvoiceStats } from '../utils/reportMetrics';

const TrueScopeContext = createContext(null);

export function TrueScopeProvider({ children }) {
  const [activeScreen, setActiveScreen] = useState('overview');
  const [company, setCompany] = useState(INITIAL_COMPANY);
  const [invoices, setInvoices] = useState(INITIAL_INVOICES);
  const [backendLoadError, setBackendLoadError] = useState('');
  const [notifications, setNotifications] = useState(NOTIFICATIONS);

  // Modals state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  // Filter state for Invoices screen
  const [invoiceSearchQuery, setInvoiceSearchQuery] = useState('');
  const [selectedScopeFilter, setSelectedScopeFilter] = useState('all');

  useEffect(() => {
    let isMounted = true;

    apiRequest('/api/invoices')
      .then((response) => {
        if (!isMounted) return;
        setBackendLoadError('');
        const restoredInvoices = Array.isArray(response?.invoices)
          ? response.invoices.flatMap(adaptUploadedInvoice)
          : [];
        setInvoices((previous) => {
          const existingIds = new Set(previous.map((invoice) => invoice.id));
          return [
            ...restoredInvoices.filter((invoice) => !existingIds.has(invoice.id)),
            ...previous,
          ];
        });
      })
      .catch((error) => {
        if (isMounted) {
          setBackendLoadError(
            error instanceof Error
              ? error.message
              : 'Could not restore saved invoices from the backend.',
          );
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Computed metrics
  const stats = useMemo(
    () => calculateInvoiceStats(invoices, CATEGORY_COLORS),
    [invoices],
  );

  // Add newly simulated invoice
  const addInvoice = (newInv) => {
    const createdInvoice = {
      ...newInv,
      id: `INV-2024-${String(invoices.length + 1).padStart(3, '0')}`,
      date: new Date().toISOString().split('T')[0],
      status: 'Processed',
    };

    setInvoices((prev) => [createdInvoice, ...prev]);

    // Add notification
    const newNotif = {
      id: `notif-${Date.now()}`,
      title: 'New Invoice Processed',
      message: `${createdInvoice.invoiceNumber || 'Invoice'} (${createdInvoice.activityCategory}) calculated: +${Math.round(createdInvoice.calculatedEmissionsKg).toLocaleString()} kg CO₂e`,
      time: 'Just now',
      read: false,
      type: 'success',
    };
    setNotifications((prev) => [newNotif, ...prev]);

    // Automatically select the new invoice for details preview if desired
    setSelectedInvoice(createdInvoice);
    setIsDetailModalOpen(true);
  };

  const addUploadedInvoice = (uploadResponse) => {
    const adaptedInvoices = adaptUploadedInvoice(uploadResponse);
    if (adaptedInvoices.length === 0) return;

    setInvoices((prev) => {
      const existingLineIds = new Set(prev.map((invoice) => invoice.id));
      const newInvoices = adaptedInvoices.filter((invoice) => !existingLineIds.has(invoice.id));
      return newInvoices.length > 0 ? [...newInvoices, ...prev] : prev;
    });
  };

  // Delete invoice
  const deleteInvoice = async (id) => {
    const invoiceToDelete = invoices.find((invoice) => invoice.id === id);
    const backendInvoiceId = invoiceToDelete?.backendInvoiceId;

    if (backendInvoiceId) {
      await apiRequest(`/api/invoices/${encodeURIComponent(backendInvoiceId)}`, {
        method: 'DELETE',
      });
    }

    setInvoices((prev) => prev.filter((inv) =>
      backendInvoiceId ? inv.backendInvoiceId !== backendInvoiceId : inv.id !== id
    ));
    if (
      selectedInvoice?.id === id ||
      (backendInvoiceId && selectedInvoice?.backendInvoiceId === backendInvoiceId)
    ) {
      setIsDetailModalOpen(false);
      setSelectedInvoice(null);
    }
  };

  // Reset to original demo data
  const resetDemoData = () => {
    setInvoices(INITIAL_INVOICES);
    setCompany(INITIAL_COMPANY);
  };

  // Update invoice override (e.g. if user edits quantity or category in demo)
  const updateInvoice = (updatedInv) => {
    setInvoices((prev) =>
      prev.map((inv) => (inv.id === updatedInv.id ? updatedInv : inv))
    );
    if (selectedInvoice?.id === updatedInv.id) {
      setSelectedInvoice(updatedInv);
    }
  };

  const openInvoiceDetail = (invoice) => {
    setSelectedInvoice(invoice);
    setIsDetailModalOpen(true);
  };

  const closeInvoiceDetail = () => {
    setIsDetailModalOpen(false);
    setSelectedInvoice(null);
  };

  const unreadNotifCount = notifications.filter((n) => !n.read).length;

  const markNotificationsAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const value = {
    activeScreen,
    setActiveScreen,
    company,
    setCompany,
    invoices,
    backendLoadError,
    stats,
    monthlyTrends: MONTHLY_TREND_DATA,
    notifications,
    unreadNotifCount,
    markNotificationsAsRead,
    isUploadModalOpen,
    setIsUploadModalOpen,
    openUploadModal: () => setIsUploadModalOpen(true),
    closeUploadModal: () => setIsUploadModalOpen(false),
    selectedInvoice,
    isDetailModalOpen,
    openInvoiceDetail,
    closeInvoiceDetail,
    addInvoice,
    addUploadedInvoice,
    deleteInvoice,
    updateInvoice,
    resetDemoData,
    invoiceSearchQuery,
    setInvoiceSearchQuery,
    selectedScopeFilter,
    setSelectedScopeFilter,
  };

  return (
    <TrueScopeContext.Provider value={value}>
      {children}
    </TrueScopeContext.Provider>
  );
}

/* eslint-disable-next-line react-refresh/only-export-components */
export function useTrueScope() {
  const context = useContext(TrueScopeContext);
  if (!context) {
    throw new Error('useTrueScope must be used within a TrueScopeProvider');
  }
  return context;
}
