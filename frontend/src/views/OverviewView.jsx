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
    isSampleCompany,
    openUploadModal,
    setActiveScreen,
  } = useTrueScope();
  const hasData = invoices.length > 0;

  return (
    <div className="view-container overview-view">
      {backendLoadError && (
        <div className="error-banner" role="status">
          Saved backend invoices could not be restored. {backendLoadError}
        </div>
      )}
      {/* Top Welcome Banner */}
      <div className="overview-welcome-banner">
        <div className="welcome-banner-text">
          <div className="banner-tag-row">
            <span className="banner-facility-tag">
              {company.name} • {company.isSample ? 'Sample company' : company.size}
            </span>
          </div>
          <h2 className="welcome-heading">
            {hasData ? `${company.name}: carbon footprint` : `Welcome, ${company.name}`}
          </h2>
          <p className="welcome-desc">
            {hasData
              ? 'Your emissions across Scopes 1, 2 and 3, built directly from your invoices. Open any line to see the factor, source and confidence behind it.'
              : 'Upload your first invoice and TrueScope will extract the activity data and estimate your Scope 1, 2 and 3 emissions in seconds.'}
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
          title="Total Footprint"
          value={formatEmissions(stats.totalEmissionsKg)}
          subvalue={`${(stats.totalEmissionsKg / 1000).toFixed(2)} metric tons CO₂e`}
          trendLabel="Estimated from your invoices"
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
          title="Invoices Processed"
          value={`${stats.invoiceCount}`}
          subvalue={isSampleCompany ? 'Sample invoices across all scopes' : `Average extraction confidence: ${stats.averageConfidence}%`}
          icon={FileTextIcon}
          trendLabel={stats.skippedLineCount > 0 ? `${stats.skippedLineCount} line(s) flagged for review` : 'All lines estimated'}
        />
      </div>

      {!hasData && (
        <div className="empty-hero">
          <h3>No invoices yet for {company.name}</h3>
          <p>
            Upload an electricity bill, a fuel receipt or a freight invoice. You will see your footprint by
            scope, by category and by month here, and a report you can share with buyers.
          </p>
          <div className="empty-hero-actions">
            <button type="button" className="btn btn-primary" onClick={openUploadModal}>
              <UploadCloudIcon size={18} />
              <span>Upload your first invoice</span>
            </button>
          </div>
        </div>
      )}

      {/* Charts Row: Monthly Trend (left) + Category Breakdown (right) */}
      {hasData && (
        <div className="charts-split-grid">
          <Card
            title="Monthly Emissions Trend (kg CO₂e)"
            subtitle={isSampleCompany ? 'Sample company history' : 'Built from your invoice dates'}
            className="chart-card-trend"
          >
            <MonthlyTrendChart data={monthlyTrends} isSample={isSampleCompany} />
          </Card>

          <Card
            title="Emissions by Category"
            subtitle="Where your footprint comes from"
            className="chart-card-category"
          >
            <CategoryDonutChart categories={stats.categoryBreakdown} />
          </Card>
        </div>
      )}

      {/* Recent Invoices Activity Section */}
      {hasData && (
      <Card
        title="Recent Invoice Activity"
        subtitle="Latest invoices and the emissions estimated from them"
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
      )}

      {/* Bottom Methodology Note */}
      <div className="overview-methodology-note">
        <div className="methodology-icon">
          <InfoIcon size={18} />
        </div>
        <div className="methodology-text">
          <strong>How we calculate:</strong>
          <span>
            Emissions = activity quantity × emission factor, following the GHG Protocol Corporate Standard.
            Grid electricity uses a CO₂-basis factor (CH₄ and N₂O not included). Lines without a
            compatible quantity and unit are flagged for review rather than guessed.
            {stats.skippedLineCount > 0 ? ` ${stats.skippedLineCount} line(s) currently await review.` : ''}
          </span>
        </div>
      </div>
    </div>
  );
};
