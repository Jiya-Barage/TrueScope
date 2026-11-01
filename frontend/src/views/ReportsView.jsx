import { useState } from 'react';
import { ScopeBadge } from '../components/common/Badge';
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
  const { invoices, stats, company, isSampleCompany } = useTrueScope();
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  const handleDownloadCSV = () => {
    const csvData = generateEmissionsCSV(invoices, {
      name: company.name,
      reportingPeriod: 'All available records',
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
            <span className="reports-status-tag">Carbon report</span>
          </div>
          <h2 className="reports-title">Carbon Footprint Report & Data Export</h2>
          <p className="reports-subtitle">
            A buyer-ready summary of your Scope 1, 2 and 3 emissions, with the method and data quality stated. Print it as a PDF or download the line-by-line CSV.
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

      {/* Report document */}
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
              <strong className="meta-val">GHG Emissions Inventory Summary</strong>
            </div>
            <div className="paper-meta-row">
              <span className="meta-label">Reporting Period:</span>
              <span className="meta-val">All invoices on record</span>
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
              <span className="boundary-val">{company.employees ? `${company.employees} employees` : 'Not specified'}</span>
            </div>
            <div className="boundary-item">
              <span className="boundary-lbl">Scope basis:</span>
              <span className="boundary-val">GHG Protocol Corporate Standard; activity-based method</span>
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
                <td>Fuel combustion in owned vehicles and equipment, heating</td>
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
                <td>Purchased grid electricity</td>
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
                <td>Freight, waste, travel and purchased goods</td>
                <td>{formatNumber(stats.scope3Kg)} kg</td>
                <td>{(stats.scope3Kg / 1000).toFixed(2)} t</td>
                <td>{stats.scope3Pct.toFixed(1)}%</td>
              </tr>
              <tr className="paper-table-total-row">
                <td colSpan="2">
                  <strong>Total estimated footprint</strong>
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
              {isSampleCompany && (
              <tr>
                <td colSpan="2">
                  <strong>Sample company records included above</strong>
                </td>
                <td>{formatNumber(stats.demoTotalEmissionsKg)} kg</td>
                <td>{(stats.demoTotalEmissionsKg / 1000).toFixed(2)} t</td>
                <td>—</td>
              </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Section 3: Calculation coverage */}
        <div className="report-paper-section">
          <h3 className="section-title">3. Data Quality & Coverage</h3>
          <div className="intensity-grid">
            <div className="intensity-card">
              <span className="intensity-label">Lines awaiting review</span>
              <strong className="intensity-val">{stats.ineligibleLineCount}</strong>
              <span className="intensity-sub">Unsupported quantity or unit; never estimated from price</span>
            </div>
            <div className="intensity-card">
              <span className="intensity-label">Lines on a CO₂ basis</span>
              <strong className="intensity-val">{stats.co2OnlyLineCount}</strong>
              <span className="intensity-sub">e.g. grid electricity; CH₄ and N₂O not included</span>
            </div>
            <div className="intensity-card">
              <span className="intensity-label">Lines using indicative factors</span>
              <strong className="intensity-val">{stats.unverifiedCalculationCount}</strong>
              <span className="intensity-sub">Factor and source are listed on every line</span>
            </div>
            {isSampleCompany && (
            <div className="intensity-card">
              <span className="intensity-label">Sample records</span>
              <strong className="intensity-val">{stats.demoRowCount}</strong>
              <span className="intensity-sub">Pre-loaded for the sample company</span>
            </div>
            )}
          </div>
        </div>

        {/* Section 4: Limitations */}
        <div className="report-paper-section">
          <h3 className="section-title">4. Notes on Method</h3>
          <p>
            Emissions are calculated as activity quantity × emission factor. Where an invoice line has no compatible quantity and unit (for example a trip count for freight), it is flagged for review rather than estimated from price. Review each line's factor and source before external disclosure.
          </p>
        </div>

        {/* Section 5: Notice & Audit Disclaimer */}
        <div className="report-paper-footer">
          <div className="footer-disclaimer-box">
            <strong>Methodology & Disclaimer</strong>
            <p>
              This document was generated by TrueScope. Factors come from the TrueScope India default library and are indicative; confirm them against your reporting year and geography before external disclosure. This summary supports management accounting and supplier questionnaires and is not a certified regulatory filing (e.g. BRSR, CSRD or ISO 14064-1).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
