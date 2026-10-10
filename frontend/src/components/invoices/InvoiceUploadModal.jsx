import { useState } from 'react';
import { Modal } from '../common/Modal';
import {
  UploadCloudIcon,
  SparklesIcon,
  FileTextIcon,
  InfoIcon,
} from '../common/Icons';
import { PRESET_SAMPLE_INVOICES } from '../../data/mockData';
import { useTrueScope } from '../../context/TrueScopeContext';

export const InvoiceUploadModal = () => {
  const { isUploadModalOpen, closeUploadModal, addInvoice } = useTrueScope();

  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedPreset, setSelectedPreset] = useState(null);
  const [processingState, setProcessingState] = useState('idle'); // idle | parsing | classifying | calculating | done | error
  const [progressPercent, setProgressPercent] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');

  const resetState = () => {
    setSelectedFile(null);
    setSelectedPreset(null);
    setProcessingState('idle');
    setProgressPercent(0);
    setErrorMessage('');
  };

  const handleClose = () => {
    resetState();
    closeUploadModal();
  };

  // Handle Drag & Drop
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (file) => {
    setSelectedFile(file);
    setSelectedPreset(null);
    setErrorMessage('');
  };

  const handleSelectPreset = (preset) => {
    setSelectedPreset(preset);
    setSelectedFile({ name: preset.fileName, size: 245000 });
    setErrorMessage('');
  };

  // Start Simulated Processing
  const handleStartSimulatedProcessing = () => {
    if (!selectedFile && !selectedPreset) {
      setErrorMessage('Please select an invoice file or pick a demo preset.');
      return;
    }

    setProcessingState('parsing');
    setProgressPercent(25);

    // Step 1: Simulated OCR Parsing
    setTimeout(() => {
      setProcessingState('classifying');
      setProgressPercent(60);

      // Step 2: Simulated Activity Classification
      setTimeout(() => {
        setProcessingState('calculating');
        setProgressPercent(90);

        // Step 3: Simulated Factor Calculation
        setTimeout(() => {
          setProgressPercent(100);
          setProcessingState('done');

          // Assemble the generated invoice
          const template = selectedPreset || PRESET_SAMPLE_INVOICES[0];
          const calculatedEmissions = Math.round(template.quantity * template.emissionFactor);

          const newInvoice = {
            invoiceNumber: `INV-DEMO-${Math.floor(1000 + Math.random() * 9000)}`,
            supplier: template.supplier,
            billingPeriod: 'Current Month Billing Period',
            totalAmount: template.totalAmount,
            currency: 'USD',
            itemDescription: template.itemDescription,
            quantity: template.quantity,
            unit: template.unit,
            activityCategory: template.activityCategory,
            scope: template.scope,
            emissionFactor: template.emissionFactor,
            emissionFactorUnit: template.emissionFactorUnit,
            emissionFactorNote: 'Demo Mock Factor - Unverified (Simulation)',
            calculatedEmissionsKg: calculatedEmissions,
            confidence: template.confidence || 95,
            confidenceLevel: 'high',
            extractedFields: {
              fileName: selectedFile?.name || template.fileName,
              fileSize: selectedFile?.size ? `${Math.round(selectedFile.size / 1024)} KB` : '184 KB',
              scanMethod: 'Simulated Client OCR Pipeline',
              processedTimestamp: new Date().toLocaleTimeString(),
            },
          };

          // Delay slightly so the user sees 100% completion
          setTimeout(() => {
            addInvoice(newInvoice);
            handleClose();
          }, 600);
        }, 800);
      }, 900);
    }, 800);
  };

  const isProcessing =
    processingState === 'parsing' ||
    processingState === 'classifying' ||
    processingState === 'calculating' ||
    processingState === 'done';

  return (
    <Modal
      isOpen={isUploadModalOpen}
      onClose={handleClose}
      title="Upload Invoice for Carbon Estimation"
      subtitle="Simulate AI-driven invoice parsing, category classification, and CO₂e calculation."
      maxWidth="680px"
      footer={
        <div className="upload-modal-footer">
          <div className="simulation-notice-text">
            <span>⚡ Simulated client-side processing for prototype review</span>
          </div>
          <div className="upload-footer-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleClose}
              disabled={isProcessing}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleStartSimulatedProcessing}
              disabled={(!selectedFile && !selectedPreset) || isProcessing}
            >
              {isProcessing ? 'Processing...' : 'Run Demo Analysis'}
            </button>
          </div>
        </div>
      }
    >
      <div className="upload-modal-content">
        {/* Transparent Demo Notice Banner */}
        <div className="demo-notice-banner">
          <InfoIcon size={18} className="demo-notice-icon" />
          <div className="demo-notice-content">
            <strong>Demo Simulation Mode</strong>
            <p>
              The backend OCR and emission-factor engine are not connected yet.
              Uploaded documents are processed locally with mock AI classification to demonstrate the SME user experience.
            </p>
          </div>
        </div>

        {/* Processing State Stepper */}
        {isProcessing && (
          <div className="processing-progress-card">
            <div className="progress-header">
              <div className="progress-title-row">
                <SparklesIcon size={18} className="progress-sparkle" />
                <span className="progress-step-text">
                  {processingState === 'parsing' && 'Step 1 of 3: Performing OCR text extraction...'}
                  {processingState === 'classifying' && 'Step 2 of 3: Classifying activity and mapping GHG Scope...'}
                  {processingState === 'calculating' && 'Step 3 of 3: Applying emission factor and estimating kg CO₂e...'}
                  {processingState === 'done' && 'Extraction complete! Loading results...'}
                </span>
              </div>
              <span className="progress-number">{progressPercent}%</span>
            </div>

            <div className="progress-bar-track">
              <div
                className="progress-bar-fill"
                style={{ width: `${progressPercent}%` }}
              />
            </div>

            <div className="progress-steps-list">
              <span className={`p-step ${progressPercent >= 25 ? 'active' : ''}`}>
                1. Text OCR
              </span>
              <span className={`p-step ${progressPercent >= 60 ? 'active' : ''}`}>
                2. AI Scope Tagging
              </span>
              <span className={`p-step ${progressPercent >= 90 ? 'active' : ''}`}>
                3. Emission Calculation
              </span>
            </div>
          </div>
        )}

        {/* Drag and Drop Zone */}
        {!isProcessing && (
          <>
            <div
              className={`dropzone-area ${dragActive ? 'drag-over' : ''} ${
                selectedFile ? 'has-file' : ''
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input
                type="file"
                id="invoice-file-input"
                className="dropzone-file-input"
                accept=".pdf,.png,.jpg,.jpeg,.csv"
                onChange={handleFileChange}
              />
              <label htmlFor="invoice-file-input" className="dropzone-label">
                <div className="dropzone-icon-circle">
                  {selectedFile ? (
                    <FileTextIcon size={28} className="dropzone-icon-active" />
                  ) : (
                    <UploadCloudIcon size={28} className="dropzone-icon" />
                  )}
                </div>

                {selectedFile ? (
                  <div className="selected-file-details">
                    <span className="file-name">{selectedFile.name}</span>
                    <span className="file-ready-tag">
                      ✓ Ready for demo extraction (Click "Run Demo Analysis")
                    </span>
                  </div>
                ) : (
                  <div className="dropzone-instructions">
                    <span className="dropzone-prompt">
                      <strong>Click to browse</strong> or drag and drop invoice here
                    </span>
                    <span className="dropzone-formats">
                      Supports PDF, PNG, JPG, or CSV (Utility bills, fuel receipts, logistics invoices)
                    </span>
                  </div>
                )}
              </label>
            </div>

            {errorMessage && (
              <div className="upload-error-msg">{errorMessage}</div>
            )}

            {/* Quick Preset Invoices for Hackathon Testing */}
            <div className="preset-invoices-section">
              <div className="preset-header">
                <span className="preset-title">Or test with a preset SME invoice:</span>
                <span className="preset-subtitle">Instant sample data</span>
              </div>

              <div className="preset-grid">
                {PRESET_SAMPLE_INVOICES.map((preset, index) => {
                  const isPresetActive = selectedPreset?.title === preset.title;
                  return (
                    <button
                      key={index}
                      type="button"
                      className={`preset-invoice-card ${isPresetActive ? 'selected' : ''}`}
                      onClick={() => handleSelectPreset(preset)}
                    >
                      <div className="preset-card-top">
                        <FileTextIcon size={16} />
                        <span className="preset-badge">{preset.scope}</span>
                      </div>
                      <strong className="preset-item-title">{preset.title}</strong>
                      <div className="preset-meta-row">
                        <span>{preset.quantity.toLocaleString()} {preset.unit}</span>
                        <span>•</span>
                        <span>{preset.activityCategory}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
};
