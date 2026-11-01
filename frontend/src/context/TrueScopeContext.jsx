import { createContext, useContext, useState, useMemo, useEffect } from 'react';
import {
  INITIAL_INVOICES,
  MONTHLY_TREND_DATA,
  CATEGORY_COLORS,
  SAMPLE_COMPANY_ID,
} from '../data/mockData';
import {
  loadCompanies,
  saveCompanies,
  loadActiveCompanyId,
  saveActiveCompanyId,
  loadInvoiceOwners,
  saveInvoiceOwners,
  createCompanyId,
  sizeLabel,
} from '../utils/companyStore';
import { adaptUploadedInvoice } from '../utils/invoiceAdapter';
import { apiRequest } from '../services/api';
import { calculateInvoiceStats, buildMonthlyTrend } from '../utils/reportMetrics';

const TrueScopeContext = createContext(null);

export function TrueScopeProvider({ children }) {
  const [activeScreen, setActiveScreen] = useState('overview');
  const [companies, setCompanies] = useState(loadCompanies);
  const [activeCompanyId, setActiveCompanyId] = useState(() =>
    loadActiveCompanyId(loadCompanies()),
  );
  const [invoiceOwners, setInvoiceOwners] = useState(loadInvoiceOwners);
  const [allInvoices, setAllInvoices] = useState(INITIAL_INVOICES);
  const [backendLoadError, setBackendLoadError] = useState('');
  const [notifications, setNotifications] = useState([]);
  const [isCompanyModalOpen, setIsCompanyModalOpen] = useState(false);
  const [companyModalMode, setCompanyModalMode] = useState('create');

  const company = useMemo(
    () => companies.find((item) => item.id === activeCompanyId) || companies[0],
    [companies, activeCompanyId],
  );
  const isSampleCompany = company.id === SAMPLE_COMPANY_ID;

  const invoices = useMemo(
    () =>
      allInvoices.filter((invoice) => {
        if (!invoice.isBackendUpload) return isSampleCompany;
        const owner = invoiceOwners[invoice.backendInvoiceId] || SAMPLE_COMPANY_ID;
        return owner === company.id;
      }),
    [allInvoices, invoiceOwners, company.id, isSampleCompany],
  );

  useEffect(() => saveCompanies(companies), [companies]);
  useEffect(() => saveActiveCompanyId(activeCompanyId), [activeCompanyId]);
  useEffect(() => saveInvoiceOwners(invoiceOwners), [invoiceOwners]);

  const pushNotification = (title, message, type = 'success') => {
    setNotifications((prev) => [
      { id: `notif-${Date.now()}-${prev.length}`, title, message, time: 'Just now', read: false, type },
      ...prev,
    ]);
  };

  const setCompany = (updater) => {
    setCompanies((prev) =>
      prev.map((item) => {
        if (item.id !== activeCompanyId) return item;
        const next = typeof updater === 'function' ? updater(item) : { ...item, ...updater };
        return { ...next, id: item.id, isSample: item.isSample };
      }),
    );
  };

  const addCompany = (details) => {
    const id = createCompanyId(details.name);
    const employees = Number(details.employees) || 0;
    const created = {
      id,
      isSample: false,
      name: details.name.trim(),
      industry: details.industry.trim() || 'General business',
      employees,
      size: sizeLabel(employees),
      location: details.location.trim() || 'India',
      reportingYear: details.reportingYear || String(new Date().getFullYear()),
      baselineYear: String(Number(details.reportingYear || new Date().getFullYear()) - 1),
      emissionUnit: 'kg',
      netZeroTarget: details.netZeroTarget?.trim() || '',
      factorDatabase: 'TrueScope India Default Library',
    };
    setCompanies((prev) => [...prev, created]);
    setActiveCompanyId(id);
    setActiveScreen('overview');
    return created;
  };

  const switchCompany = (id) => {
    if (companies.some((item) => item.id === id)) {
      setActiveCompanyId(id);
      setActiveScreen('overview');
      setIsDetailModalOpen(false);
      setSelectedInvoice(null);
    }
  };

  const deleteCompany = async (id) => {
    if (id === SAMPLE_COMPANY_ID) return;
    const owned = [
      ...new Set(
        allInvoices
          .filter((invoice) => invoice.isBackendUpload && invoiceOwners[invoice.backendInvoiceId] === id)
          .map((invoice) => invoice.backendInvoiceId),
      ),
    ];
    await Promise.all(
      owned.map((backendId) =>
        apiRequest(`/api/invoices/${encodeURIComponent(backendId)}`, { method: 'DELETE' }).catch(() => null),
      ),
    );
    setAllInvoices((prev) => prev.filter((invoice) => !owned.includes(invoice.backendInvoiceId)));
    setInvoiceOwners((prev) => Object.fromEntries(Object.entries(prev).filter(([, owner]) => owner !== id)));
    setCompanies((prev) => prev.filter((item) => item.id !== id));
    if (activeCompanyId === id) {
      setActiveCompanyId(SAMPLE_COMPANY_ID);
      setActiveScreen('overview');
    }
  };

  const openCompanyModal = (mode = 'create') => {
    setCompanyModalMode(mode);
    setIsCompanyModalOpen(true);
  };
  const closeCompanyModal = () => setIsCompanyModalOpen(false);

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
        setAllInvoices((previous) => {
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
    () => calculateInvoiceStats(invoices, CATEGORY_COLORS, { includeSample: isSampleCompany }),
    [invoices, isSampleCompany],
  );

  const monthlyTrends = useMemo(
    () => (isSampleCompany ? MONTHLY_TREND_DATA : buildMonthlyTrend(invoices)),
    [invoices, isSampleCompany],
  );

  // Add newly simulated invoice
  const addInvoice = (newInv) => {
    const createdInvoice = {
      ...newInv,
      id: `INV-2024-${String(allInvoices.length + 1).padStart(3, '0')}`,
      date: new Date().toISOString().split('T')[0],
      status: 'Processed',
    };

    setAllInvoices((prev) => [createdInvoice, ...prev]);

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

  const invoiceKey = (invoice) =>
    [invoice.invoiceNumber, invoice.supplier, invoice.date]
      .map((part) => String(part || '').trim().toLowerCase())
      .join('|');

  const addUploadedInvoice = (uploadResponse) => {
    const adaptedInvoices = adaptUploadedInvoice(uploadResponse);
    if (adaptedInvoices.length === 0) return { added: false, duplicate: false };

    const backendId = uploadResponse.invoice_id;
    const incomingKey = invoiceKey(adaptedInvoices[0]);
    const hasNumber = Boolean(String(adaptedInvoices[0].invoiceNumber || '').trim());
    const isDuplicate =
      hasNumber &&
      invoices.some(
        (existing) =>
          existing.isBackendUpload &&
          existing.backendInvoiceId !== backendId &&
          invoiceKey(existing) === incomingKey,
      );

    if (isDuplicate) {
      apiRequest(`/api/invoices/${encodeURIComponent(backendId)}`, { method: 'DELETE' }).catch(() => null);
      pushNotification(
        'Duplicate invoice skipped',
        `${adaptedInvoices[0].invoiceNumber} from ${adaptedInvoices[0].supplier || 'this supplier'} was already uploaded, so it was not counted twice.`,
        'info',
      );
      return { added: false, duplicate: true, invoiceNumber: adaptedInvoices[0].invoiceNumber };
    }

    setInvoiceOwners((prev) => ({ ...prev, [backendId]: company.id }));
    setAllInvoices((prev) => {
      const existingLineIds = new Set(prev.map((invoice) => invoice.id));
      const newInvoices = adaptedInvoices.filter((invoice) => !existingLineIds.has(invoice.id));
      return newInvoices.length > 0 ? [...newInvoices, ...prev] : prev;
    });
    pushNotification(
      'Invoice processed',
      `${adaptedInvoices[0].invoiceNumber || 'Invoice'} from ${adaptedInvoices[0].supplier || 'supplier'}: ${adaptedInvoices.length} line item(s) extracted.`,
    );
    return { added: true, duplicate: false };
  };

  // Delete invoice
  const deleteInvoice = async (id) => {
    const invoiceToDelete = allInvoices.find((invoice) => invoice.id === id);
    const backendInvoiceId = invoiceToDelete?.backendInvoiceId;

    if (backendInvoiceId) {
      await apiRequest(`/api/invoices/${encodeURIComponent(backendInvoiceId)}`, {
        method: 'DELETE',
      });
    }

    setAllInvoices((prev) => prev.filter((inv) =>
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
    setAllInvoices((prev) => [
      ...prev.filter((invoice) => invoice.isBackendUpload),
      ...INITIAL_INVOICES,
    ]);
  };

  // Update invoice override (e.g. if user edits quantity or category in demo)
  const updateInvoice = (updatedInv) => {
    setAllInvoices((prev) =>
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
    companies,
    isSampleCompany,
    addCompany,
    switchCompany,
    deleteCompany,
    isCompanyModalOpen,
    companyModalMode,
    openCompanyModal,
    closeCompanyModal,
    invoices,
    backendLoadError,
    stats,
    monthlyTrends,
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
