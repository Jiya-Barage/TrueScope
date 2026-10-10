export const Card = ({ children, className = '', title, subtitle, headerAction, footer }) => {
  return (
    <div className={`ts-card ${className}`}>
      {(title || subtitle || headerAction) && (
        <div className="ts-card-header">
          <div>
            {title && <h3 className="ts-card-title">{title}</h3>}
            {subtitle && <p className="ts-card-subtitle">{subtitle}</p>}
          </div>
          {headerAction && <div className="ts-card-action">{headerAction}</div>}
        </div>
      )}
      <div className="ts-card-body">{children}</div>
      {footer && <div className="ts-card-footer">{footer}</div>}
    </div>
  );
};

export const MetricCard = ({
  title,
  value,
  subvalue,
  badge,
  icon: Icon,
  trend,
  trendLabel,
  scopeColor,
}) => {
  return (
    <div className="metric-card" style={scopeColor ? { borderLeft: `4px solid ${scopeColor}` } : {}}>
      <div className="metric-header">
        <div className="metric-title-wrap">
          <span className="metric-title">{title}</span>
          {badge}
        </div>
        {Icon && (
          <div className="metric-icon-wrap">
            <Icon size={20} className="metric-icon" />
          </div>
        )}
      </div>

      <div className="metric-value-row">
        <span className="metric-value">{value}</span>
      </div>

      {(subvalue || trend) && (
        <div className="metric-footer">
          {trend && (
            <span className={`metric-trend ${trend.startsWith('+') ? 'trend-up' : 'trend-down'}`}>
              {trend}
            </span>
          )}
          {trendLabel && <span className="metric-trend-label">{trendLabel}</span>}
          {subvalue && <span className="metric-subvalue">{subvalue}</span>}
        </div>
      )}
    </div>
  );
};
