import { Card } from '../components/common/Card';
import { DemoPill } from '../components/common/Badge';
import {
  UploadCloudIcon,
  RefreshCwIcon,
} from '../components/common/Icons';
import { InvoiceTable } from '../components/invoices/InvoiceTable';
import { formatEmissions } from '../utils/formatters';
import { useTrueScope } from '../context/TrueScopeContext';

export const InvoicesView = () => {
  const {
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
            <DemoPill label="DEMO REPOSITORY" />
            <span className="invoices-count-tag">{invoices.length} Documents Processed</span>
          </div>
          <h2 className="invoices-title">Invoices & Activity Data</h2>
          <p className="invoices-subtitle">
            Every business invoice is parsed into structured line items, classified into GHG emission activities,
            and assigned an emission factor.
          </p>
        </div>

        <div className="invoices-header-right">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={resetDemoData}
            title="Reset invoices back to initial demo data"
          >
            <RefreshCwIcon size={16} />
            <span>Reset Demo Data</span>
          </button>

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
          <span className="strip-label">Total Invoice Emissions</span>
          <strong className="strip-val">{formatEmissions(stats.totalEmissionsKg)}</strong>
        </div>
        <div className="summary-strip-divider" />
        <div className="summary-strip-item">
          <span className="strip-label">Scope 1 Total</span>
          <span className="strip-val s1">{formatEmissions(stats.scope1Kg)}</span>
        </div>
        <div className="summary-strip-divider" />
        <div className="summary-strip-item">
          <span className="strip-label">Scope 2 Total</span>
          <span className="strip-val s2">{formatEmissions(stats.scope2Kg)}</span>
        </div>
        <div className="summary-strip-divider" />
        <div className="summary-strip-item">
          <span className="strip-label">Scope 3 Total</span>
          <span className="strip-val s3">{formatEmissions(stats.scope3Kg)}</span>
        </div>
        <div className="summary-strip-divider" />
        <div className="summary-strip-item">
          <span className="strip-label">Average Confidence</span>
          <span className="strip-val conf">{stats.averageConfidence}%</span>
        </div>
      </div>

      {/* Invoices Table with Search & Filtering */}
      <Card
        title="Extracted Invoice Register"
        subtitle="Click any row to inspect line item calculations, confidence breakdown, or test overrides"
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
