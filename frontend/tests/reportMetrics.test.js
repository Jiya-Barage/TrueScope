import assert from 'node:assert/strict';
import test from 'node:test';
import { calculateInvoiceStats, buildMonthlyTrend } from '../src/utils/reportMetrics.js';

test('uploaded totals include CO2e and CO2-basis lines but exclude demo, skipped, failed, and invalid rows', () => {
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

  assert.equal(stats.totalEmissionsKg, 115);
  assert.equal(stats.scope1Kg, 29);
  assert.equal(stats.scope2Kg, 86);
  assert.equal(stats.scope3Kg, 0);
  assert.equal(stats.demoTotalEmissionsKg, 30);
  assert.equal(stats.demoRowCount, 1);
  assert.equal(stats.invoiceCount, 6);
  assert.equal(stats.averageConfidence, 80);
  assert.equal(stats.skippedLineCount, 1);
  assert.equal(stats.ineligibleLineCount, 3);
  assert.equal(stats.co2OnlyLineCount, 1);
  assert.equal(stats.unverifiedCalculationCount, 2);
  assert.deepEqual(
    stats.categoryBreakdown.map(({ category, emissions }) => ({ category, emissions })),
    [
      { category: 'Purchased Electricity', emissions: 71 },
      { category: 'Natural Gas Heating', emissions: 29 },
      { category: 'Other', emissions: 15 },
    ],
  );

  const withSample = calculateInvoiceStats(invoices, {}, { includeSample: true });
  assert.equal(withSample.totalEmissionsKg, 145);
  assert.equal(withSample.scope1Kg, 59);
  assert.equal(withSample.invoiceCount, 7);
});

test('buildMonthlyTrend groups calculated lines by invoice month and scope', () => {
  const trend = buildMonthlyTrend([
    { isBackendUpload: true, date: '2026-09-10', scope: 'Scope 1', calculationStatus: 'calculated', emissionsBasis: 'CO2e', emissionsUnit: 'kg CO2e', emissionsValue: 100 },
    { isBackendUpload: true, date: '2026-09-22', scope: 'Scope 2', calculationStatus: 'calculated', emissionsBasis: 'CO2', emissionsUnit: 'kg CO2', emissionsValue: 50 },
    { isBackendUpload: true, date: '2026-10-02', scope: 'Scope 3', calculationStatus: 'calculated', emissionsBasis: 'CO2e', emissionsUnit: 'kg CO2e', emissionsValue: 25 },
    { isBackendUpload: true, date: '2026-10-03', scope: 'Scope 3', calculationStatus: 'skipped' },
  ]);
  assert.deepEqual(trend.map((m) => [m.month, m.total]), [['Sep 26', 150], ['Oct 26', 25]]);
  assert.equal(trend[0].scope2, 50);
});
