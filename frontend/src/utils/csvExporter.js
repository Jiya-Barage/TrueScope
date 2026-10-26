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
    'Emission Factor Source',
    'Emission Factor Source Title',
    'Emission Factor Source Publisher',
    'Emission Factor Dataset Version',
    'Emission Factor Publication Year',
    'Emission Factor Reference Year',
    'Emission Factor Geography',
    'Library Default Geography',
    'Emission Factor Activity Boundary',
    'Emission Factor Method',
    'Emission Factor Provenance Limitation',
    'Emission Factor Verified',
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
      escapeCSV(inv.emissionFactorNote || (isUploaded ? null : 'Unverified emission factor')),
      escapeCSV(inv.emissionFactorSource),
      escapeCSV(inv.emissionFactorProvenance?.source_title),
      escapeCSV(inv.emissionFactorProvenance?.source_publisher),
      escapeCSV(inv.emissionFactorProvenance?.dataset_version),
      escapeCSV(inv.emissionFactorProvenance?.publication_year),
      escapeCSV(inv.emissionFactorSourceYear),
      escapeCSV(inv.emissionFactorGeography),
      escapeCSV(inv.emissionFactorLibraryDefaultGeography),
      escapeCSV(inv.emissionFactorProvenance?.activity_boundary),
      escapeCSV(inv.emissionFactorProvenance?.method),
      escapeCSV(inv.emissionFactorProvenance?.rationale),
      escapeCSV(isUploaded ? inv.emissionFactorVerified : false),
      escapeCSV(emissionsValue),
      escapeCSV(emissionsUnit),
      escapeCSV(emissionsBasis),
      escapeCSV(calculationStatus),
      escapeCSV(
        isUploaded
          ? inv.calculationReason
          : 'Predefined sample value; not an engine calculation.',
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
    `# NOTICE: This export includes all available rows, not a filtered reporting period. Uploaded rows retain the backend emissions basis, unit, factor geography, verification state, and calculation status. Sample rows contain predefined values and are identified in Data Provenance.`,
    `#`,
  ].map((line) =>
    [escapeCSV(line), ...headers.slice(1).map(() => '""')].join(','),
  );

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
  try {
    link.click();
  } finally {
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
};

export const createReportFilename = (organizationName, date = new Date()) => {
  const organizationSlug = String(organizationName || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'organization';
  return `truescope-emissions-report-${organizationSlug}-${date.toISOString().slice(0, 10)}.csv`;
};
