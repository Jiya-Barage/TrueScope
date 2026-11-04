import { INITIAL_COMPANY, SAMPLE_COMPANY_ID } from '../data/mockData';

const COMPANIES_KEY = 'truescope.companies.v1';
const ACTIVE_KEY = 'truescope.activeCompany.v1';
const OWNERS_KEY = 'truescope.invoiceOwners.v1';

const readJson = (key, fallback) => {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
};

const writeJson = (key, value) => {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable: app keeps working in memory */
  }
};

export const loadCompanies = () => {
  const stored = readJson(COMPANIES_KEY, []);
  const custom = Array.isArray(stored)
    ? stored.filter((company) => company && company.id && company.id !== SAMPLE_COMPANY_ID)
    : [];
  const storedSample = Array.isArray(stored)
    ? stored.find((company) => company?.id === SAMPLE_COMPANY_ID)
    : null;
  return [{ ...INITIAL_COMPANY, ...(storedSample || {}), id: SAMPLE_COMPANY_ID, isSample: true }, ...custom];
};

export const saveCompanies = (companies) => writeJson(COMPANIES_KEY, companies);

export const loadActiveCompanyId = (companies) => {
  const id = readJson(ACTIVE_KEY, SAMPLE_COMPANY_ID);
  return companies.some((company) => company.id === id) ? id : SAMPLE_COMPANY_ID;
};

export const saveActiveCompanyId = (id) => writeJson(ACTIVE_KEY, id);

export const loadInvoiceOwners = () => {
  const owners = readJson(OWNERS_KEY, {});
  return owners && typeof owners === 'object' ? owners : {};
};

export const saveInvoiceOwners = (owners) => writeJson(OWNERS_KEY, owners);

export const createCompanyId = (name) => {
  const slug = String(name || 'company')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 24) || 'company';
  return `${slug}-${Date.now().toString(36)}`;
};

export const sizeLabel = (employees) => {
  const count = Number(employees);
  if (!Number.isFinite(count) || count <= 0) return 'SME';
  if (count < 10) return `Micro enterprise (${count} employees)`;
  if (count < 50) return `Small enterprise (${count} employees)`;
  return `Medium enterprise (${count} employees)`;
};
