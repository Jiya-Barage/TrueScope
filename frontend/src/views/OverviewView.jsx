import { Card, MetricCard } from '../components/common/Card';
import { ScopeBadge } from '../components/common/Badge';
import {
  UploadCloudIcon,
  FileTextIcon,
  SparklesIcon,
  TrendingDownIcon,
  InfoIcon,
} from '../components/common/Icons';
import { MonthlyTrendChart } from '../components/charts/MonthlyTrendChart';
import { CategoryDonutChart } from '../components/charts/CategoryDonutChart';
import { InvoiceTable } from '../components/invoices/InvoiceTable';
import { formatEmissions } from '../utils/formatters';
import { useTrueScope } from '../context/TrueScopeContext';

export const OverviewView = () => {
  const {
    stats,
    monthlyTrends,
    invoices,
    backendLoadError,
    company,
    openUploadModal,
    setActiveScreen,
  } = useTrueScope();

  return (
    <div className="view-container overview-view">
      {backendLoadError && (
        <div className="error-banner" role="status">
          Saved backend invoices could not be restored. {backendLoadError}
        </div>
      )}
      {/* Top Welcome / Demo Banner */}
      <div className="overview-welcome-banner">
        <div className="welcome-banner-text">
          <div className="banner-tag-row">
            <span className="banner-facility-tag">
              {company.name} • {company.size}
            </span>
          </div>
          <h2 className="welcome-heading">SME Greenhouse Gas Overview</h2>
          <p className="welcome-desc">
            Uploaded invoice calculation results are shown separately from sample data.
            Review factor provenance and verification status before interpreting any estimate.
          </p>
        </div>

        <div className="welcome-banner-cta">
          <button
            type="button"
            className="btn btn-primary banner-upload-btn"
            onClick={openUploadModal}
          >
            <UploadCloudIcon size={18} />
            <span>Process New Invoice</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="kpi-grid">
        <MetricCard
          title="Uploaded CO₂e Results"
          value={formatEmissions(stats.totalEmissionsKg)}
          subvalue={`${(stats.totalEmissionsKg / 1000).toFixed(2)} metric tons CO₂e; excludes sample and ineligible rows`}
          trendLabel="Unverified estimates; review factor evidence"
          icon={TrendingDownIcon}
        />

        <MetricCard
          title="Scope 1 (Direct)"
          value={formatEmissions(stats.scope1Kg)}
          subvalue={`${stats.scope1Pct.toFixed(1)}% of footprint`}
          scopeColor="#d97706"
          trendLabel="Fleet fuel & gas heating"
          badge={<ScopeBadge scope="Scope 1" />}
        />

        <MetricCard
          title="Scope 2 (Electricity)"
          value={formatEmissions(stats.scope2Kg)}
          subvalue={`${stats.scope2Pct.toFixed(1)}% of footprint`}
          scopeColor="#0284c7"
          trendLabel="Purchased facility grid power"
          badge={<ScopeBadge scope="Scope 2" />}
        />

        <MetricCard
          title="Scope 3 (Value Chain)"
          value={formatEmissions(stats.scope3Kg)}
          subvalue={`${stats.scope3Pct.toFixed(1)}% of footprint`}
          scopeColor="#8b5cf6"
          trendLabel="Logistics, waste & materials"
          badge={<ScopeBadge scope="Scope 3" />}
        />

        <MetricCard
          title="Uploaded Invoices"
          value={`${stats.invoiceCount}`}
          subvalue={`Average extraction confidence: ${stats.averageConfidence}%`}
          icon={FileTextIcon}
          trendLabel={`${stats.skippedLineCount} uploaded line(s) skipped`}
        />
      </div>

      {/* Charts Row: Monthly Trend (left) + Category Breakdown (right) */}
      <div className="charts-split-grid">
        <Card
          title="Monthly Emissions Trend (kg CO₂e)"
          subtitle="Sample emissions trend; uploaded invoices are excluded"
          className="chart-card-trend"
        >
          <MonthlyTrendChart data={monthlyTrends} />
        </Card>

        <Card
          title="Emissions by Category"
          subtitle="Eligible uploaded CO₂e calculations only; sample records excluded"
          className="chart-card-category"
        >
          <CategoryDonutChart
            categories={stats.categoryBreakdown}
          />
        </Card>
      </div>

      {/* Recent Invoices Activity Section */}
      <Card
        title="Recent Invoice Activity"
        subtitle="Uploaded invoices and reference sample records"
        headerAction={
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => setActiveScreen('invoices')}
          >
            <span>View All ({invoices.length})</span>
            <SparklesIcon size={16} />
          </button>
        }
      >
        <InvoiceTable
          invoices={invoices}
          limit={5}
          showSearchAndFilters={false}
          emptyMessage="No invoices uploaded yet."
        />
      </Card>

      {/* Bottom Methodology & Limitations Note */}
      <div className="overview-methodology-note">
        <div className="methodology-icon">
          <InfoIcon size={18} />
        </div>
        <div className="methodology-text">
          <strong>Calculation Basis & Limitations:</strong>
          <span>
            Activity quantity × emission factor produces emissions in that factor's reported basis and unit; CO₂ is not treated as CO₂e.
            Sample values are excluded from uploaded totals. Uploaded CO₂-only, skipped, failed, or otherwise ineligible rows are excluded from CO₂e totals; uploaded factor values remain unverified unless evidence is established.
          </span>
        </div>
      </div>
    </div>
  );
};
