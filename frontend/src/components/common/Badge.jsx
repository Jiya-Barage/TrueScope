export const ScopeBadge = ({ scope }) => {
  const normalized = (scope || '').toLowerCase();
  let colorClass = 'badge-scope-unknown';
  let label = 'Unclassified';
  if (normalized === 'scope 1' || normalized === '1') {
    colorClass = 'badge-scope1';
    label = 'Scope 1';
  } else if (normalized === 'scope 2' || normalized === '2') {
    colorClass = 'badge-scope2';
    label = 'Scope 2';
  } else if (normalized === 'scope 3' || normalized === '3') {
    colorClass = 'badge-scope3';
    label = 'Scope 3';
  }

  return <span className={`badge ${colorClass}`}>{label}</span>;
};

export const ConfidenceBadge = ({ confidence, confidenceFlag }) => {
  const hasScore = typeof confidence === 'number' && Number.isFinite(confidence);
  const score = hasScore ? confidence : null;
  const knownFlags = { high: 'High', medium: 'Med', low: 'Low' };
  const flagClasses = {
    high: 'badge-conf-high',
    medium: 'badge-conf-med',
    low: 'badge-conf-low',
  };
  let label = 'Unavailable';
  let levelClass = 'badge-conf-unknown';

  if (hasScore) {
    if (knownFlags[confidenceFlag]) {
      label = knownFlags[confidenceFlag];
      levelClass = flagClasses[confidenceFlag];
    } else {
      label = 'Low';
      levelClass = 'badge-conf-low';
      if (score >= 90) {
        label = 'High';
        levelClass = 'badge-conf-high';
      } else if (score >= 75) {
        label = 'Med';
        levelClass = 'badge-conf-med';
      }
    }
  }

  return (
    <span
      className={`badge ${levelClass}`}
      title={hasScore ? `AI Confidence Score: ${score}%` : 'AI confidence unavailable'}
    >
      <span className="badge-dot" />
      {hasScore ? `${score}% (${label})` : label}
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
