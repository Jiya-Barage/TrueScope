import { createContext, useContext, useState, useMemo } from 'react';
import {
  INITIAL_COMPANY,
  INITIAL_INVOICES,
  MONTHLY_TREND_DATA,
  CATEGORY_COLORS,
  NOTIFICATIONS,
} from '../data/mockData';
import { adaptUploadedInvoice } from '../utils/invoiceAdapter';

const TrueScopeContext = createContext(null);

export function TrueScopeProvider({ children }) {
  const [activeScreen, setActiveScreen] = useState('overview');
  const [company, setCompany] = useState(INITIAL_COMPANY);
  const [invoices, setInvoices] = useState(INITIAL_INVOICES);
  const [notifications, setNotifications] = useState(NOTIFICATIONS);

  // Modals state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  // Filter state for Invoices screen
  const [invoiceSearchQuery, setInvoiceSearchQuery] = useState('');
  const [selectedScopeFilter, setSelectedScopeFilter] = useState('all');

  // Computed metrics
  const stats = useMemo(() => {
    let scope1 = 0;
    let scope2 = 0;
    let scope3 = 0;
    let totalConfidence = 0;
    let confidenceCount = 0;

    const categoryMap = {};

    invoices.forEach((inv) => {
      const canAggregateAsCo2e =
        !inv.isBackendUpload ||
        (inv.emissionsBasis === 'CO2e' && inv.emissionsUnit === 'kg CO2e');
      const em = canAggregateAsCo2e ? Number(inv.calculatedEmissionsKg) || 0 : 0;
      if (inv.scope === 'Scope 1') scope1 += em;
      else if (inv.scope === 'Scope 2') scope2 += em;
      else if (inv.scope === 'Scope 3') scope3 += em;

      if (typeof inv.confidence === 'number' && Number.isFinite(inv.confidence)) {
        totalConfidence += inv.confidence;
        confidenceCount += 1;
      }

      const cat = inv.activityCategory || 'Other';
      if (canAggregateAsCo2e && !categoryMap[cat]) {
        categoryMap[cat] = {
          category: cat,
          emissions: 0,
          scope: inv.scope,
          color: CATEGORY_COLORS[cat] || '#64748b',
          invoiceIds: new Set(),
        };
      }
      if (canAggregateAsCo2e) {
        categoryMap[cat].emissions += em;
        categoryMap[cat].invoiceIds.add(inv.backendInvoiceId || inv.id);
      }
    });

    const totalEmissionsKg = scope1 + scope2 + scope3;

    // Convert category map to sorted array with percentages
    const categoryBreakdown = Object.values(categoryMap)
      .map(({ invoiceIds, ...item }) => ({
        ...item,
        count: invoiceIds.size,
        percentage: totalEmissionsKg > 0 ? (item.emissions / totalEmissionsKg) * 100 : 0,
      }))
      .sort((a, b) => b.emissions - a.emissions);

    const averageConfidence = confidenceCount > 0
      ? Math.round(totalConfidence / confidenceCount)
      : 0;

    return {
      totalEmissionsKg,
      scope1Kg: scope1,
      scope2Kg: scope2,
      scope3Kg: scope3,
      scope1Pct: totalEmissionsKg > 0 ? (scope1 / totalEmissionsKg) * 100 : 0,
      scope2Pct: totalEmissionsKg > 0 ? (scope2 / totalEmissionsKg) * 100 : 0,
      scope3Pct: totalEmissionsKg > 0 ? (scope3 / totalEmissionsKg) * 100 : 0,
      invoiceCount: new Set(invoices.map((inv) => inv.backendInvoiceId || inv.id)).size,
      averageConfidence,
      categoryBreakdown,
    };
  }, [invoices]);

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
  const deleteInvoice = (id) => {
    const invoiceToDelete = invoices.find((invoice) => invoice.id === id);
    const backendInvoiceId = invoiceToDelete?.backendInvoiceId;
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
