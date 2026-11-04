import { useState } from 'react';
import { Modal } from '../common/Modal';
import { useTrueScope } from '../../context/TrueScopeContext';

const INDUSTRIES = [
  'Manufacturing',
  'Textiles & Apparel',
  'Food & Beverage',
  'Logistics & Transport',
  'Retail & Wholesale',
  'IT & Professional Services',
  'Hospitality',
  'Construction & Real Estate',
  'Healthcare',
  'Education',
  'Agriculture',
  'Other',
];

const emptyForm = () => ({
  name: '',
  industry: INDUSTRIES[0],
  employees: '',
  location: '',
  reportingYear: String(new Date().getFullYear()),
  netZeroTarget: '',
});

export const CompanyModal = () => {
  const { isCompanyModalOpen, closeCompanyModal, addCompany, openUploadModal } = useTrueScope();
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState('');

  const set = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const handleClose = () => {
    setForm(emptyForm());
    setError('');
    closeCompanyModal();
  };

  const handleSubmit = (event, thenUpload = false) => {
    event.preventDefault();
    if (!form.name.trim()) {
      setError('Enter your company name to continue.');
      return;
    }
    const employees = Number(form.employees);
    if (form.employees !== '' && (!Number.isFinite(employees) || employees < 1)) {
      setError('Number of employees must be a positive number.');
      return;
    }
    addCompany(form);
    handleClose();
    if (thenUpload) setTimeout(openUploadModal, 150);
  };

  const years = Array.from({ length: 5 }, (_, index) => String(new Date().getFullYear() - index));

  return (
    <Modal
      isOpen={isCompanyModalOpen}
      onClose={handleClose}
      title="Add your company"
      subtitle="Each company gets its own invoices, dashboard and reports."
      maxWidth="640px"
      footer={
        <div className="upload-modal-footer">
          <div className="simulation-notice-text">
            <span>Saved on this device. You can edit it later in Settings.</span>
          </div>
          <div className="upload-footer-actions">
            <button type="button" className="btn btn-secondary" onClick={handleClose}>
              Cancel
            </button>
            <button type="button" className="btn btn-secondary" onClick={(e) => handleSubmit(e, false)}>
              Create company
            </button>
            <button type="button" className="btn btn-primary" onClick={(e) => handleSubmit(e, true)}>
              Create &amp; upload invoice
            </button>
          </div>
        </div>
      }
    >
      <form className="settings-form" onSubmit={(e) => handleSubmit(e, false)} noValidate>
        {error && <div className="error-banner" role="alert">{error}</div>}
        <div className="settings-grid">
          <div className="form-group">
            <label className="form-label" htmlFor="co-name">Company name *</label>
            <input
              id="co-name"
              className="form-input"
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              placeholder="e.g. Sahyadri Textiles Pvt Ltd"
              autoFocus
            />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="co-industry">Industry</label>
            <select
              id="co-industry"
              className="form-select"
              value={form.industry}
              onChange={(e) => set('industry', e.target.value)}
            >
              {INDUSTRIES.map((industry) => (
                <option key={industry} value={industry}>{industry}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="co-emp">Employees</label>
            <input
              id="co-emp"
              type="number"
              min="1"
              className="form-input"
              value={form.employees}
              onChange={(e) => set('employees', e.target.value)}
              placeholder="e.g. 25"
            />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="co-loc">Location</label>
            <input
              id="co-loc"
              className="form-input"
              value={form.location}
              onChange={(e) => set('location', e.target.value)}
              placeholder="City, State"
            />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="co-year">Reporting year</label>
            <select
              id="co-year"
              className="form-select"
              value={form.reportingYear}
              onChange={(e) => set('reportingYear', e.target.value)}
            >
              {years.map((year) => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="co-target">Reduction target (optional)</label>
            <input
              id="co-target"
              className="form-input"
              value={form.netZeroTarget}
              onChange={(e) => set('netZeroTarget', e.target.value)}
              placeholder="e.g. Net zero by 2040"
            />
          </div>
        </div>
      </form>
    </Modal>
  );
};
