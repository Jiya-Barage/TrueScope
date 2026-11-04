import { Card } from '../components/common/Card';
import {
  UploadCloudIcon,
  RefreshCwIcon,
} from '../components/common/Icons';
import { InvoiceTable } from '../components/invoices/InvoiceTable';
import { formatEmissions } from '../utils/formatters';
import { useTrueScope } from '../context/TrueScopeContext';

export const InvoicesView = () => {
  const {
    isSampleCompany,
    invoices,
    stats,
    openUploadModal,
    resetDemoData,
  } = useTrueScope();

  return (
    <div className="view-container invoices-view">
      {/* Top Header Card */}
      <div className="invoices-header-card">
        <div className="invoices-header-left">
          <div className="invoices-header-tag">
            <span className="invoices-count-tag">{stats.invoiceCount} invoice(s)</span>
          </div>
          <h2 className="invoices-title">Invoices & Activity Data</h2>
          <p className="invoices-subtitle">
            Every extracted line item with its activity data, emission factor and confidence. Lines that need a closer look are flagged for review instead of being guessed.
          </p>
        </div>

        <div className="invoices-header-right">
          {isSampleCompany && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={resetDemoData}
              title="Restore the sample company's invoices"
            >
              <RefreshCwIcon size={16} />
              <span>Restore sample invoices</span>
            </button>
          )}

          <button
            type="button"
            className="btn btn-primary"
            onClick={openUploadModal}
          >
            <UploadCloudIcon size={18} />
            <span>Upload New Invoice</span>
          </button>
        </div>
      </div>

      {/* Mini Stats Bar */}
      <div className="invoices-summary-strip">
        <div className="summary-strip-item">
          <span className="strip-label">Total footprint</span>
          <strong className="strip-val">{formatEmissions(stats.totalEmissionsKg)}</strong>
        </div>
        <div className="summary-strip-divider" />
        <div className="summary-strip-item">
          <span className="strip-label">Scope 1</span>
          <span className="strip-val s1">{formatEmissions(stats.scope1Kg)}</span>
        </div>
        <div className="summary-strip-divider" />
        <div className="summary-strip-item">
          <span className="strip-label">Scope 2</span>
          <span className="strip-val s2">{formatEmissions(stats.scope2Kg)}</span>
        </div>
        <div className="summary-strip-divider" />
        <div className="summary-strip-item">
          <span className="strip-label">Scope 3</span>
          <span className="strip-val s3">{formatEmissions(stats.scope3Kg)}</span>
        </div>
        <div className="summary-strip-divider" />
        <div className="summary-strip-item">
          <span className="strip-label">Average extraction confidence</span>
          <span className="strip-val conf">{stats.averageConfidence}%</span>
        </div>
        <p className="invoices-subtitle">
          Totals include every line with a compatible quantity and unit. Grid electricity uses a CO₂-basis factor. Lines awaiting review are not included until resolved.
        </p>
      </div>

      {/* Invoices Table with Search & Filtering */}
      <Card
        title="Invoice register"
        subtitle="Click any row to inspect the calculation, factor source and confidence"
      >
        <InvoiceTable
          invoices={invoices}
          showSearchAndFilters={true}
          emptyMessage="No invoices match your search filters."
        />
      </Card>
    </div>
  );
};
