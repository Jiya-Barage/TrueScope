import { prettyCategory } from './formatters.js';

const VALID_SCOPES = new Set(['Scope 1', 'Scope 2', 'Scope 3']);

const isValidEmission = (value) =>
  typeof value === 'number' && Number.isFinite(value) && value >= 0;

const ELIGIBLE_BASES = new Set(['CO2e', 'CO2']);
const ELIGIBLE_UNITS = new Set(['kg CO2e', 'kg CO2']);

export function calculateInvoiceStats(invoices, categoryColors = {}, options = {}) {
  const { includeSample = false } = options;
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
        if (includeSample) {
          uploadedScopeTotals[invoice.scope] += emission;
          const sampleCategory = prettyCategory(invoice.activityCategory);
          if (!categoryMap.has(sampleCategory)) {
            categoryMap.set(sampleCategory, {
              category: sampleCategory,
              emissions: 0,
              scope: invoice.scope,
              color: categoryColors[sampleCategory] || '#64748b',
              invoiceIds: new Set(),
            });
          }
          const sampleData = categoryMap.get(sampleCategory);
          sampleData.emissions += emission;
          sampleData.invoiceIds.add(invoice.id);
        }
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

    const emission = ELIGIBLE_BASES.has(invoice.emissionsBasis) &&
      ELIGIBLE_UNITS.has(invoice.emissionsUnit)
      ? invoice.emissionsValue
      : null;
    const eligible =
      invoice.calculationStatus === 'calculated' &&
      VALID_SCOPES.has(invoice.scope) &&
      isValidEmission(emission);

    if (!eligible) {
      ineligibleLineCount += 1;
      continue;
    }

    uploadedScopeTotals[invoice.scope] += emission;
    const category = prettyCategory(invoice.activityCategory);
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
    invoiceCount: includeSample
      ? uploadedInvoiceIds.size + demoRowCount
      : uploadedInvoiceIds.size,
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

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * Builds a month-by-month emissions series (kg CO2e) from a company's invoices.
 * Only calculated rows with a valid scope and emission value are included.
 */
export function buildMonthlyTrend(invoices) {
  const buckets = new Map();
  for (const invoice of invoices) {
    if (!VALID_SCOPES.has(invoice.scope)) continue;
    let emission = null;
    if (invoice.isBackendUpload) {
      if (
        invoice.calculationStatus === 'calculated' &&
        ELIGIBLE_BASES.has(invoice.emissionsBasis) &&
        ELIGIBLE_UNITS.has(invoice.emissionsUnit)
      ) {
        emission = invoice.emissionsValue;
      }
    } else {
      emission = invoice.calculatedEmissionsKg;
    }
    if (!isValidEmission(emission)) continue;
    const match = /^(\d{4})-(\d{2})/.exec(invoice.date || '');
    if (!match) continue;
    const key = `${match[1]}-${match[2]}`;
    if (!buckets.has(key)) {
      buckets.set(key, {
        key,
        month: `${MONTH_NAMES[Number(match[2]) - 1]} ${match[1].slice(2)}`,
        scope1: 0,
        scope2: 0,
        scope3: 0,
      });
    }
    const bucket = buckets.get(key);
    if (invoice.scope === 'Scope 1') bucket.scope1 += emission;
    if (invoice.scope === 'Scope 2') bucket.scope2 += emission;
    if (invoice.scope === 'Scope 3') bucket.scope3 += emission;
  }
  return [...buckets.values()]
    .sort((a, b) => a.key.localeCompare(b.key))
    .map((bucket) => ({
      ...bucket,
      total: bucket.scope1 + bucket.scope2 + bucket.scope3,
    }));
}
