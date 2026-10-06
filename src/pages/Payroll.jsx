import { useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, BadgeCheck, Calculator, ChevronDown, CircleDollarSign, FileCheck2, UserRound } from 'lucide-react';
import { calculatePreview } from '../lib/payroll';
import { initials, money, periodLabel } from '../lib/format';

export default function Payroll({ employees, deductions: defaults, onCreate, goHistory }) {
  const currentPeriod = new Date().toISOString().slice(0, 7);
  const [step, setStep] = useState(1); const [employeeId, setEmployeeId] = useState('');
  const [period, setPeriod] = useState(currentPeriod); const [hours, setHours] = useState('');
  const [deductions, setDeductions] = useState({ ...defaults, other_amount: 0, other_label: 'Otros conceptos' });
  const [saving, setSaving] = useState(false); const [created, setCreated] = useState(null);
  const employee = employees.find((e) => String(e.id) === String(employeeId));
  const preview = useMemo(() => calculatePreview(employee, hours, deductions), [employee, hours, deductions]);
  const setDeduction = (key) => (e) => setDeductions({ ...deductions, [key]: e.target.value });
  const liquidate = async () => { setSaving(true); const result = await onCreate({ employee_id: Number(employeeId), period, hours: Number(hours), deductions }); setSaving(false); if (result) { setCreated(result); setStep(3); } };
  const reset = () => { setCreated(null); setEmployeeId(''); setHours(''); setPeriod(currentPeriod); setStep(1); };
  if (step === 3 && created) return <div className="success-view"><span className="success-icon"><FileCheck2 size={35} /></span><span className="eyebrow">Liquidación registrada</span><h2>El periodo quedó liquidado correctamente.</h2><p>La liquidación <strong>{created.code}</strong> de {created.employee_name} se guardó en el histórico y ya está disponible para generar su volante.</p><div className="success-amount"><span>Neto pagado</span><strong>{money(created.net_pay)}</strong><small>{periodLabel(created.period)}</small></div><div className="success-actions"><button className="secondary-button" onClick={reset}>Nueva liquidación</button><button className="primary-button" onClick={goHistory}>Ver en el historial <ArrowRight size={17} /></button></div></div>;
  return <div className="page-stack payroll-page">
    <section className="page-heading"><div><span className="eyebrow">Proceso de liquidación</span><h2>Calcular nómina</h2><p>Seleccione al empleado e ingrese únicamente las novedades del periodo.</p></div></section>
    <div className="stepper"><div className="step active"><span>{step > 1 ? <BadgeCheck size={19} /> : '1'}</span><div><strong>Datos del periodo</strong><small>Empleado y horas</small></div></div><i className={step > 1 ? 'done' : ''} /><div className={`step ${step >= 2 ? 'active' : ''}`}><span>2</span><div><strong>Revisión</strong><small>Totales y deducciones</small></div></div><i /><div className="step"><span>3</span><div><strong>Confirmación</strong><small>Registro histórico</small></div></div></div>
    {step === 1 ? <section className="panel payroll-form-panel">
      <div className="section-title"><span><UserRound size={21} /></span><div><h3>Información de liquidación</h3><p>Los datos laborales se consultan desde la ficha del empleado.</p></div></div>
      <div className="payroll-fields">
        <label className="span-2">Empleado activo<div className="select-wrap"><select value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}><option value="">Seleccione un empleado</option>{employees.filter(e => e.status === 'Activo').map(e => <option value={e.id} key={e.id}>{e.name} · {e.position}</option>)}</select><ChevronDown size={18} /></div></label>
        <label>Periodo<input type="month" value={period} onChange={(e) => setPeriod(e.target.value)} /></label>
        <label>Horas trabajadas<input type="number" min="1" max="744" value={hours} onChange={(e) => setHours(e.target.value)} placeholder="Ej. 160" /></label>
      </div>
      {employee && <div className="employee-preview"><span className="large-avatar">{initials(employee.name)}</span><div className="employee-main"><small>Empleado seleccionado</small><strong>{employee.name}</strong><span>CC {employee.document} · {employee.position}</span></div><div><small>Valor por hora</small><strong>{money(employee.hourly_rate)}</strong></div><div><small>Beneficiarios</small><strong>{employee.children} {employee.children === 1 ? 'hijo' : 'hijos'}</strong></div></div>}
      <div className="panel-actions"><span>Podrá revisar los conceptos antes de guardar.</span><button className="primary-button" disabled={!employee || !hours || !period} onClick={() => setStep(2)}>Revisar liquidación <ArrowRight size={17} /></button></div>
    </section> : <section className="review-layout">
      <article className="panel review-main"><button className="back-button" onClick={() => setStep(1)}><ArrowLeft size={17} />Modificar datos</button><div className="review-employee"><span>{initials(employee.name)}</span><div><small>Liquidación para</small><h3>{employee.name}</h3><p>{employee.position} · {periodLabel(period)} · {hours} horas</p></div></div>
        <div className="concepts"><div className="concept-head"><h4>Devengados</h4><span>Valor</span></div><div><span>Pago por horas <small>{hours} × {money(employee.hourly_rate)}</small></span><strong>{money(preview.base)}</strong></div><div><span>Bonificación por hijos <small>{employee.children} registrados</small></span><strong className="positive">+ {money(preview.bonus)}</strong></div><div className="concept-head deductions-title"><h4>Deducciones</h4><span>Valor</span></div><div><span>EPS <small>{deductions.eps_percent}% del pago base</small></span><strong>− {money(preview.eps)}</strong></div><div><span>Pensión <small>{deductions.pension_percent}% del pago base</small></span><strong>− {money(preview.pension)}</strong></div><div><span>ARL <small>{deductions.arl_percent}% del pago base</small></span><strong>− {money(preview.arl)}</strong></div><div><span>{deductions.other_label || 'Otros conceptos'}</span><strong>− {money(preview.other)}</strong></div></div>
      </article>
      <aside className="review-side"><article className="panel deduction-config"><div className="section-title compact"><span><Calculator size={19} /></span><div><h3>Parámetros</h3><p>Ajustables para esta liquidación</p></div></div><div className="mini-grid"><label>EPS (%)<input type="number" step="0.01" value={deductions.eps_percent} onChange={setDeduction('eps_percent')} /></label><label>Pensión (%)<input type="number" step="0.01" value={deductions.pension_percent} onChange={setDeduction('pension_percent')} /></label><label>ARL (%)<input type="number" step="0.01" value={deductions.arl_percent} onChange={setDeduction('arl_percent')} /></label><label>Otros ($)<input type="number" min="0" value={deductions.other_amount} onChange={setDeduction('other_amount')} /></label></div></article>
      <article className="total-card"><CircleDollarSign size={24} /><span>Neto a pagar</span><strong>{money(preview.net)}</strong><small>Devengado {money(preview.base + preview.bonus)}<br />Deducciones {money(preview.totalDeductions)}</small><button disabled={saving || preview.net < 0} onClick={liquidate}>{saving ? 'Registrando…' : 'Confirmar liquidación'} <ArrowRight size={17} /></button></article></aside>
    </section>}
  </div>;
}

