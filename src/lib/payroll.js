export function childBonus(children) {
  const count = Number(children) || 0;
  if (count >= 3) return 600000;
  if (count === 2) return 400000;
  if (count === 1) return 250000;
  return 0;
}

export function calculatePreview(employee, hours, deductions) {
  const base = Number(employee?.hourly_rate || 0) * Number(hours || 0);
  const bonus = childBonus(employee?.children);
  const eps = base * Number(deductions.eps_percent || 0) / 100;
  const pension = base * Number(deductions.pension_percent || 0) / 100;
  const arl = base * Number(deductions.arl_percent || 0) / 100;
  const other = Number(deductions.other_amount || 0);
  const totalDeductions = eps + pension + arl + other;
  return { base, bonus, eps, pension, arl, other, totalDeductions, net: base + bonus - totalDeductions };
}

