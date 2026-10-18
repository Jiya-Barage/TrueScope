const isConfidenceScore = (value) =>
  typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1;

const isFiniteNumber = (value) =>
  typeof value === 'number' && Number.isFinite(value);

export function adaptUploadedInvoice(response) {
  const invoice = response?.result;
  if (
    response?.status !== 'completed' ||
    typeof response.invoice_id !== 'string' ||
    !Array.isArray(invoice?.line_items)
  ) {
    return [];
  }

  return invoice.line_items.map((line, index) => {
    const calculation =
      line.calculation_status === 'calculated' &&
      line.emission_calculation &&
      typeof line.emission_calculation === 'object'
        ? line.emission_calculation
        : null;
    const confidence = isConfidenceScore(line.confidence)
      ? line.confidence * 100
      : null;
    const confidenceFlag = ['high', 'medium', 'low'].includes(line.confidence_flag)
      ? line.confidence_flag
      : null;
    const scope = [1, 2, 3].includes(line.scope) ? `Scope ${line.scope}` : null;
    const emissionsValue = isFiniteNumber(calculation?.emissions)
      ? calculation.emissions
      : null;
    const emissionsUnit =
      typeof calculation?.emissions_unit === 'string'
        ? calculation.emissions_unit
        : null;
    const emissionsBasis =
      typeof calculation?.emissions_basis === 'string'
        ? calculation.emissions_basis
        : null;
    const calculatedEmissionsKg =
      emissionsBasis === 'CO2e' && emissionsUnit === 'kg CO2e'
        ? emissionsValue
        : null;

    return {
      id: `${response.invoice_id}:line:${index + 1}`,
      backendInvoiceId: response.invoice_id,
      backendLineNumber: index + 1,
      isBackendUpload: true,
      rawApiResponse: response,
      rawInvoiceResult: invoice,
      rawLineItem: line,
      invoiceNumber: invoice.invoice_number,
      supplier: invoice.vendor,
      date: invoice.invoice_date,
      billingPeriod: null,
      totalAmount: null,
      currency: invoice.currency,
      itemDescription: line.description,
      quantity: line.quantity,
      unit: line.unit,
      activityCategory: line.category,
      scope,
      confidence,
      confidenceFlag,
      confidenceLevel: confidenceFlag,
      emissionFactor: calculation?.emission_factor ?? null,
      emissionFactorUnit: calculation?.factor_unit ?? null,
      emissionFactorNote: calculation?.validation_status ?? null,
      emissionFactorSource: calculation?.factor_source ?? null,
      emissionFactorSourceYear: calculation?.source_year ?? null,
      calculatedEmissionsKg,
      emissionsValue,
      emissionsUnit,
      emissionsBasis,
      emissionCalculation: calculation,
      calculationStatus: line.calculation_status ?? 'skipped',
      calculationReason: line.calculation_reason ?? null,
      reviewRequired: Boolean(line.review_required),
      reviewReasons: Array.isArray(line.review_reasons) ? line.review_reasons : [],
      reasons: Array.isArray(line.reasons) ? line.reasons : [],
      processingStatus: invoice.processing_status ?? response.status,
      status: response.status === 'completed' ? 'Processed' : response.status,
      source: invoice.source ?? null,
    };
  });
}