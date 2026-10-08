import { useMemo, useState } from 'react';
import { Download, Eye, FileClock, Mail, Search } from 'lucide-react';
import EmptyState from '../components/EmptyState';
import Modal from '../components/Modal';
import Skeleton from '../components/Skeleton';
import { money, periodLabel, shortDate } from '../lib/format';

export default function History({ payrolls, loading, onEmail }) {
  const [query, setQuery] = useState(''); const [selected, setSelected] = useState(null);
  const filtered = useMemo(() => payrolls.filter((p) => `${p.employee_name} ${p.code} ${p.period}`.toLowerCase().includes(query.toLowerCase())), [payrolls, query]);
  const print = () => window.print();
  return <div className="page-stack">
    <section className="page-heading"><div><span className="eyebrow">Trazabilidad</span><h2>Historial de nómina</h2><p>Consulte liquidaciones cerradas sin alterar sus valores originales.</p></div></section>
    <section className="panel table-panel"><div className="toolbar"><div className="search-field"><Search size={18} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar por empleado, periodo o consecutivo" /></div><span className="immutable-note">Registros protegidos contra edición</span></div>
    {loading ? <Skeleton /> : filtered.length ? <div className="table-scroll"><table><thead><tr><th>Consecutivo</th><th>Empleado</th><th>Periodo</th><th>Horas</th><th>Devengado</th><th>Deducciones</th><th>Neto pagado</th><th /></tr></thead><tbody>{filtered.map((p) => <tr key={p.id}><td><strong className="code">{p.code}</strong><small>{shortDate(p.created_at)}</small></td><td><strong>{p.employee_name}</strong><small>{p.employee_position}</small></td><td>{periodLabel(p.period)}</td><td>{p.hours}</td><td>{money(p.base_pay + p.child_bonus)}</td><td>{money(p.total_deductions)}</td><td><strong>{money(p.net_pay)}</strong></td><td><button className="table-action" onClick={() => setSelected(p)} title="Ver volante"><Eye size={17} /></button></td></tr>)}</tbody></table></div> : <EmptyState icon={FileClock} title="Sin liquidaciones registradas" description="Cuando confirme una nómina, aparecerá aquí con su información histórica." />}</section>
    <Modal open={!!selected} title="Volante de pago" subtitle={selected ? `${selected.code} · ${periodLabel(selected.period)}` : ''} onClose={() => setSelected(null)} wide>
      {selected && <div className="payslip" id="payslip"><div className="payslip-brand"><div><strong>NÓMINA</strong> CLARA<small>Comprobante de pago</small></div><span>{selected.code}</span></div><div className="payslip-info"><div><small>Empleado</small><strong>{selected.employee_name}</strong><span>CC {selected.employee_document}</span></div><div><small>Cargo</small><strong>{selected.employee_position}</strong><span>{selected.employee_email}</span></div><div><small>Periodo liquidado</small><strong>{periodLabel(selected.period)}</strong><span>{selected.hours} horas trabajadas</span></div></div><div className="payslip-table"><div className="pay-row pay-head"><span>Concepto</span><span>Devengado</span><span>Deducción</span></div><div className="pay-row"><span>Pago por horas</span><span>{money(selected.base_pay)}</span><span>—</span></div><div className="pay-row"><span>Bonificación por hijos</span><span>{money(selected.child_bonus)}</span><span>—</span></div><div className="pay-row"><span>EPS</span><span>—</span><span>{money(selected.eps_deduction)}</span></div><div className="pay-row"><span>Pensión</span><span>—</span><span>{money(selected.pension_deduction)}</span></div><div className="pay-row"><span>ARL</span><span>—</span><span>{money(selected.arl_deduction)}</span></div>{selected.other_deduction > 0 && <div className="pay-row"><span>Otros conceptos</span><span>—</span><span>{money(selected.other_deduction)}</span></div>}</div><div className="payslip-total"><span>Neto pagado</span><strong>{money(selected.net_pay)}</strong></div><p className="payslip-legal">Este comprobante corresponde a una liquidación cerrada y conserva los datos vigentes al momento de su registro.</p></div>}
      <div className="modal-actions print-hidden"><button className="secondary-button" onClick={() => onEmail(selected)}><Mail size={17} />Enviar al correo</button><button className="primary-button" onClick={print}><Download size={17} />Guardar como PDF</button></div>
    </Modal>
  </div>;
}

