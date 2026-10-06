import { ArrowRight, Calculator, CalendarDays, CircleDollarSign, Clock3, UserPlus, Users } from 'lucide-react';
import { money, periodLabel, shortDate } from '../lib/format';
import Skeleton from '../components/Skeleton';

export default function Dashboard({ data, loading, goTo }) {
  if (loading) return <Skeleton rows={6} />;
  const cards = [
    { label: 'Empleados activos', value: data.active_employees, helper: `${data.total_employees} registrados`, icon: Users, tone: 'blue' },
    { label: 'Nómina del periodo', value: money(data.current_payroll), helper: periodLabel(data.current_period), icon: CircleDollarSign, tone: 'green' },
    { label: 'Liquidaciones', value: data.payroll_count, helper: 'Histórico consolidado', icon: CalendarDays, tone: 'gold' },
  ];
  return <div className="page-stack">
    <section className="welcome-row">
      <div><span className="eyebrow">Panorama general</span><h2>Buenos días, Catalina.</h2><p>Estos son los movimientos más relevantes de su operación de nómina.</p></div>
      <button className="primary-button" onClick={() => goTo('payroll')}><Calculator size={18} />Nueva liquidación</button>
    </section>
    <section className="metric-grid">{cards.map(({ label, value, helper, icon: Icon, tone }) => <article className="metric-card" key={label}><div><span>{label}</span><strong>{value}</strong><small>{helper}</small></div><span className={`metric-icon ${tone}`}><Icon size={22} /></span></article>)}</section>
    <section className="dashboard-grid">
      <article className="panel recent-panel">
        <div className="panel-head"><div><h3>Actividad reciente</h3><p>Últimas liquidaciones registradas</p></div><button className="text-button" onClick={() => goTo('history')}>Ver historial <ArrowRight size={16} /></button></div>
        <div className="activity-list">{data.recent_payrolls?.length ? data.recent_payrolls.map((item) => <div className="activity" key={item.id}><span className="activity-avatar">{item.employee_name.split(' ').map(x => x[0]).slice(0,2).join('')}</span><div><strong>{item.employee_name}</strong><span>{periodLabel(item.period)} · {item.hours} horas</span></div><div className="activity-amount"><strong>{money(item.net_pay)}</strong><span>{shortDate(item.created_at)}</span></div></div>) : <div className="activity-empty">Todavía no hay liquidaciones. Cree la primera para iniciar el histórico.</div>}</div>
      </article>
      <article className="panel quick-panel">
        <div className="panel-head"><div><h3>Acciones rápidas</h3><p>Atajos de gestión frecuente</p></div></div>
        <button onClick={() => goTo('employees')}><span className="quick-icon"><UserPlus size={20} /></span><div><strong>Registrar empleado</strong><small>Crear una nueva ficha laboral</small></div><ArrowRight size={17} /></button>
        <button onClick={() => goTo('payroll')}><span className="quick-icon green"><Calculator size={20} /></span><div><strong>Calcular nómina</strong><small>Liquidar un periodo de pago</small></div><ArrowRight size={17} /></button>
        <div className="cutoff-note"><Clock3 size={18} /><div><strong>Cierre sugerido</strong><span>Valide novedades antes del último día hábil.</span></div></div>
      </article>
    </section>
  </div>;
}

