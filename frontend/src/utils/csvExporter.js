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
    'Emission Factor',
    'Emission Factor Unit',
    'Emission Factor Status',
    'Estimated Emissions',
    'Emissions Unit',
    'Emissions Basis',
    'Calculation Status',
    'Calculation Note',
    'Confidence Score (%)',
    'Data Provenance',
    'Status',
  ];

  const escapeCSV = (val) => {
    if (val === null || val === undefined) return '""';
    const str = String(val).replace(/"/g, '""');
    return `"${str}"`;
  };

  const rows = invoices.map((inv) => {
    const isUploaded = Boolean(inv.isBackendUpload);
    const hasEngineCalculation =
      isUploaded && inv.calculationStatus === 'calculated';
    const emissionsValue = isUploaded
      ? hasEngineCalculation
        ? inv.emissionsValue
        : null
      : inv.calculatedEmissionsKg;
    const emissionsUnit = isUploaded ? inv.emissionsUnit : 'kg CO2e';
    const emissionsBasis = isUploaded ? inv.emissionsBasis : 'CO2e';
    const calculationStatus = isUploaded
      ? inv.calculationStatus || 'not_available'
      : 'predefined_demo_value';
    const provenance = inv.source?.label || (isUploaded ? 'uploaded_invoice' : 'demo_mock');

    return [
      escapeCSV(inv.invoiceNumber),
      escapeCSV(inv.date),
      escapeCSV(inv.supplier),
      escapeCSV(inv.itemDescription),
      escapeCSV(inv.activityCategory),
      escapeCSV(inv.scope),
      escapeCSV(inv.quantity),
      escapeCSV(inv.unit),
      escapeCSV(inv.emissionFactor),
      escapeCSV(inv.emissionFactorUnit),
      escapeCSV(inv.emissionFactorNote || (isUploaded ? null : 'Demo Mock Factor - Unverified')),
      escapeCSV(emissionsValue),
      escapeCSV(emissionsUnit),
      escapeCSV(emissionsBasis),
      escapeCSV(calculationStatus),
      escapeCSV(
        isUploaded
          ? inv.calculationReason
          : 'Predefined demo/mock value; not an engine calculation.',
      ),
      escapeCSV(inv.confidence),
      escapeCSV(provenance),
      escapeCSV(inv.status),
    ];
  });

  // Include disclaimer and metadata in CSV header comments
  const reportDate = new Date().toISOString().split('T')[0];
  const metadataLines = [
    `# TrueScope Carbon Accounting - GHG Activity Data Report`,
    `# Organization: ${companyInfo.name || 'Apex Logistics & Supplies SME'}`,
    `# Reporting Period: ${companyInfo.reportingPeriod || '2024 YTD'}`,
    `# Generated At: ${reportDate}`,
    `# NOTICE: Uploaded rows retain backend emissions basis, unit, and calculation status. Demo/mock rows contain predefined values and are identified in Data Provenance.`,
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
