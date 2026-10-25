const VALID_SCOPES = new Set(['Scope 1', 'Scope 2', 'Scope 3']);

const isValidEmission = (value) =>
  typeof value === 'number' && Number.isFinite(value) && value >= 0;

export function calculateInvoiceStats(invoices, categoryColors = {}) {
  const uploadedScopeTotals = { 'Scope 1': 0, 'Scope 2': 0, 'Scope 3': 0 };
  const demoScopeTotals = { 'Scope 1': 0, 'Scope 2': 0, 'Scope 3': 0 };
  const categoryMap = new Map();
  const uploadedInvoiceIds = new Set();
  let totalConfidence = 0;
  let confidenceCount = 0;
  let skippedLineCount = 0;
  let ineligibleLineCount = 0;
  let unverifiedCalculationCount = 0;
  let co2OnlyLineCount = 0;
  let demoRowCount = 0;

  for (const invoice of invoices) {
    if (!invoice.isBackendUpload) {
      demoRowCount += 1;
      const emission = invoice.calculatedEmissionsKg;
      if (VALID_SCOPES.has(invoice.scope) && isValidEmission(emission)) {
        demoScopeTotals[invoice.scope] += emission;
      }
      continue;
    }

    uploadedInvoiceIds.add(invoice.backendInvoiceId || invoice.id);
    if (invoice.calculationStatus === 'skipped') skippedLineCount += 1;
    if (
      invoice.calculationStatus === 'calculated' &&
      invoice.emissionsBasis === 'CO2'
    ) {
      co2OnlyLineCount += 1;
    }
    if (
      invoice.calculationStatus === 'calculated' &&
      isValidEmission(invoice.emissionsValue) &&
      invoice.emissionFactorVerified !== true
    ) {
      unverifiedCalculationCount += 1;
    }
    if (typeof invoice.confidence === 'number' && Number.isFinite(invoice.confidence)) {
      totalConfidence += invoice.confidence;
      confidenceCount += 1;
    }

    const emission = invoice.calculatedEmissionsKg;
    const eligible =
      invoice.calculationStatus === 'calculated' &&
      invoice.emissionsBasis === 'CO2e' &&
      invoice.emissionsUnit === 'kg CO2e' &&
      VALID_SCOPES.has(invoice.scope) &&
      isValidEmission(emission);

    if (!eligible) {
      ineligibleLineCount += 1;
      continue;
    }

    uploadedScopeTotals[invoice.scope] += emission;
    const category = invoice.activityCategory || 'Other';
    if (!categoryMap.has(category)) {
      categoryMap.set(category, {
        category,
        emissions: 0,
        scope: invoice.scope,
        color: categoryColors[category] || '#64748b',
        invoiceIds: new Set(),
      });
    }
    const categoryData = categoryMap.get(category);
    categoryData.emissions += emission;
    categoryData.invoiceIds.add(invoice.backendInvoiceId || invoice.id);
  }

  const totalEmissionsKg = Object.values(uploadedScopeTotals).reduce(
    (total, value) => total + value,
    0,
  );
  const scope1Kg = uploadedScopeTotals['Scope 1'];
  const scope2Kg = uploadedScopeTotals['Scope 2'];
  const scope3Kg = uploadedScopeTotals['Scope 3'];
  const categoryBreakdown = [...categoryMap.values()]
    .map(({ invoiceIds, ...category }) => ({
      ...category,
      count: invoiceIds.size,
      percentage: totalEmissionsKg > 0
        ? (category.emissions / totalEmissionsKg) * 100
        : 0,
    }))
    .sort((first, second) => second.emissions - first.emissions);

  return {
    totalEmissionsKg,
    scope1Kg,
    scope2Kg,
    scope3Kg,
    scope1Pct: totalEmissionsKg > 0 ? (scope1Kg / totalEmissionsKg) * 100 : 0,
    scope2Pct: totalEmissionsKg > 0 ? (scope2Kg / totalEmissionsKg) * 100 : 0,
    scope3Pct: totalEmissionsKg > 0 ? (scope3Kg / totalEmissionsKg) * 100 : 0,
    invoiceCount: uploadedInvoiceIds.size,
    averageConfidence: confidenceCount > 0
      ? Math.round(totalConfidence / confidenceCount)
      : 0,
    skippedLineCount,
    ineligibleLineCount,
    unverifiedCalculationCount,
    co2OnlyLineCount,
    categoryBreakdown,
    demoTotalEmissionsKg: Object.values(demoScopeTotals).reduce(
      (total, value) => total + value,
      0,
    ),
    demoRowCount,
  };
}
