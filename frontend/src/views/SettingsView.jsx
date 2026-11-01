import { useState } from 'react';
import { Card } from '../components/common/Card';
import {
  RefreshCwIcon,
  TrashIcon,
  CheckCircleIcon,
} from '../components/common/Icons';
import { useTrueScope } from '../context/TrueScopeContext';

export const SettingsView = () => {
  const { company, setCompany, resetDemoData, deleteInvoice, invoices, deleteCompany, openCompanyModal } = useTrueScope();
  const [saveToast, setSaveToast] = useState(false);
  const [clearError, setClearError] = useState('');

  // Form local state
  const [formData, setFormData] = useState({
    name: company.name,
    industry: company.industry,
    size: company.size,
    location: company.location,
    reportingYear: company.reportingYear,
    baselineYear: company.baselineYear,
    emissionUnit: company.emissionUnit,
    netZeroTarget: company.netZeroTarget || '',
    employees: company.employees || '',
  });
  const thisYear = new Date().getFullYear();
  const yearOptions = Array.from({ length: 6 }, (_, index) => String(thisYear - index));
  const withCurrent = (value) => (yearOptions.includes(String(value)) ? yearOptions : [String(value), ...yearOptions]);

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = (e) => {
    e.preventDefault();
    const employees = Number(formData.employees) || 0;
    setCompany((prev) => ({
      ...prev,
      ...formData,
      employees,
      size: employees > 0
        ? `${employees < 10 ? 'Micro' : employees < 50 ? 'Small' : 'Medium'} enterprise (${employees} employees)`
        : prev.size,
    }));
    setSaveToast(true);
    setTimeout(() => setSaveToast(false), 3000);
  };

  // Allow tester to test empty state
  const handleClearAll = async () => {
    if (window.confirm(`Remove all invoices for ${company.name}? This cannot be undone${company.isSample ? ', but you can restore the sample invoices.' : '.'}`)) {
      setClearError('');
      try {
        await Promise.all(invoices.map((invoice) => deleteInvoice(invoice.id)));
      } catch (error) {
        setClearError(
          error instanceof Error ? error.message : 'Could not clear all invoices.',
        );
      }
    }
  };

  return (
    <div className="view-container settings-view">
      <div className="settings-header-card">
        <h2 className="settings-title">Company Settings</h2>
        <p className="settings-subtitle">
          Company profile, reporting years and the emission factor library used for your estimates.
        </p>
      </div>

      {saveToast && (
        <div className="download-toast">
          <CheckCircleIcon size={18} />
          <span>Settings saved successfully!</span>
        </div>
      )}
      {clearError && <div className="error-banner" role="alert">{clearError}</div>}

      <form onSubmit={handleSave} className="settings-form">
        {/* Organization Information */}
        <Card
          title="Company profile"
          subtitle="Shown on your carbon report and used for intensity benchmarks"
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
              <label className="form-label">Employees</label>
              <input
                type="number"
                min="1"
                className="form-input"
                value={formData.employees}
                onChange={(e) => handleChange('employees', e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Location</label>
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
          title="Reporting preferences"
          subtitle="Reporting period, baseline, target and units"
        >
          <div className="settings-grid">
            <div className="form-group">
              <label className="form-label">Active Reporting Year</label>
              <select
                className="form-select"
                value={formData.reportingYear}
                onChange={(e) => handleChange('reportingYear', e.target.value)}
              >
                {withCurrent(formData.reportingYear).map((year) => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Emissions Baseline Year</label>
              <select
                className="form-select"
                value={formData.baselineYear}
                onChange={(e) => handleChange('baselineYear', e.target.value)}
              >
                {withCurrent(formData.baselineYear).map((year) => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Emission factor library</label>
              <input
                type="text"
                className="form-input"
                value="TrueScope India Default Library · GHG Protocol method"
                readOnly
              />
            </div>

            <div className="form-group">
              <label className="form-label">Reduction target</label>
              <input
                type="text"
                className="form-input"
                value={formData.netZeroTarget}
                placeholder="e.g. Net zero by 2040"
                onChange={(e) => handleChange('netZeroTarget', e.target.value)}
              />
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

      {/* Workspace management */}
      <Card
        title="Companies & data"
        subtitle="Manage companies on this device and the invoices stored for the active company"
      >
        <div className="sandbox-actions-grid">
          <div className="sandbox-action-card">
            <div className="sandbox-info">
              <strong className="sandbox-action-title">Add another company</strong>
              <p className="sandbox-action-desc">
                Track a second business, a client or a supplier. Each company has its own invoices and reports.
              </p>
            </div>
            <button type="button" className="btn btn-secondary" onClick={() => openCompanyModal('create')}>
              <span>Add company</span>
            </button>
          </div>

          {company.isSample && (
            <div className="sandbox-action-card">
              <div className="sandbox-info">
                <strong className="sandbox-action-title">Restore sample invoices</strong>
                <p className="sandbox-action-desc">
                  Brings back the sample company's eight invoices across Scopes 1, 2 and 3.
                </p>
              </div>
              <button type="button" className="btn btn-secondary" onClick={resetDemoData}>
                <RefreshCwIcon size={16} />
                <span>Restore sample invoices</span>
              </button>
            </div>
          )}

          <div className="sandbox-action-card">
            <div className="sandbox-info">
              <strong className="sandbox-action-title">Remove all invoices</strong>
              <p className="sandbox-action-desc">
                Deletes every invoice stored for {company.name} so you can start fresh.
              </p>
            </div>
            <button type="button" className="btn btn-danger-ghost" onClick={handleClearAll}>
              <TrashIcon size={16} />
              <span>Remove invoices</span>
            </button>
          </div>

          {!company.isSample && (
            <div className="sandbox-action-card">
              <div className="sandbox-info">
                <strong className="sandbox-action-title">Delete this company</strong>
                <p className="sandbox-action-desc">
                  Permanently removes {company.name} and all of its invoices from this device.
                </p>
              </div>
              <button
                type="button"
                className="btn btn-danger-ghost"
                onClick={() => {
                  if (window.confirm(`Delete ${company.name} and all of its invoices?`)) deleteCompany(company.id);
                }}
              >
                <TrashIcon size={16} />
                <span>Delete company</span>
              </button>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};
