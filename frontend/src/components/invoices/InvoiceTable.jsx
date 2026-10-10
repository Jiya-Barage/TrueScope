import { ScopeBadge, ConfidenceBadge } from '../common/Badge';
import { ChevronRightIcon, FileTextIcon } from '../common/Icons';
import { formatEmissions, formatDate } from '../../utils/formatters';
import { useTrueScope } from '../../context/TrueScopeContext';

export const InvoiceTable = ({
  invoices = [],
  limit,
  showSearchAndFilters = false,
  emptyMessage = 'No invoices found matching criteria.',
}) => {
  const {
    openInvoiceDetail,
    invoiceSearchQuery,
    setInvoiceSearchQuery,
    selectedScopeFilter,
    setSelectedScopeFilter,
  } = useTrueScope();

  // Filter invoices if search and filter are active
  const filtered = invoices.filter((inv) => {
    if (selectedScopeFilter !== 'all' && inv.scope !== selectedScopeFilter) {
      return false;
    }
    if (invoiceSearchQuery.trim()) {
      const q = invoiceSearchQuery.toLowerCase();
      const matchNumber = inv.invoiceNumber?.toLowerCase().includes(q);
      const matchSupplier = inv.supplier?.toLowerCase().includes(q);
      const matchItem = inv.itemDescription?.toLowerCase().includes(q);
      const matchCat = inv.activityCategory?.toLowerCase().includes(q);
      return matchNumber || matchSupplier || matchItem || matchCat;
    }
    return true;
  });

  const displayList = limit ? filtered.slice(0, limit) : filtered;

  return (
    <div className="invoice-table-wrapper">
      {showSearchAndFilters && (
        <div className="table-controls-bar">
          <div className="search-input-wrap">
            <input
              type="text"
              placeholder="Search by supplier, invoice #, or category..."
              className="table-search-input"
              value={invoiceSearchQuery}
              onChange={(e) => setInvoiceSearchQuery(e.target.value)}
            />
          </div>

          <div className="filter-controls">
            <select
              className="scope-filter-select"
              value={selectedScopeFilter}
              onChange={(e) => setSelectedScopeFilter(e.target.value)}
            >
              <option value="all">All Scopes</option>
              <option value="Scope 1">Scope 1 (Direct)</option>
              <option value="Scope 2">Scope 2 (Electricity)</option>
              <option value="Scope 3">Scope 3 (Value Chain)</option>
            </select>
          </div>
        </div>
      )}

      {displayList.length === 0 ? (
        <div className="table-empty-state">
          <FileTextIcon size={32} className="empty-icon" />
          <p className="empty-title">{emptyMessage}</p>
          <span className="empty-subtitle">
            Try adjusting your search query or upload a new invoice.
          </span>
        </div>
      ) : (
        <div className="table-responsive-container">
          <table className="ts-table">
            <thead>
              <tr>
                <th>Invoice & Supplier</th>
                <th>Extracted Activity Item</th>
                <th>Category</th>
                <th>Scope</th>
                <th>Quantity</th>
                <th>Estimated CO₂e</th>
                <th>AI Confidence</th>
                <th className="th-action">Action</th>
              </tr>
            </thead>
            <tbody>
              {displayList.map((inv) => (
                <tr
                  key={inv.id}
                  className="table-row-clickable"
                  onClick={() => openInvoiceDetail(inv)}
                >
                  <td>
                    <div className="td-invoice-main">
                      <span className="td-inv-num">{inv.invoiceNumber}</span>
                      <span className="td-supplier">{inv.supplier}</span>
                      <span className="td-date">{formatDate(inv.date)}</span>
                    </div>
                  </td>
                  <td>
                    <div className="td-item-desc" title={inv.itemDescription}>
                      {inv.itemDescription}
                    </div>
                  </td>
                  <td>
                    <span className="td-category-tag">{inv.activityCategory}</span>
                  </td>
                  <td>
                    <ScopeBadge scope={inv.scope} />
                  </td>
                  <td>
                    <span className="td-quantity">
                      {inv.quantity.toLocaleString()} <span className="unit-sub">{inv.unit}</span>
                    </span>
                  </td>
                  <td>
                    <strong className="td-emissions">
                      {formatEmissions(inv.calculatedEmissionsKg)}
                    </strong>
                  </td>
                  <td>
                    <ConfidenceBadge confidence={inv.confidence} />
                  </td>
                  <td className="td-action">
                    <button
                      type="button"
                      className="btn-table-row-action"
                      onClick={(e) => {
                        e.stopPropagation();
                        openInvoiceDetail(inv);
                      }}
                      title="View invoice results breakdown"
                    >
                      <span>View</span>
                      <ChevronRightIcon size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
