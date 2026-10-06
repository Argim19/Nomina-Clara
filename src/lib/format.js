export const money = (value = 0) => new Intl.NumberFormat('es-CO', {
  style: 'currency', currency: 'COP', maximumFractionDigits: 0,
}).format(Number(value) || 0);

export const shortDate = (value) => new Intl.DateTimeFormat('es-CO', {
  day: '2-digit', month: 'short', year: 'numeric',
}).format(new Date(value));

export const periodLabel = (period) => {
  if (!period) return '—';
  const [year, month] = period.split('-');
  const label = new Intl.DateTimeFormat('es-CO', { month: 'long', year: 'numeric', timeZone: 'UTC' })
    .format(new Date(`${year}-${month}-01T00:00:00Z`));
  return label.charAt(0).toUpperCase() + label.slice(1);
};

export const initials = (name = '') => name.split(' ').filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase();

