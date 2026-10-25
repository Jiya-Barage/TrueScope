import assert from 'node:assert/strict';
import test from 'node:test';
import {
  createReportFilename,
  downloadCSV,
  generateEmissionsCSV,
} from '../src/utils/csvExporter.js';

const parseCSV = (content) => {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;

  for (let index = 0; index < content.length; index += 1) {
    const character = content[index];
    if (quoted) {
      if (character === '"' && content[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (character === '"') {
        quoted = false;
      } else {
        field += character;
      }
    } else if (character === '"' && field.length === 0) {
      quoted = true;
    } else if (character === ',') {
      row.push(field);
      field = '';
    } else if (character === '\r' || character === '\n') {
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
      if (character === '\r' && content[index + 1] === '\n') index += 1;
    } else {
      field += character;
    }
  }

  assert.equal(quoted, false, 'CSV ends with a closed quoted field');
  if (row.length > 0 || field.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows;
};

test('CSV export preserves data, basis, trust metadata, and escaping', () => {
  const csv = generateEmissionsCSV(
    [
      {
        isBackendUpload: true,
        invoiceNumber: 'INV-1',
        date: '2026-10-20',
        supplier: 'Société, "Énergie"\nNorth',
        itemDescription: 'Electricity, "grid"\nconsumption',
        activityCategory: 'electricity_grid',
        scope: 'Scope 2',
        quantity: 100,
        unit: 'kWh',
        emissionFactor: 0.71,
        emissionFactorUnit: 'kg CO2/kWh',
        emissionFactorNote: 'unverified_demo_value',
        emissionFactorGeography: null,
        emissionFactorLibraryDefaultGeography: 'India',
        emissionFactorProvenance: {
          source_title: 'Grid emissions study',
          source_publisher: 'Example energy authority',
          dataset_version: 'v1',
          publication_year: 2025,
          activity_boundary: 'Purchased grid electricity',
          method: 'Location-based average',
          rationale: 'Illustrative test provenance only.',
        },
        emissionFactorVerified: false,
        emissionFactorSource: 'https://example.gov/source?a=1&b=2',
        emissionFactorSourceYear: 2025,
        emissionsValue: 71,
        emissionsUnit: 'kg CO2',
        emissionsBasis: 'CO2',
        calculationStatus: 'calculated',
        calculationReason: null,
        confidence: 90,
        source: { label: 'uploaded_invoice' },
        status: 'Processed',
      },
    ],
    {
      name: 'Company, "Énergie"\nNorth',
      reportingPeriod: 'All available records',
    },
  );

  const rows = parseCSV(csv);
  assert.equal(rows[0][0], '# TrueScope Carbon Accounting - GHG Activity Data Report');
  assert.equal(rows[1][0], '# Organization: Company, "Énergie"\nNorth');
  assert.equal(rows[2][0], '# Reporting Period: All available records');

  const headerIndex = rows.findIndex((row) => row[0] === 'Invoice Number');
  const headers = rows[headerIndex];
  const invoice = rows[headerIndex + 1];
  const value = (header) => invoice[headers.indexOf(header)];

  assert.ok(rows.every((row) => row.length === headers.length));
  assert.equal(headers.length, invoice.length);
  assert.equal(value('Invoice Number'), 'INV-1');
  assert.equal(value('Supplier'), 'Société, "Énergie"\nNorth');
  assert.equal(value('Extracted Item'), 'Electricity, "grid"\nconsumption');
  assert.equal(value('Emission Factor Source'), 'https://example.gov/source?a=1&b=2');
  assert.equal(value('Emission Factor Reference Year'), '2025');
  assert.equal(value('Emission Factor Geography'), '');
  assert.equal(value('Library Default Geography'), 'India');
  assert.equal(value('Emission Factor Source Title'), 'Grid emissions study');
  assert.equal(value('Emission Factor Source Publisher'), 'Example energy authority');
  assert.equal(value('Emission Factor Dataset Version'), 'v1');
  assert.equal(value('Emission Factor Publication Year'), '2025');
  assert.equal(value('Emission Factor Activity Boundary'), 'Purchased grid electricity');
  assert.equal(value('Emission Factor Method'), 'Location-based average');
  assert.equal(value('Emission Factor Provenance Limitation'), 'Illustrative test provenance only.');
  assert.equal(value('Emission Factor Verified'), 'false');
  assert.equal(value('Emission Factor Status'), 'unverified_demo_value');
  assert.equal(value('Estimated Emissions'), '71');
  assert.equal(value('Emissions Unit'), 'kg CO2');
  assert.equal(value('Emissions Basis'), 'CO2');
  assert.equal(value('Calculation Status'), 'calculated');
  assert.equal(value('Status'), 'Processed');
  assert.equal(value('Data Provenance'), 'uploaded_invoice');
  assert.notEqual(value('Emissions Unit'), 'kg CO2e');
});

test('download creates a UTF-8 CSV Blob, valid filename, and delays URL revocation', async () => {
  const originalDocument = globalThis.document;
  const originalSetTimeout = globalThis.setTimeout;
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;
  let clicked = false;
  let removed = false;
  let blob;
  let delayedCallback;
  const attributes = {};
  const revoked = [];

  globalThis.document = {
    body: { appendChild: () => {} },
    createElement: () => ({
      style: {},
      setAttribute: (name, value) => { attributes[name] = value; },
      click: () => { clicked = true; },
      remove: () => { removed = true; },
    }),
  };
  globalThis.setTimeout = (callback, milliseconds) => {
    assert.equal(milliseconds, 1000);
    delayedCallback = callback;
    return 1;
  };
  URL.createObjectURL = (createdBlob) => {
    blob = createdBlob;
    return 'blob:truescope-report';
  };
  URL.revokeObjectURL = (url) => revoked.push(url);

  try {
    downloadCSV('a,b\r\n1,2', 'truescope-report.csv');
    assert.equal(blob.type, 'text/csv;charset=utf-8;');
    assert.equal(await blob.text(), 'a,b\r\n1,2');
    assert.equal(attributes.href, 'blob:truescope-report');
    assert.equal(attributes.download, 'truescope-report.csv');
    assert.equal(clicked, true);
    assert.equal(removed, true);
    assert.deepEqual(revoked, []);
    delayedCallback();
    assert.deepEqual(revoked, ['blob:truescope-report']);
  } finally {
    globalThis.document = originalDocument;
    globalThis.setTimeout = originalSetTimeout;
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
  }
});

test('report filename is sanitized and has a safe fallback', () => {
  assert.equal(
    createReportFilename('Company, Énergie', new Date('2026-10-25T00:00:00.000Z')),
    'truescope-emissions-report-company-nergie-2026-10-25.csv',
  );
  assert.equal(
    createReportFilename('💚', new Date('2026-10-25T00:00:00.000Z')),
    'truescope-emissions-report-organization-2026-10-25.csv',
  );
});
