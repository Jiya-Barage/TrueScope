import { useEffect, useRef, useState } from 'react';
import { Modal } from '../common/Modal';
import {
  UploadCloudIcon,
  SparklesIcon,
  FileTextIcon,
  InfoIcon,
} from '../common/Icons';
import { PRESET_SAMPLE_INVOICES } from '../../data/mockData';
import { useTrueScope } from '../../context/TrueScopeContext';
import { apiRequest } from '../../services/api';

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;
const SUPPORTED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg'];

export const InvoiceUploadModal = () => {
  const { isUploadModalOpen, closeUploadModal, addUploadedInvoice } = useTrueScope();

  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedPreset, setSelectedPreset] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [uploadResponse, setUploadResponse] = useState(null);
  const uploadInFlight = useRef(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!selectedFile && fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [selectedFile]);

  const resetState = () => {
    setSelectedFile(null);
    setSelectedPreset(null);
    setUploadResponse(null);
    setErrorMessage('');
  };

  const handleClose = () => {
    if (uploadInFlight.current) return;
    resetState();
    closeUploadModal();
  };

  // Handle Drag & Drop
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (isUploading) return;
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
    if (!isUploading && e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (file) => {
    const extension = `.${file.name.split('.').pop()}`.toLowerCase();
    if (!SUPPORTED_EXTENSIONS.includes(extension)) {
      setSelectedFile(null);
      setSelectedPreset(null);
      setErrorMessage('Choose a PDF, PNG, JPG, or JPEG invoice file.');
      return;
    }

    if (file.size === 0) {
      setSelectedFile(null);
      setSelectedPreset(null);
      setErrorMessage('The selected file is empty. Choose a non-empty invoice file.');
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setSelectedFile(null);
      setSelectedPreset(null);
      setErrorMessage('Invoice files must be 10 MiB or smaller.');
      return;
    }

    setSelectedFile(file);
    setSelectedPreset(null);
    setErrorMessage('');
  };

  const handleSelectPreset = (preset) => {
    setSelectedPreset(preset);
    setSelectedFile(null);
    setErrorMessage('Presets are reference data, not files. Demo processing is not connected in this upload workflow.');
  };

  const handleUpload = async () => {
    if (uploadInFlight.current) return;
    if (!selectedFile) {
      setErrorMessage('Select a supported invoice file to upload.');
      return;
    }

    uploadInFlight.current = true;
    setIsUploading(true);
    setErrorMessage('');
    setUploadResponse(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await apiRequest('/api/invoices/upload', {
        method: 'POST',
        body: formData,
      });
      addUploadedInvoice(response);
      setUploadResponse(response);
      setSelectedFile(null);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Invoice upload failed.');
    } finally {
      uploadInFlight.current = false;
      setIsUploading(false);
    }
  };

  return (
    <Modal
      isOpen={isUploadModalOpen}
      onClose={handleClose}
      title="Upload Invoice for Carbon Estimation"
      subtitle="Upload a supported invoice for synchronous backend processing."
      maxWidth="680px"
      footer={
        <div className="upload-modal-footer">
          <div className="simulation-notice-text">
            <span>PDF, PNG, JPG, or JPEG • Maximum 10 MiB</span>
          </div>
          <div className="upload-footer-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleClose}
              disabled={isUploading}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleUpload}
              disabled={!selectedFile || isUploading}
            >
              {isUploading ? 'Uploading...' : 'Upload Invoice'}
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
            <strong>Backend Processing</strong>
            <p>
              The selected file is sent to the TrueScope backend for synchronous processing. Sample presets below are reference data and are not uploaded by this workflow.
            </p>
          </div>
        </div>

        {isUploading && (
          <div className="processing-progress-card">
            <div className="progress-header">
              <div className="progress-title-row">
                <SparklesIcon size={18} className="progress-sparkle" />
                <span className="progress-step-text">
                  Uploading and processing invoice...
                </span>
              </div>
            </div>
          </div>
        )}

        {uploadResponse && (() => {
          const lineItems = uploadResponse.result?.line_items;
          const lineItemCount = Array.isArray(lineItems) ? lineItems.length : 0;
          const warnings = Array.isArray(uploadResponse.result?.warnings)
            ? uploadResponse.result.warnings
            : [];

          return (
            <>
              <div className="download-toast" role="status">
                {lineItemCount > 0
                  ? `Upload processed successfully. Invoice ID: ${uploadResponse.invoice_id || 'Unavailable'}. ${lineItemCount} line item(s) are available in the invoice list.`
                  : `Upload processing completed. Invoice ID: ${uploadResponse.invoice_id || 'Unavailable'}. No line items were extracted.`}
                {' '}The raw response is retained in this modal.
              </div>
              {lineItemCount === 0 && warnings.length > 0 && (
                <ul role="status">
                  {warnings.map((warning, index) => (
                    <li key={`upload-warning-${index}`}>{warning}</li>
                  ))}
                </ul>
              )}
              <details>
                <summary>Raw backend response</summary>
                <pre style={{ maxHeight: '240px', overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(uploadResponse, null, 2)}
                </pre>
              </details>
            </>
          );
        })()}

        {errorMessage && (
          <div className="upload-error-msg" role="alert">{errorMessage}</div>
        )}

        {/* Drag and Drop Zone */}
        {!isUploading && (
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
                accept=".pdf,.png,.jpg,.jpeg"
                ref={fileInputRef}
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

                {selectedFile || selectedPreset ? (
                  <div className="selected-file-details">
                    <span className="file-name">{selectedFile?.name || selectedPreset?.fileName}</span>
                    <span className="file-ready-tag">
                      {selectedFile
                        ? 'Ready to upload to the backend.'
                        : 'Preset data only; choose an actual file to upload.'}
                    </span>
                  </div>
                ) : (
                  <div className="dropzone-instructions">
                    <span className="dropzone-prompt">
                      <strong>Click to browse</strong> or drag and drop invoice here
                    </span>
                    <span className="dropzone-formats">
                      Supports PDF, PNG, JPG, or JPEG up to 10 MiB
                    </span>
                  </div>
                )}
              </label>
            </div>

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
                      disabled={isUploading}
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
