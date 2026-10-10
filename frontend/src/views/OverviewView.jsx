import { Card, MetricCard } from '../components/common/Card';
import { ScopeBadge, DemoPill } from '../components/common/Badge';
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
    company,
    openUploadModal,
    setActiveScreen,
  } = useTrueScope();

  return (
    <div className="view-container overview-view">
      {/* Top Welcome / Demo Banner */}
      <div className="overview-welcome-banner">
        <div className="welcome-banner-text">
          <div className="banner-tag-row">
            <DemoPill label="DEMO ENVIRONMENT" />
            <span className="banner-facility-tag">
              {company.name} • {company.size}
            </span>
          </div>
          <h2 className="welcome-heading">SME Greenhouse Gas Overview</h2>
          <p className="welcome-desc">
            Aggregated carbon footprint calculated from supplier invoices and utility meters.
            Classified per the Greenhouse Gas Protocol Corporate Standard.
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
          title="Total Estimated Emissions"
          value={formatEmissions(stats.totalEmissionsKg)}
          subvalue={`${(stats.totalEmissionsKg / 1000).toFixed(2)} metric tons CO₂e`}
          trend="-4.2%"
          trendLabel="vs last month"
          icon={TrendingDownIcon}
          badge={<DemoPill label="ESTIMATE" />}
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
          title="Processed Invoices"
          value={`${stats.invoiceCount}`}
          subvalue={`Avg Confidence: ${stats.averageConfidence}%`}
          icon={FileTextIcon}
          trendLabel="100% matched to factors"
        />
      </div>

      {/* Charts Row: Monthly Trend (left) + Category Breakdown (right) */}
      <div className="charts-split-grid">
        <Card
          title="Monthly Emissions Trend (kg CO₂e)"
          subtitle="Historical and current month emissions split by Scope 1, 2, and 3"
          className="chart-card-trend"
        >
          <MonthlyTrendChart data={monthlyTrends} />
        </Card>

        <Card
          title="Emissions by Category"
          subtitle="Relative contribution of SME activities to total footprint"
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
        subtitle="Latest vendor invoices processed by TrueScope OCR and classification"
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

      {/* Bottom Methodology & Hackathon Note */}
      <div className="overview-methodology-note">
        <div className="methodology-icon">
          <InfoIcon size={18} />
        </div>
        <div className="methodology-text">
          <strong>GHG Protocol Alignment & Demo Factor Notice:</strong>
          <span>
            TrueScope applies activity-based emission modeling: <code>Activity Quantity × Emission Factor = kg CO₂e</code>.
            In this prototype MVP, calculations use simulated mock factors for demonstration and hackathon evaluation.
          </span>
        </div>
      </div>
    </div>
  );
};
