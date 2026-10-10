import { useState } from 'react';
import { Card } from '../components/common/Card';
import { ScopeBadge, DemoPill } from '../components/common/Badge';
import {
  InfoIcon,
} from '../components/common/Icons';
import { formatEmissions } from '../utils/formatters';
import { useTrueScope } from '../context/TrueScopeContext';

export const EmissionsView = () => {
  const { stats, company } = useTrueScope();
  const [selectedScopeTab, setSelectedScopeTab] = useState('all');

  const scopeDetails = [
    {
      scope: 'Scope 1',
      title: 'Direct Emissions',
      description:
        'Emissions from sources directly owned or controlled by the SME, such as company vehicles (fleet diesel/petrol) and on-site fuel combustion for heating.',
      emissions: stats.scope1Kg,
      percentage: stats.scope1Pct,
      color: '#d97706',
      sources: ['Fleet delivery vans', 'Warehouse gas heating', 'On-site generators'],
    },
    {
      scope: 'Scope 2',
      title: 'Indirect (Purchased Energy)',
      description:
        'Emissions from the generation of purchased electricity, steam, heating, or cooling consumed by the SME at leased or owned premises.',
      emissions: stats.scope2Kg,
      percentage: stats.scope2Pct,
      color: '#0284c7',
      sources: ['Facility lighting & IT servers', 'HVAC systems', 'Refrigeration units'],
    },
    {
      scope: 'Scope 3',
      title: 'Value Chain (Upstream & Downstream)',
      description:
        'All other indirect emissions that occur in the SME value chain, including 3rd-party logistics & freight, packaging materials, business flights, and waste disposal.',
      emissions: stats.scope3Kg,
      percentage: stats.scope3Pct,
      color: '#8b5cf6',
      sources: ['Third-party freight shipping', 'Packaging materials', 'Waste & recycling', 'Business travel'],
    },
  ];

  const filteredCategories =
    selectedScopeTab === 'all'
      ? stats.categoryBreakdown
      : stats.categoryBreakdown.filter((c) => c.scope === selectedScopeTab);

  return (
    <div className="view-container emissions-view">
      {/* Header Banner */}
      <div className="emissions-header-banner">
        <div>
          <div className="emissions-tag-row">
            <DemoPill label="GHG PROTOCOL ALIGNED" />
            <span className="emissions-facility-tag">
              Baseline Year: {company.baselineYear} • Reporting Year: {company.reportingYear}
            </span>
          </div>
          <h2 className="emissions-title">Greenhouse Gas (GHG) Scope Breakdown</h2>
          <p className="emissions-desc">
            Granular accounting categorized per the Greenhouse Gas Protocol Corporate Accounting and Reporting Standard.
          </p>
        </div>
      </div>

      {/* 3 Scope Cards Row */}
      <div className="scope-cards-grid">
        {scopeDetails.map((s) => (
          <div
            key={s.scope}
            className="scope-summary-card"
            style={{ borderTop: `4px solid ${s.color}` }}
          >
            <div className="scope-card-header">
              <span className="scope-name-tag" style={{ color: s.color }}>
                {s.scope}
              </span>
              <strong className="scope-share">{s.percentage.toFixed(1)}% of total</strong>
            </div>

            <h3 className="scope-title">{s.title}</h3>
            <p className="scope-description">{s.description}</p>

            <div className="scope-stat-row">
              <span className="scope-kg">{formatEmissions(s.emissions)}</span>
            </div>

            <div className="scope-sources-list">
              <span className="sources-label">Primary SME Drivers:</span>
              <ul>
                {s.sources.map((src, idx) => (
                  <li key={idx}>
                    <span className="source-dot" style={{ backgroundColor: s.color }} />
                    <span>{src}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>

      {/* Category Breakdown Table with Tabs */}
      <Card
        title="Activity Categories & Emission Intensities"
        subtitle="Individual activity groups mapped from supplier invoice line items"
        headerAction={
          <div className="scope-tabs-bar">
            {['all', 'Scope 1', 'Scope 2', 'Scope 3'].map((tab) => (
              <button
                key={tab}
                type="button"
                className={`scope-tab-btn ${selectedScopeTab === tab ? 'active' : ''}`}
                onClick={() => setSelectedScopeTab(tab)}
              >
                {tab === 'all' ? 'All Activities' : tab}
              </button>
            ))}
          </div>
        }
      >
        <div className="category-table-wrap">
          <table className="ts-table">
            <thead>
              <tr>
                <th>Activity Category</th>
                <th>GHG Scope</th>
                <th>Invoices Count</th>
                <th>Total Emissions</th>
                <th>% of Total Footprint</th>
                <th>Contribution Bar</th>
              </tr>
            </thead>
            <tbody>
              {filteredCategories.map((cat) => (
                <tr key={cat.category}>
                  <td>
                    <div className="cat-name-cell">
                      <span className="cat-dot" style={{ backgroundColor: cat.color }} />
                      <strong className="cat-cell-title">{cat.category}</strong>
                    </div>
                  </td>
                  <td>
                    <ScopeBadge scope={cat.scope} />
                  </td>
                  <td>{cat.count} document{cat.count > 1 ? 's' : ''}</td>
                  <td>
                    <strong>{formatEmissions(cat.emissions)}</strong>
                  </td>
                  <td>
                    <span className="cat-cell-pct">{cat.percentage.toFixed(1)}%</span>
                  </td>
                  <td>
                    <div className="cat-cell-bar-track">
                      <div
                        className="cat-cell-bar-fill"
                        style={{
                          width: `${cat.percentage}%`,
                          backgroundColor: cat.color,
                        }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Methodology & Factor Provenance Card */}
      <div className="methodology-card">
        <h4 className="methodology-title">
          <InfoIcon size={18} />
          <span>Accounting Formula & Emission Factor Methodology</span>
        </h4>
        <div className="methodology-grid">
          <div className="methodology-block">
            <span className="block-label">1. Activity Data (Invoice OCR)</span>
            <p className="block-text">
              Direct physical activity units are extracted from invoices (e.g., kWh of electricity, litres of fuel, tonne-km of freight shipping).
            </p>
          </div>
          <div className="methodology-block">
            <span className="block-label">2. Emission Factor Application</span>
            <p className="block-text">
              The matched factor converts activity data into carbon dioxide equivalent: <code>kg CO₂e = Activity × Factor</code>.
            </p>
          </div>
          <div className="methodology-block">
            <span className="block-label">3. Compliance Notice</span>
            <p className="block-text">
              In this hackathon build, emission factors are simulated demonstration values. Production integrations connect to certified repositories (DEFRA, EPA GHG Hub).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
