import assert from 'node:assert/strict';
import test from 'node:test';
import { adaptUploadedInvoice } from '../src/utils/invoiceAdapter.js';

test('uploaded invoice adapter preserves partial calculation status', () => {
  const [invoice] = adaptUploadedInvoice({
    invoice_id: 'inv_partial',
    status: 'completed',
    result: {
      emission_calculation_status: 'partial',
      line_items: [
        {
          description: 'Office paper',
          category: 'purchased_goods',
          calculation_status: 'skipped',
          calculation_reason: 'No emission factor matches this category and unit.',
          review_required: true,
          review_reasons: ['No emission factor matches this category and unit.'],
        },
      ],
    },
  });

  assert.equal(invoice.processingStatus, 'completed');
  assert.equal(invoice.emissionCalculationStatus, 'partial');
  assert.equal(invoice.calculationStatus, 'skipped');
  assert.equal(invoice.reviewRequired, true);
});

test('uploaded invoice adapter preserves complete calculation status', () => {
  const [invoice] = adaptUploadedInvoice({
    invoice_id: 'inv_complete',
    status: 'completed',
    result: {
      emission_calculation_status: 'complete',
      line_items: [
        {
          description: 'Electricity',
          category: 'electricity_grid',
          calculation_status: 'calculated',
          emission_calculation: {
            emissions: 71,
            emissions_unit: 'kg CO2',
            emissions_basis: 'CO2',
            factor_provenance: {
              geography: null,
              activity_boundary: null,
              method: null,
              rationale: 'No factor-specific source evidence.',
            },
            trust_metadata: {
              geography: null,
              library_default_geography: 'India',
              factor_verified: false,
            },
          },
        },
      ],
    },
  });

  assert.equal(invoice.emissionCalculationStatus, 'complete');
  assert.equal(invoice.calculationStatus, 'calculated');
  assert.equal(invoice.emissionFactorGeography, null);
  assert.equal(invoice.emissionFactorLibraryDefaultGeography, 'India');
  assert.equal(
    invoice.emissionFactorProvenance.rationale,
    'No factor-specific source evidence.',
  );
  assert.equal(invoice.emissionFactorVerified, false);
});
