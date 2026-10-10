import { useState } from 'react';
import { ScopeBadge, DemoPill } from '../components/common/Badge';
import {
  DownloadIcon,
  CheckCircleIcon,
} from '../components/common/Icons';
import { formatEmissions, formatNumber, formatDate } from '../utils/formatters';
import { generateEmissionsCSV, downloadCSV } from '../utils/csvExporter';
import { useTrueScope } from '../context/TrueScopeContext';

export const ReportsView = () => {
  const { invoices, stats, company } = useTrueScope();
  const [downloadSuccess, setDownloadSuccess] = useState(false);
  const [reportPeriod, setReportPeriod] = useState('2024-YTD');

  const handleDownloadCSV = () => {
    const csvData = generateEmissionsCSV(invoices, {
      name: company.name,
      reportingPeriod: reportPeriod === '2024-YTD' ? '2024 YTD (Jan - Oct)' : 'Q3 2024',
    });

    const dateStr = new Date().toISOString().split('T')[0];
    const filename = `truescope-emissions-report-${company.name.toLowerCase().replace(/[^a-z0-9]/g, '-')}-${dateStr}.csv`;

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
            Generate audit-ready GHG Protocol summary reports for enterprise buyers, lenders, and sustainability disclosures.
          </p>
        </div>

        <div className="reports-actions-group">
          <select
            className="report-period-select"
            value={reportPeriod}
            onChange={(e) => setReportPeriod(e.target.value)}
          >
            <option value="2024-YTD">Reporting Period: 2024 YTD</option>
            <option value="2024-Q3">Reporting Period: Q3 2024</option>
            <option value="2024-Q2">Reporting Period: Q2 2024</option>
          </select>

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
          <span>Report CSV downloaded successfully! Contains all {invoices.length} extracted line items.</span>
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
              <span className="meta-val">{reportPeriod === '2024-YTD' ? 'Jan 01, 2024 - Oct 10, 2024' : 'Q3 2024'}</span>
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
              <span className="boundary-lbl">Standard:</span>
              <span className="boundary-val">GHG Protocol Corporate Standard (Operational Control)</span>
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
                <td>Fleet Diesel, Facility Natural Gas</td>
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
                <td>Facility Electric Power (Grid Average)</td>
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
                <td>Freight Shipping, Packaging, Travel, Waste</td>
                <td>{formatNumber(stats.scope3Kg)} kg</td>
                <td>{(stats.scope3Kg / 1000).toFixed(2)} t</td>
                <td>{stats.scope3Pct.toFixed(1)}%</td>
              </tr>
              <tr className="paper-table-total-row">
                <td colSpan="2">
                  <strong>Total Gross Estimated Emissions</strong>
                </td>
                <td>
                  <strong>{formatNumber(stats.totalEmissionsKg)} kg</strong>
                </td>
                <td>
                  <strong>{(stats.totalEmissionsKg / 1000).toFixed(2)} t</strong>
                </td>
                <td>
                  <strong>100.0%</strong>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Section 3: Intensity Metrics */}
        <div className="report-paper-section">
          <h3 className="section-title">3. SME Carbon Intensity Metrics</h3>
          <div className="intensity-grid">
            <div className="intensity-card">
              <span className="intensity-label">Per Employee</span>
              <strong className="intensity-val">
                {formatNumber(stats.totalEmissionsKg / 42, 1)} kg CO₂e
              </strong>
              <span className="intensity-sub">Based on 42 full-time staff</span>
            </div>
            <div className="intensity-card">
              <span className="intensity-label">Per Processed Invoice</span>
              <strong className="intensity-val">
                {formatNumber(stats.invoiceCount > 0 ? stats.totalEmissionsKg / stats.invoiceCount : 0, 0)} kg CO₂e
              </strong>
              <span className="intensity-sub">Across {stats.invoiceCount} invoices</span>
            </div>
            <div className="intensity-card">
              <span className="intensity-label">Avg AI Confidence</span>
              <strong className="intensity-val">{stats.averageConfidence}%</strong>
              <span className="intensity-sub">Automated OCR & Mapping</span>
            </div>
          </div>
        </div>

        {/* Section 4: Recommended SME Reductions */}
        <div className="report-paper-section">
          <h3 className="section-title">4. High-Impact Decarbonization Roadmap</h3>
          <div className="recommendations-list">
            <div className="rec-item">
              <div className="rec-num">1</div>
              <div className="rec-text">
                <strong>Transition Facility Power to Green Renewable Tariffs (Scope 2)</strong>
                <p>Purchased electricity represents {stats.scope2Pct.toFixed(1)}% of your footprint. Switching to certified renewable electricity eliminates up to {formatNumber(stats.scope2Kg)} kg CO₂e annually.</p>
              </div>
            </div>

            <div className="rec-item">
              <div className="rec-num">2</div>
              <div className="rec-text">
                <strong>Fleet Electrification & Route Optimization (Scope 1)</strong>
                <p>Delivery van diesel fuel contributes {formatEmissions(stats.scope1Kg)}. Phased transition to electric commercial vans will reduce direct transport emissions by 75%.</p>
              </div>
            </div>

            <div className="rec-item">
              <div className="rec-num">3</div>
              <div className="rec-text">
                <strong>Supplier Engagement for Packaging & Low-Carbon Freight (Scope 3)</strong>
                <p>Switching corrugated boxes to 100% post-consumer recycled fiber lowers packaging footprint by an estimated 32%.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Section 5: Notice & Audit Disclaimer */}
        <div className="report-paper-footer">
          <div className="footer-disclaimer-box">
            <strong>DEMONSTRATION PROTOTYPE NOTICE & DISCLAIMER</strong>
            <p>
              This document was generated locally by the TrueScope SME Carbon Accounting Frontend MVP.
              The emission factors, classifications, and carbon calculations contained herein are mock demonstration values
              intended solely for technical review and hackathon demonstration. They do not constitute certified regulatory
              filings (SEC, CSRD, or ISO 14064-1) without formal verification against certified factor databases and independent auditing.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
