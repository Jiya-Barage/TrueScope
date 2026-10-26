import { useState } from 'react';
import { ScopeBadge, DemoPill } from '../components/common/Badge';
import {
  DownloadIcon,
  CheckCircleIcon,
} from '../components/common/Icons';
import { formatNumber, formatDate } from '../utils/formatters';
import {
  createReportFilename,
  generateEmissionsCSV,
  downloadCSV,
} from '../utils/csvExporter';
import { useTrueScope } from '../context/TrueScopeContext';

export const ReportsView = () => {
  const { invoices, stats, company } = useTrueScope();
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  const handleDownloadCSV = () => {
    const csvData = generateEmissionsCSV(invoices, {
      name: company.name,
      reportingPeriod: 'All available demo and uploaded records',
    });

    const filename = createReportFilename(company.name);

    downloadCSV(csvData, filename);

    setDownloadSuccess(true);
    setTimeout(() => setDownloadSuccess(false), 4000);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="view-container reports-view">
      {/* Header Bar with Action Buttons */}
      <div className="reports-header-card">
        <div>
          <div className="reports-tag-row">
            <DemoPill label="DEMO REPORT PREVIEW" />
            <span className="reports-status-tag">Draft Audit Document</span>
          </div>
          <h2 className="reports-title">Carbon Footprint Reports & Data Export</h2>
          <p className="reports-subtitle">
            Uploaded invoice totals include eligible CO₂e calculations only. Synthetic demo values are shown separately; skipped and CO₂-only calculations are excluded and disclosed below.
          </p>
        </div>

        <div className="reports-actions-group">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handlePrint}
            title="Print or save as PDF via browser"
          >
            <span>Print / PDF</span>
          </button>

          <button
            type="button"
            className="btn btn-primary btn-download-csv"
            onClick={handleDownloadCSV}
          >
            <DownloadIcon size={18} />
            <span>Download CSV Report</span>
          </button>
        </div>
      </div>

      {downloadSuccess && (
        <div className="download-toast">
          <CheckCircleIcon size={18} />
          <span>Report CSV downloaded successfully! Contains all {invoices.length} available rows.</span>
        </div>
      )}

      {/* Mock Report Document Preview Paper */}
      <div className="report-paper">
        {/* Paper Header */}
        <div className="report-paper-header">
          <div className="paper-brand">
            <h2 className="paper-logo-text">TrueScope</h2>
            <span className="paper-tagline">AI-Powered SME Carbon Accounting Platform</span>
          </div>
          <div className="paper-meta-box">
            <div className="paper-meta-row">
              <span className="meta-label">Document:</span>
              <strong className="meta-val">GHG Inventory Disclosure (Draft)</strong>
            </div>
            <div className="paper-meta-row">
              <span className="meta-label">Reporting Period:</span>
              <span className="meta-val">All loaded records; no date filter</span>
            </div>
            <div className="paper-meta-row">
              <span className="meta-label">Generated:</span>
              <span className="meta-val">{formatDate(new Date().toISOString())}</span>
            </div>
          </div>
        </div>

        <div className="paper-divider" />

        {/* Section 1: Organization & Boundary */}
        <div className="report-paper-section">
          <h3 className="section-title">1. Organization & Operational Boundary</h3>
          <div className="boundary-grid">
            <div className="boundary-item">
              <span className="boundary-lbl">Reporting Entity:</span>
              <strong className="boundary-val">{company.name}</strong>
            </div>
            <div className="boundary-item">
              <span className="boundary-lbl">Industry Sector:</span>
              <span className="boundary-val">{company.industry}</span>
            </div>
            <div className="boundary-item">
              <span className="boundary-lbl">Headcount:</span>
              <span className="boundary-val">42 Full-Time Employees</span>
            </div>
            <div className="boundary-item">
              <span className="boundary-lbl">Scope basis:</span>
              <span className="boundary-val">Demo classifications; methodology not independently validated</span>
            </div>
          </div>
        </div>

        {/* Section 2: Executive Summary Table */}
        <div className="report-paper-section">
          <h3 className="section-title">2. Greenhouse Gas Inventory Summary</h3>
          <table className="paper-table">
            <thead>
              <tr>
                <th>Scope Classification</th>
                <th>Sources Included</th>
                <th>Emissions (kg CO₂e)</th>
                <th>Emissions (t CO₂e)</th>
                <th>Share (%)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <div className="scope-cell">
                    <ScopeBadge scope="Scope 1" />
                    <strong>Direct Emissions</strong>
                  </div>
                </td>
                <td>Eligible uploaded Scope 1 calculations only</td>
                <td>{formatNumber(stats.scope1Kg)} kg</td>
                <td>{(stats.scope1Kg / 1000).toFixed(2)} t</td>
                <td>{stats.scope1Pct.toFixed(1)}%</td>
              </tr>
              <tr>
                <td>
                  <div className="scope-cell">
                    <ScopeBadge scope="Scope 2" />
                    <strong>Indirect (Purchased Electricity)</strong>
                  </div>
                </td>
                <td>Eligible uploaded Scope 2 calculations only</td>
                <td>{formatNumber(stats.scope2Kg)} kg</td>
                <td>{(stats.scope2Kg / 1000).toFixed(2)} t</td>
                <td>{stats.scope2Pct.toFixed(1)}%</td>
              </tr>
              <tr>
                <td>
                  <div className="scope-cell">
                    <ScopeBadge scope="Scope 3" />
                    <strong>Value Chain Emissions</strong>
                  </div>
                </td>
                <td>Eligible uploaded Scope 3 calculations only</td>
                <td>{formatNumber(stats.scope3Kg)} kg</td>
                <td>{(stats.scope3Kg / 1000).toFixed(2)} t</td>
                <td>{stats.scope3Pct.toFixed(1)}%</td>
              </tr>
              <tr className="paper-table-total-row">
                <td colSpan="2">
                  <strong>Uploaded CO₂e subtotal</strong>
                </td>
                <td>
                  <strong>{formatNumber(stats.totalEmissionsKg)} kg</strong>
                </td>
                <td>
                  <strong>{(stats.totalEmissionsKg / 1000).toFixed(2)} t</strong>
                </td>
                <td>
                  <strong>{stats.totalEmissionsKg > 0 ? '100.0%' : '0.0%'}</strong>
                </td>
              </tr>
              <tr>
                <td colSpan="2">
                  <strong>Synthetic demo subtotal (excluded from uploaded totals)</strong>
                </td>
                <td>{formatNumber(stats.demoTotalEmissionsKg)} kg</td>
                <td>{(stats.demoTotalEmissionsKg / 1000).toFixed(2)} t</td>
                <td>—</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Section 3: Calculation coverage */}
        <div className="report-paper-section">
          <h3 className="section-title">3. Calculation Coverage & Trust</h3>
          <div className="intensity-grid">
            <div className="intensity-card">
              <span className="intensity-label">Uploaded rows excluded from totals</span>
              <strong className="intensity-val">{stats.ineligibleLineCount}</strong>
              <span className="intensity-sub">{stats.skippedLineCount} skipped; other rows were not eligible CO₂e calculations</span>
            </div>
            <div className="intensity-card">
              <span className="intensity-label">CO₂-only uploaded rows</span>
              <strong className="intensity-val">{stats.co2OnlyLineCount}</strong>
              <span className="intensity-sub">Kept distinct; not added to CO₂e totals</span>
            </div>
            <div className="intensity-card">
              <span className="intensity-label">Unverified uploaded calculations</span>
              <strong className="intensity-val">{stats.unverifiedCalculationCount}</strong>
              <span className="intensity-sub">Factor evidence remains a review item</span>
            </div>
            <div className="intensity-card">
              <span className="intensity-label">Predefined demo rows</span>
              <strong className="intensity-val">{stats.demoRowCount}</strong>
              <span className="intensity-sub">Synthetic values, not engine calculations</span>
            </div>
          </div>
        </div>

        {/* Section 4: Limitations */}
        <div className="report-paper-section">
          <h3 className="section-title">4. Review Before Use</h3>
          <p>
            The uploaded summary excludes synthetic demo rows, CO₂-only results, skipped or failed calculations, and rows without a compatible CO₂e result. The synthetic demo subtotal is displayed separately and is not an uploaded invoice result. Review each uploaded line item and its factor provenance; unsupported rows are not estimated from invoice price.
          </p>
        </div>

        {/* Section 5: Notice & Audit Disclaimer */}
        <div className="report-paper-footer">
          <div className="footer-disclaimer-box">
            <strong>DEMONSTRATION PROTOTYPE NOTICE & DISCLAIMER</strong>
            <p>
              This document was generated locally by the TrueScope SME Carbon Accounting Frontend MVP.
              Preloaded rows contain synthetic mock values. Uploaded rows use the local demo factor library where a category and unit match;
              those factors remain unverified and may be unsupported for the invoice geography or reporting year. This preview is not a certified
              regulatory filing (SEC, CSRD, or ISO 14064-1).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
