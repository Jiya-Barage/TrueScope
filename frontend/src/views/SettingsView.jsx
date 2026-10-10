import { useState } from 'react';
import { Card } from '../components/common/Card';
import { DemoPill } from '../components/common/Badge';
import {
  RefreshCwIcon,
  TrashIcon,
  CheckCircleIcon,
} from '../components/common/Icons';
import { useTrueScope } from '../context/TrueScopeContext';

export const SettingsView = () => {
  const { company, setCompany, resetDemoData, deleteInvoice, invoices } = useTrueScope();
  const [saveToast, setSaveToast] = useState(false);

  // Form local state
  const [formData, setFormData] = useState({
    name: company.name,
    industry: company.industry,
    size: company.size,
    location: company.location,
    reportingYear: company.reportingYear,
    baselineYear: company.baselineYear,
    emissionUnit: company.emissionUnit,
    factorDatabase: company.factorDatabase,
  });

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = (e) => {
    e.preventDefault();
    setCompany((prev) => ({ ...prev, ...formData }));
    setSaveToast(true);
    setTimeout(() => setSaveToast(false), 3000);
  };

  // Allow tester to test empty state
  const handleClearAll = () => {
    if (window.confirm('Clear all invoices to test empty state? You can restore them anytime.')) {
      invoices.forEach((inv) => deleteInvoice(inv.id));
    }
  };

  return (
    <div className="view-container settings-view">
      <div className="settings-header-card">
        <div className="settings-header-tag">
          <DemoPill label="SME CONFIGURATION" />
        </div>
        <h2 className="settings-title">Organization Settings & Emission Parameters</h2>
        <p className="settings-subtitle">
          Configure SME profile attributes, reporting boundaries, and default emission factor libraries.
        </p>
      </div>

      {saveToast && (
        <div className="download-toast">
          <CheckCircleIcon size={18} />
          <span>Settings saved successfully!</span>
        </div>
      )}

      <form onSubmit={handleSave} className="settings-form">
        {/* Organization Information */}
        <Card
          title="Organization Profile"
          subtitle="Details used in GHG audit reports and employee carbon intensity benchmarks"
        >
          <div className="settings-grid">
            <div className="form-group">
              <label className="form-label">Company Name</label>
              <input
                type="text"
                className="form-input"
                value={formData.name}
                onChange={(e) => handleChange('name', e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Industry Classification</label>
              <input
                type="text"
                className="form-input"
                value={formData.industry}
                onChange={(e) => handleChange('industry', e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Organization Size</label>
              <input
                type="text"
                className="form-input"
                value={formData.size}
                onChange={(e) => handleChange('size', e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Primary Operating Hub</label>
              <input
                type="text"
                className="form-input"
                value={formData.location}
                onChange={(e) => handleChange('location', e.target.value)}
              />
            </div>
          </div>
        </Card>

        {/* GHG Protocol Parameters */}
        <Card
          title="Carbon Accounting Preferences"
          subtitle="Define baseline periods and emission factor datasets"
        >
          <div className="settings-grid">
            <div className="form-group">
              <label className="form-label">Active Reporting Year</label>
              <select
                className="form-select"
                value={formData.reportingYear}
                onChange={(e) => handleChange('reportingYear', e.target.value)}
              >
                <option value="2024">2024 (Current Fiscal Year)</option>
                <option value="2023">2023</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Emissions Baseline Year</label>
              <select
                className="form-select"
                value={formData.baselineYear}
                onChange={(e) => handleChange('baselineYear', e.target.value)}
              >
                <option value="2023">2023 (Pledge Baseline)</option>
                <option value="2022">2022</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Emission Factor Source</label>
              <select
                className="form-select"
                value={formData.factorDatabase}
                onChange={(e) => handleChange('factorDatabase', e.target.value)}
              >
                <option value="Demo Mock Factors (Unverified)">Demo Mock Factors (Current Active)</option>
                <option value="UK DEFRA / DESNZ 2024 (Backend Roadmap)">UK DEFRA 2024 (Future API Integration)</option>
                <option value="US EPA GHG Hub 2024 (Backend Roadmap)">US EPA GHG Hub (Future API Integration)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Preferred Unit Display</label>
              <select
                className="form-select"
                value={formData.emissionUnit}
                onChange={(e) => handleChange('emissionUnit', e.target.value)}
              >
                <option value="kg">Kilograms CO₂e (kg CO₂e)</option>
                <option value="t">Metric Tonnes CO₂e (t CO₂e)</option>
              </select>
            </div>
          </div>

          <div className="form-actions-row">
            <button type="submit" className="btn btn-primary">
              Save Settings
            </button>
          </div>
        </Card>
      </form>

      {/* Demo Sandbox Management */}
      <Card
        title="Demo Sandbox & State Management"
        subtitle="Tools to test different states (empty state, reset sample data) during evaluation"
      >
        <div className="sandbox-actions-grid">
          <div className="sandbox-action-card">
            <div className="sandbox-info">
              <strong className="sandbox-action-title">Reset to Default Sample Invoices</strong>
              <p className="sandbox-action-desc">
                Restores the standard suite of 8 realistic SME invoices spanning Scopes 1, 2, and 3.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={resetDemoData}
            >
              <RefreshCwIcon size={16} />
              <span>Reset Data</span>
            </button>
          </div>

          <div className="sandbox-action-card">
            <div className="sandbox-info">
              <strong className="sandbox-action-title">Purge Invoices (Test Empty State)</strong>
              <p className="sandbox-action-desc">
                Clears all loaded invoices so you can inspect empty state screens and upload fresh test documents.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-danger-ghost"
              onClick={handleClearAll}
            >
              <TrashIcon size={16} />
              <span>Clear All</span>
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
};
