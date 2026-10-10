import { useState } from 'react';
import { formatNumber } from '../../utils/formatters';
import { ScopeBadge } from '../common/Badge';

export const CategoryDonutChart = ({ categories = [] }) => {
  const [hoveredCategory, setHoveredCategory] = useState(null);

  if (!categories || categories.length === 0) {
    return <div className="chart-empty-state">No category breakdown data available</div>;
  }

  // Calculate SVG Donut parameters
  const size = 180;
  const strokeWidth = 24;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  const segments = categories.reduce((acc, cat) => {
    const prevOffset = acc.length > 0 ? acc[acc.length - 1].cumulativePct : 0;
    const strokeDasharray = `${(cat.percentage / 100) * circumference} ${circumference}`;
    const strokeDashoffset = -((prevOffset / 100) * circumference);
    const cumulativePct = prevOffset + cat.percentage;
    acc.push({
      ...cat,
      strokeDasharray,
      strokeDashoffset,
      cumulativePct,
    });
    return acc;
  }, []);

  const activeItem = hoveredCategory || categories[0];

  return (
    <div className="category-chart-container">
      <div className="donut-and-metric">
        {/* SVG Donut */}
        <div className="donut-svg-wrap">
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="donut-svg">
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="transparent"
              stroke="#e8ede8"
              strokeWidth={strokeWidth}
            />
            {segments.map((seg) => (
              <circle
                key={seg.category}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="transparent"
                stroke={seg.color}
                strokeWidth={hoveredCategory?.category === seg.category ? strokeWidth + 4 : strokeWidth}
                strokeDasharray={seg.strokeDasharray}
                strokeDashoffset={seg.strokeDashoffset}
                strokeLinecap="butt"
                className="donut-segment"
                onMouseEnter={() => setHoveredCategory(seg)}
                onMouseLeave={() => setHoveredCategory(null)}
                style={{
                  transform: 'rotate(-90deg)',
                  transformOrigin: '50% 50%',
                  transition: 'stroke-width 0.2s ease, opacity 0.2s ease',
                  opacity: hoveredCategory && hoveredCategory.category !== seg.category ? 0.6 : 1,
                  cursor: 'pointer',
                }}
              />
            ))}
          </svg>

          {/* Donut Center Display */}
          <div className="donut-center-content">
            <span className="donut-center-label">Top Category</span>
            <strong className="donut-center-value">{activeItem ? `${activeItem.percentage.toFixed(1)}%` : '0%'}</strong>
            <span className="donut-center-sub">{activeItem ? activeItem.category.split(' ')[0] : ''}</span>
          </div>
        </div>

        {/* Selected Category Highlight Callout */}
        <div className="donut-callout">
          {activeItem && (
            <div className="donut-selected-card">
              <div className="callout-header">
                <span className="legend-color-dot" style={{ backgroundColor: activeItem.color }} />
                <span className="callout-title">{activeItem.category}</span>
                <ScopeBadge scope={activeItem.scope} />
              </div>
              <div className="callout-value-row">
                <span className="callout-emissions">{formatNumber(activeItem.emissions)} kg CO₂e</span>
                <span className="callout-pct">({activeItem.percentage.toFixed(1)}% of total)</span>
              </div>
              <div className="callout-invoices-count">
                Based on {activeItem.count} invoice{activeItem.count > 1 ? 's' : ''}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Category breakdown progress list */}
      <div className="category-list">
        {categories.map((cat) => {
          const isSelected = hoveredCategory?.category === cat.category;
          return (
            <div
              key={cat.category}
              className={`category-item-row ${isSelected ? 'highlighted' : ''}`}
              onMouseEnter={() => setHoveredCategory(cat)}
              onMouseLeave={() => setHoveredCategory(null)}
            >
              <div className="cat-row-top">
                <div className="cat-name-group">
                  <span className="cat-indicator" style={{ backgroundColor: cat.color }} />
                  <span className="cat-name">{cat.category}</span>
                </div>
                <div className="cat-values">
                  <span className="cat-kg">{formatNumber(cat.emissions)} kg</span>
                  <span className="cat-pct">{cat.percentage.toFixed(1)}%</span>
                </div>
              </div>

              <div className="cat-progress-track">
                <div
                  className="cat-progress-fill"
                  style={{
                    width: `${cat.percentage}%`,
                    backgroundColor: cat.color,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
