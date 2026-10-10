/**
 * Client-side CSV generator and exporter for TrueScope carbon reports.
 * Complies with DEMO labeling requirements.
 */

export const generateEmissionsCSV = (invoices, companyInfo = {}) => {
  const headers = [
    'Invoice Number',
    'Date',
    'Supplier',
    'Extracted Item',
    'Activity Category',
    'GHG Scope',
    'Quantity',
    'Unit',
    'Emission Factor (kg CO2e/unit)',
    'Emission Factor Status',
    'Estimated Emissions (kg CO2e)',
    'Confidence Score (%)',
    'Status',
  ];

  const escapeCSV = (val) => {
    if (val === null || val === undefined) return '""';
    const str = String(val).replace(/"/g, '""');
    return `"${str}"`;
  };

  const rows = invoices.map((inv) => [
    escapeCSV(inv.invoiceNumber),
    escapeCSV(inv.date),
    escapeCSV(inv.supplier),
    escapeCSV(inv.itemDescription),
    escapeCSV(inv.activityCategory),
    escapeCSV(inv.scope),
    escapeCSV(inv.quantity),
    escapeCSV(inv.unit),
    escapeCSV(inv.emissionFactor),
    escapeCSV(inv.emissionFactorNote || 'Demo Mock Factor - Unverified'),
    escapeCSV(inv.calculatedEmissionsKg),
    escapeCSV(inv.confidence),
    escapeCSV(inv.status),
  ]);

  // Include disclaimer and metadata in CSV header comments
  const reportDate = new Date().toISOString().split('T')[0];
  const metadataLines = [
    `# TrueScope Carbon Accounting - GHG Activity Data Report (DEMO EXPORT)`,
    `# Organization: ${companyInfo.name || 'Apex Logistics & Supplies SME'}`,
    `# Reporting Period: ${companyInfo.reportingPeriod || '2024 YTD'}`,
    `# Generated At: ${reportDate}`,
    `# NOTICE: Data contains demonstration calculations. Emission factors are unverified demo placeholders.`,
    `#`,
  ];

  const csvContent = [
    ...metadataLines,
    headers.join(','),
    ...rows.map((r) => r.join(',')),
  ].join('\r\n');

  return csvContent;
};

export const downloadCSV = (content, filename = 'truescope-emissions-report-demo.csv') => {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};
