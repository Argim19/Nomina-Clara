import test from 'node:test';
import assert from 'node:assert/strict';
import { calculatePreview, childBonus } from '../src/lib/payroll.js';

test('aplica la escala completa de bonificaciones', () => {
  assert.equal(childBonus(0), 0);
  assert.equal(childBonus(1), 250000);
  assert.equal(childBonus(2), 400000);
  assert.equal(childBonus(3), 600000);
  assert.equal(childBonus(6), 600000);
});

test('calcula el neto con deducciones parametrizadas', () => {
  const result = calculatePreview({ hourly_rate: 25000, children: 2 }, 160, { eps_percent: 4, pension_percent: 4, arl_percent: 0, other_amount: 50000 });
  assert.equal(result.base, 4000000);
  assert.equal(result.bonus, 400000);
  assert.equal(result.totalDeductions, 370000);
  assert.equal(result.net, 4030000);
});

