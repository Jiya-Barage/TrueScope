import { useState } from 'react';
import { Modal } from '../common/Modal';
import { ScopeBadge, ConfidenceBadge } from '../common/Badge';
import {
  FileTextIcon,
  SparklesIcon,
  CheckCircleIcon,
  TrashIcon,
} from '../common/Icons';
import {
  formatEmissionValue,
  formatEmissions,
  formatCurrency,
  formatDate,
} from '../../utils/formatters';
import { useTrueScope } from '../../context/TrueScopeContext';

export const InvoiceDetailModal = () => {
  const {
    isDetailModalOpen,
    closeInvoiceDetail,
    selectedInvoice,
    updateInvoice,
    deleteInvoice,
  } = useTrueScope();

  // Local editable fields to test override
  const [editableQuantity, setEditableQuantity] = useState(0);
  const [editableFactor, setEditableFactor] = useState(0);
  const [isEditing, setIsEditing] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  if (!selectedInvoice) return null;
  const isBackendUpload = Boolean(selectedInvoice.isBackendUpload);

  const handleStartEditing = () => {
    if (isBackendUpload) return;
    setEditableQuantity(selectedInvoice.quantity || 0);
    setEditableFactor(selectedInvoice.emissionFactor || 0);
    setIsEditing(true);
  };

  const handleCancelEditing = () => {
    setIsEditing(false);
  };

  const handleClose = () => {
    setIsEditing(false);
    closeInvoiceDetail();
  };

  const currentQuantity = isEditing
    ? Number(editableQuantity) || 0
    : Number(selectedInvoice.quantity) || 0;
  const currentFactor = isEditing
    ? Number(editableFactor) || 0
    : Number(selectedInvoice.emissionFactor) || 0;
  const recalculatedEmissions = Math.round(currentQuantity * currentFactor);

  const handleSaveOverride = () => {
    const updated = {
      ...selectedInvoice,
      quantity: currentQuantity,
      emissionFactor: currentFactor,
      calculatedEmissionsKg: recalculatedEmissions,
    };
    updateInvoice(updated);
    setIsEditing(false);
  };

  const handleDelete = async () => {
    if (window.confirm(`Delete ${selectedInvoice.invoiceNumber}?`)) {
      setDeleteError('');
      try {
        await deleteInvoice(selectedInvoice.id);
      } catch (error) {
        setDeleteError(
          error instanceof Error ? error.message : 'Could not delete this invoice.',
        );
      }
    }
  };

  return (
    <Modal
      isOpen={isDetailModalOpen}
      onClose={handleClose}
      title="Invoice Extraction & Emission Results"
      subtitle={isBackendUpload
        ? `Processed details for ${selectedInvoice.invoiceNumber || selectedInvoice.backendInvoiceId}`
        : `Verified details for ${selectedInvoice.invoiceNumber}`}
      maxWidth="720px"
      footer={
        <div className="detail-modal-footer">
          <button
            type="button"
            className="btn btn-danger-ghost"
            onClick={handleDelete}
            title="Delete this invoice"
          >
            <TrashIcon size={16} />
            <span>Remove Invoice</span>
          </button>

          <div className="detail-footer-right">
            {isEditing ? (
              <>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleCancelEditing}
                >
                  Cancel Edit
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleSaveOverride}
                >
                  Save Override
                </button>
              </>
            ) : (
              <>
                {!isBackendUpload && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleStartEditing}
                  >
                    Edit / Override Values
                  </button>
                )}
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleClose}
                >
                  Done
                </button>
              </>
            )}
          </div>
        </div>
      }
    >
      <div className="invoice-detail-content">
        {deleteError && <div className="error-banner" role="alert">{deleteError}</div>}
        {/* Top Summary Banner */}
        <div className="detail-hero-card">
          <div className="detail-hero-top">
            <div className="detail-hero-meta">
              <span className="detail-inv-number">
                {selectedInvoice.invoiceNumber || selectedInvoice.backendInvoiceId || selectedInvoice.id}
              </span>
              <span className="detail-supplier">
                {selectedInvoice.supplier || (isBackendUpload ? 'Supplier not identified' : '')}
              </span>
            </div>
            <div className="detail-hero-badges">
              <ScopeBadge scope={selectedInvoice.scope} />
              <ConfidenceBadge
                confidence={selectedInvoice.confidence}
                confidenceFlag={isBackendUpload ? selectedInvoice.confidenceFlag : undefined}
              />
            </div>
          </div>

          <div className="detail-emission-kpi">
            <span className="kpi-label">Estimated Carbon Impact</span>
            <span className="kpi-value">
              {isBackendUpload
                ? formatEmissionValue(selectedInvoice.emissionsValue, selectedInvoice.emissionsUnit)
                : formatEmissions(isEditing ? recalculatedEmissions : selectedInvoice.calculatedEmissionsKg)}
            </span>
            <span className="kpi-sub">
              {isBackendUpload
                ? selectedInvoice.emissionCalculation?.calculation ||
                  selectedInvoice.calculationReason ||
                  'No engine calculation is available.'
                : `Formula: ${currentQuantity.toLocaleString()} ${selectedInvoice.unit || ''} × ${currentFactor} ${selectedInvoice.emissionFactorUnit || ''}`}
            </span>
          </div>
        </div>

        {/* Extracted Activity Details Grid */}
        <div className="detail-section">
          <h4 className="detail-section-title">
            <SparklesIcon size={16} />
            <span>Extracted Activity Breakdown</span>
          </h4>

          <div className="detail-grid">
            <div className="detail-field-card">
              <span className="field-label">Extracted Line Item</span>
              <strong className="field-val">{selectedInvoice.itemDescription}</strong>
            </div>

            <div className="detail-field-card">
              <span className="field-label">Activity Category</span>
              <strong className="field-val highlight-cat">
                {selectedInvoice.activityCategory}
              </strong>
            </div>

            <div className="detail-field-card">
              <span className="field-label">Quantity & Unit</span>
              {isEditing ? (
                <div className="inline-edit-group">
                  <input
                    type="number"
                    className="inline-input"
                    value={editableQuantity}
                    onChange={(e) => setEditableQuantity(e.target.value)}
                  />
                  <span className="unit-label">{selectedInvoice.unit}</span>
                </div>
              ) : (
                <strong className="field-val">
                  {selectedInvoice.quantity == null
                    ? 'Not provided'
                    : `${Number(selectedInvoice.quantity).toLocaleString()} ${selectedInvoice.unit || ''}`}
                </strong>
              )}
            </div>

            <div className="detail-field-card">
              <span className="field-label">GHG Protocol Scope</span>
              <strong className="field-val">{selectedInvoice.scope || 'Unclassified'}</strong>
            </div>

            <div className="detail-field-card">
              <span className="field-label">Emission Factor</span>
              {isBackendUpload ? (
                <div>
                  <strong className="field-val">
                    {selectedInvoice.emissionFactor == null
                      ? 'Not available'
                      : `${selectedInvoice.emissionFactor} ${selectedInvoice.emissionFactorUnit || ''}`}
                  </strong>
                  {selectedInvoice.emissionFactorNote && (
                    <span className="factor-note-pill">
                      {selectedInvoice.emissionFactorNote}
                    </span>
                  )}
                  {selectedInvoice.emissionCalculation && (
                    <span className="factor-note-pill">
                      {selectedInvoice.emissionFactorVerified
                        ? 'Verified'
                        : 'Unverified — review required'}
                    </span>
                  )}
                  {selectedInvoice.emissionFactorGeography && (
                    <span className="factor-note-pill">
                      Geography: {selectedInvoice.emissionFactorGeography}
                    </span>
                  )}
                  {!selectedInvoice.emissionFactorGeography && (
                    <span className="factor-note-pill">
                      Geography not established
                      {selectedInvoice.emissionFactorLibraryDefaultGeography
                        ? ` (library default: ${selectedInvoice.emissionFactorLibraryDefaultGeography})`
                        : ''}
                    </span>
                  )}
                  {selectedInvoice.emissionFactorSource && (
                    <span className="factor-note-pill">
                      Source: {selectedInvoice.emissionFactorSource}
                      {selectedInvoice.emissionFactorSourceYear
                        ? ` (${selectedInvoice.emissionFactorSourceYear})`
                        : ''}
                    </span>
                  )}
                  {selectedInvoice.emissionFactorProvenance && (
                    <span className="factor-note-pill">
                      Activity boundary:{' '}
                      {selectedInvoice.emissionFactorProvenance.activity_boundary ||
                        'Not documented'}
                    </span>
                  )}
                  {selectedInvoice.emissionFactorProvenance && (
                    <span className="factor-note-pill">
                      Method:{' '}
                      {selectedInvoice.emissionFactorProvenance.method ||
                        'Not documented'}
                    </span>
                  )}
                  {selectedInvoice.emissionFactorProvenance?.rationale && (
                    <span className="factor-note-pill">
                      Provenance limitation:{' '}
                      {selectedInvoice.emissionFactorProvenance.rationale}
                    </span>
                  )}
                </div>
              ) : isEditing ? (
                <div className="inline-edit-group">
                  <input
                    type="number"
                    step="0.001"
                    className="inline-input"
                    value={editableFactor}
                    onChange={(e) => setEditableFactor(e.target.value)}
                  />
                  <span className="unit-label">{selectedInvoice.emissionFactorUnit}</span>
                </div>
              ) : (
                <div>
                  <strong className="field-val">
                    {selectedInvoice.emissionFactor} {selectedInvoice.emissionFactorUnit}
                  </strong>
                  <span className="factor-note-pill">
                    {selectedInvoice.emissionFactorNote || 'Demo Mock Factor - Unverified'}
                  </span>
                </div>
              )}
            </div>

            <div className="detail-field-card">
              <span className="field-label">AI Extraction Confidence</span>
              <div className="conf-bar-group">
                <strong className="field-val">
                  {selectedInvoice.confidence == null ? 'Not available' : `${selectedInvoice.confidence}%`}
                </strong>
                <span className="conf-status-text">
                  {selectedInvoice.confidenceFlag
                    ? `${selectedInvoice.confidenceFlag} confidence classification`
                    : selectedInvoice.confidence == null
                      ? 'Confidence unavailable'
                      : selectedInvoice.confidence >= 90
                        ? 'High confidence classification'
                        : 'Standard confidence match'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Document Metadata (OCR parsed) */}
        <div className="detail-section">
          <h4 className="detail-section-title">
            <FileTextIcon size={16} />
            <span>Document & Billing Metadata</span>
          </h4>

          <div className="metadata-table-card">
            {isBackendUpload && (
              <>
                <div className="meta-row">
                  <span className="meta-name">Invoice emission calculations</span>
                  <span className="meta-value">
                    {selectedInvoice.emissionCalculationStatus === 'partial'
                      ? 'Partial — review required'
                      : selectedInvoice.emissionCalculationStatus === 'complete'
                        ? 'Complete'
                        : selectedInvoice.emissionCalculationStatus === 'not_applicable'
                          ? 'Not applicable'
                          : 'Unavailable'}
                  </span>
                </div>
                <div className="meta-row">
                  <span className="meta-name">This line calculation</span>
                  <span className="meta-value">
                    {selectedInvoice.calculationStatus === 'calculated'
                      ? 'Calculated'
                      : selectedInvoice.calculationStatus === 'not_applicable'
                        ? 'Not applicable'
                        : 'Skipped'}
                  </span>
                </div>
              </>
            )}
            <div className="meta-row">
              <span className="meta-name">Invoice Date</span>
              <span className="meta-value">{formatDate(selectedInvoice.date)}</span>
            </div>
            <div className="meta-row">
              <span className="meta-name">Billing Period</span>
              <span className="meta-value">{selectedInvoice.billingPeriod || 'N/A'}</span>
            </div>
            <div className="meta-row">
              <span className="meta-name">Total Invoiced Amount</span>
              <span className="meta-value">
                {selectedInvoice.totalAmount == null
                  ? 'Not provided by invoice extraction'
                  : formatCurrency(selectedInvoice.totalAmount, selectedInvoice.currency)}
              </span>
            </div>
            <div className="meta-row">
              <span className="meta-name">Status</span>
              <span className="meta-value status-done">
                <CheckCircleIcon size={14} />
                <span>{selectedInvoice.status || 'Processed'}</span>
              </span>
            </div>
          </div>
        </div>

        {isBackendUpload && selectedInvoice.reviewRequired && (
          <div className="detail-section">
            <h4 className="detail-section-title">Review required</h4>
            <ul>
              {selectedInvoice.reviewReasons.map((reason, index) => (
                <li key={`${selectedInvoice.id}-review-${index}`}>{reason}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Methodology notice */}
        <div className="detail-disclaimer">
          <span className="disclaimer-bullet">•</span>
          <span>
            {isBackendUpload ? (
              <>
                <strong>Backend result:</strong> Emission value and unit are shown as returned by the engine. Confidence is a heuristic score, and review flags remain applicable.
              </>
            ) : (
              <>
                <strong>Demo Calculation:</strong> All greenhouse gas calculations are based on mock emission factors. In production, factors map to certified DEFRA, EPA GHG Hub, or regional grid APIs with full audit logs.
              </>
            )}
          </span>
        </div>
      </div>
    </Modal>
  );
};
