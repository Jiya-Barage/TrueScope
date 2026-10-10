import { useState } from 'react';
import { formatNumber } from '../../utils/formatters';

export const MonthlyTrendChart = ({ data = [] }) => {
  const [hoveredIndex, setHoveredIndex] = useState(null);

  if (!data || data.length === 0) {
    return <div className="chart-empty-state">No trend data available</div>;
  }

  // Chart dimensions
  const width = 640;
  const height = 260;
  const padding = { top: 25, right: 20, bottom: 40, left: 55 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Max value calculation
  const maxTotal = Math.max(...data.map((d) => d.total || (d.scope1 + d.scope2 + d.scope3)), 10000);
  const yTicks = [0, maxTotal * 0.25, maxTotal * 0.5, maxTotal * 0.75, maxTotal];

  const barSlotWidth = chartWidth / data.length;
  const barWidth = Math.min(28, barSlotWidth * 0.55);

  const colors = {
    scope1: '#d97706', // Scope 1 - Amber
    scope2: '#0284c7', // Scope 2 - Sky Blue
    scope3: '#8b5cf6', // Scope 3 - Purple
  };

  const hoveredData = hoveredIndex !== null ? data[hoveredIndex] : null;

  return (
    <div className="trend-chart-container">
      <div className="chart-legend-row">
        <div className="chart-legend-item">
          <span className="legend-color-dot" style={{ backgroundColor: colors.scope1 }} />
          <span>Scope 1 (Direct)</span>
        </div>
        <div className="chart-legend-item">
          <span className="legend-color-dot" style={{ backgroundColor: colors.scope2 }} />
          <span>Scope 2 (Electricity)</span>
        </div>
        <div className="chart-legend-item">
          <span className="legend-color-dot" style={{ backgroundColor: colors.scope3 }} />
          <span>Scope 3 (Value Chain)</span>
        </div>
      </div>

      <div className="chart-svg-wrap">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="trend-chart-svg"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Horizontal Grid lines & Y-axis labels */}
          {yTicks.map((tick, i) => {
            const y = padding.top + chartHeight - (tick / maxTotal) * chartHeight;
            return (
              <g key={i}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={width - padding.right}
                  y2={y}
                  stroke="#e2e8e0"
                  strokeDasharray={i === 0 ? 'none' : '3 3'}
                  strokeWidth="1"
                />
                <text
                  x={padding.left - 8}
                  y={y + 4}
                  textAnchor="end"
                  className="chart-axis-label"
                  fontSize="11"
                  fill="#718096"
                >
                  {tick >= 1000 ? `${(tick / 1000).toFixed(0)}k` : tick}
                </text>
              </g>
            );
          })}

          {/* Stacked bars for each month */}
          {data.map((item, idx) => {
            const x = padding.left + idx * barSlotWidth + (barSlotWidth - barWidth) / 2;
            const s1Height = ((item.scope1 || 0) / maxTotal) * chartHeight;
            const s2Height = ((item.scope2 || 0) / maxTotal) * chartHeight;
            const s3Height = ((item.scope3 || 0) / maxTotal) * chartHeight;

            const yS1 = padding.top + chartHeight - s1Height;
            const yS2 = yS1 - s2Height;
            const yS3 = yS2 - s3Height;

            const isHovered = hoveredIndex === idx;

            return (
              <g
                key={item.month || idx}
                className="chart-bar-group"
                onMouseEnter={() => setHoveredIndex(idx)}
                onMouseLeave={() => setHoveredIndex(null)}
                style={{ cursor: 'pointer' }}
              >
                {/* Hover background hit area */}
                <rect
                  x={padding.left + idx * barSlotWidth}
                  y={padding.top}
                  width={barSlotWidth}
                  height={chartHeight}
                  fill={isHovered ? 'rgba(45, 106, 79, 0.06)' : 'transparent'}
                  rx="4"
                />

                {/* Scope 1 bar (bottom) */}
                <rect
                  x={x}
                  y={yS1}
                  width={barWidth}
                  height={s1Height}
                  fill={colors.scope1}
                  opacity={isHovered ? 1 : 0.88}
                  rx="1"
                />

                {/* Scope 2 bar (middle) */}
                <rect
                  x={x}
                  y={yS2}
                  width={barWidth}
                  height={s2Height}
                  fill={colors.scope2}
                  opacity={isHovered ? 1 : 0.88}
                />

                {/* Scope 3 bar (top with rounded top corners) */}
                <rect
                  x={x}
                  y={yS3}
                  width={barWidth}
                  height={s3Height}
                  fill={colors.scope3}
                  opacity={isHovered ? 1 : 0.88}
                  rx="2"
                />

                {/* X-axis Month Label */}
                <text
                  x={x + barWidth / 2}
                  y={height - padding.bottom + 18}
                  textAnchor="middle"
                  className={`chart-axis-label ${isHovered ? 'active' : ''}`}
                  fontSize="11"
                  fill={isHovered ? '#14382c' : '#718096'}
                  fontWeight={isHovered ? '600' : '400'}
                >
                  {item.month}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoveredData && (
          <div
            className="chart-tooltip"
            style={{
              left: `${Math.min(
                85,
                Math.max(15, (hoveredIndex / (data.length - 1)) * 100)
              )}%`,
            }}
          >
            <div className="tooltip-title">{hoveredData.month} 2024 Emissions</div>
            <div className="tooltip-row total-row">
              <span>Total CO₂e:</span>
              <strong>{formatNumber(hoveredData.total || (hoveredData.scope1 + hoveredData.scope2 + hoveredData.scope3))} kg</strong>
            </div>
            <div className="tooltip-divider" />
            <div className="tooltip-row">
              <span className="tooltip-dot" style={{ backgroundColor: colors.scope1 }} />
              <span>Scope 1:</span>
              <span>{formatNumber(hoveredData.scope1)} kg</span>
            </div>
            <div className="tooltip-row">
              <span className="tooltip-dot" style={{ backgroundColor: colors.scope2 }} />
              <span>Scope 2:</span>
              <span>{formatNumber(hoveredData.scope2)} kg</span>
            </div>
            <div className="tooltip-row">
              <span className="tooltip-dot" style={{ backgroundColor: colors.scope3 }} />
              <span>Scope 3:</span>
              <span>{formatNumber(hoveredData.scope3)} kg</span>
            </div>
          </div>
        )}
      </div>

      <div className="chart-caption">
        <span>Unit: kg CO₂e</span>
        <span className="chart-disclaimer-tag">Demo Simulated Historical Baseline</span>
      </div>
    </div>
  );
};
