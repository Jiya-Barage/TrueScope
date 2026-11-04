/**
 * Utility functions for formatting numbers, currency, emissions, and dates.
 */

export const formatEmissions = (kgValue, unit = 'kg') => {
  if (kgValue === undefined || kgValue === null || isNaN(kgValue)) return '0 kg CO₂e';
  
  if (unit === 't') {
    const tons = kgValue / 1000;
    return `${tons.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} t CO₂e`;
  }
  
  return `${Math.round(kgValue).toLocaleString('en-US')} kg CO₂e`;
};

export const formatEmissionValue = (value, emissionsUnit) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 'Not calculated';
  if (typeof emissionsUnit !== 'string' || !emissionsUnit.trim()) return 'Unit unavailable';
  return `${value.toLocaleString('en-US', { maximumFractionDigits: 3 })} ${emissionsUnit}`;
};

export const formatNumber = (num, decimals = 0) => {
  if (num === undefined || num === null || isNaN(num)) return '0';
  return Number(num).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

export const formatCurrency = (amount, currency = 'USD') => {
  if (amount === undefined || amount === null || isNaN(amount)) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(amount);
};

export const formatDate = (dateStr) => {
  if (!dateStr) return 'N/A';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
};

const CATEGORY_LABELS = {
  electricity_grid: 'Purchased Electricity',
  natural_gas: 'Natural Gas Heating',
  mobile_fuel_diesel: 'Fleet Diesel',
  mobile_fuel_petrol: 'Fleet Petrol',
  stationary_fuel_diesel: 'Diesel (Generators)',
  freight_transport: 'Freight & Logistics',
  waste_disposal: 'Waste Management',
  business_travel: 'Business Travel',
  purchased_goods: 'Purchased Goods',
  water_effluent: 'Water & Effluent',
};

export const prettyCategory = (value) => {
  if (!value) return 'Other';
  if (CATEGORY_LABELS[value]) return CATEGORY_LABELS[value];
  return /^[a-z0-9_]+$/.test(value)
    ? value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
    : value;
};
