export const ScopeBadge = ({ scope }) => {
  const normalized = (scope || '').toLowerCase();
  let colorClass = 'badge-scope3';
  if (normalized.includes('1')) colorClass = 'badge-scope1';
  if (normalized.includes('2')) colorClass = 'badge-scope2';

  return <span className={`badge ${colorClass}`}>{scope || 'Scope 3'}</span>;
};

export const ConfidenceBadge = ({ confidence }) => {
  const score = Number(confidence) || 0;
  let levelClass = 'badge-conf-low';
  let label = 'Low';

  if (score >= 90) {
    levelClass = 'badge-conf-high';
    label = 'High';
  } else if (score >= 75) {
    levelClass = 'badge-conf-med';
    label = 'Med';
  }

  return (
    <span
      className={`badge ${levelClass}`}
      title={`AI Confidence Score: ${score}%`}
    >
      <span className="badge-dot" />
      {score}% ({label})
    </span>
  );
};

export const DemoPill = ({ label = 'DEMO DATA' }) => (
  <span className="demo-pill" title="Demonstration data for hackathon prototype">
    ⚡ {label}
  </span>
);

export const StatusBadge = ({ status = 'Processed' }) => {
  return <span className="badge badge-status">{status}</span>;
};
