import assert from 'node:assert/strict';
import test from 'node:test';
import { calculateInvoiceStats } from '../src/utils/reportMetrics.js';

test('uploaded CO2e totals exclude demo, CO2-only, skipped, failed, and invalid rows', () => {
  const invoices = [
    {
      isBackendUpload: false,
      id: 'demo-1',
      scope: 'Scope 1',
      calculatedEmissionsKg: 30,
    },
    {
      isBackendUpload: true,
      id: 'upload-1:1',
      backendInvoiceId: 'upload-1',
      calculationStatus: 'calculated',
      emissionsBasis: 'CO2e',
      emissionsUnit: 'kg CO2e',
      calculatedEmissionsKg: 71,
      emissionsValue: 71,
      scope: 'Scope 2',
      activityCategory: 'electricity_grid',
      emissionFactorVerified: false,
      confidence: 80,
    },
    {
      isBackendUpload: true,
      id: 'upload-2:1',
      backendInvoiceId: 'upload-2',
      calculationStatus: 'calculated',
      emissionsBasis: 'CO2e',
      emissionsUnit: 'kg CO2e',
      calculatedEmissionsKg: 29,
      emissionsValue: 29,
      scope: 'Scope 1',
      activityCategory: 'natural_gas',
      emissionFactorVerified: true,
      confidence: 90,
    },
    {
      isBackendUpload: true,
      id: 'upload-3:1',
      backendInvoiceId: 'upload-3',
      calculationStatus: 'calculated',
      emissionsBasis: 'CO2',
      emissionsUnit: 'kg CO2',
      emissionsValue: 15,
      calculatedEmissionsKg: null,
      scope: 'Scope 2',
      confidence: 70,
    },
    {
      isBackendUpload: true,
      id: 'upload-4:1',
      backendInvoiceId: 'upload-4',
      calculationStatus: 'skipped',
      scope: 'Scope 3',
    },
    {
      isBackendUpload: true,
      id: 'upload-5:1',
      backendInvoiceId: 'upload-5',
      calculationStatus: 'failed',
      scope: 'Scope 3',
      calculatedEmissionsKg: 1000,
      emissionsBasis: 'CO2e',
      emissionsUnit: 'kg CO2e',
    },
    {
      isBackendUpload: true,
      id: 'upload-6:1',
      backendInvoiceId: 'upload-6',
      calculationStatus: 'calculated',
      emissionsBasis: 'CO2e',
      emissionsUnit: 'kg CO2e',
      calculatedEmissionsKg: Number.NaN,
      scope: 'Scope 3',
    },
  ];

  const stats = calculateInvoiceStats(invoices);

  assert.equal(stats.totalEmissionsKg, 100);
  assert.equal(stats.scope1Kg, 29);
  assert.equal(stats.scope2Kg, 71);
  assert.equal(stats.scope3Kg, 0);
  assert.equal(stats.demoTotalEmissionsKg, 30);
  assert.equal(stats.demoRowCount, 1);
  assert.equal(stats.invoiceCount, 6);
  assert.equal(stats.averageConfidence, 80);
  assert.equal(stats.skippedLineCount, 1);
  assert.equal(stats.ineligibleLineCount, 4);
  assert.equal(stats.co2OnlyLineCount, 1);
  assert.equal(stats.unverifiedCalculationCount, 2);
  assert.deepEqual(
    stats.categoryBreakdown.map(({ category, emissions }) => ({ category, emissions })),
    [
      { category: 'electricity_grid', emissions: 71 },
      { category: 'natural_gas', emissions: 29 },
    ],
  );
});
