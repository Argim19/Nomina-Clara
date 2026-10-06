import { useMemo, useState } from 'react';
import { Edit3, Plus, Search, SlidersHorizontal, UserRoundX, Users } from 'lucide-react';
import Modal from '../components/Modal';
import EmptyState from '../components/EmptyState';
import Skeleton from '../components/Skeleton';
import { initials, money } from '../lib/format';

const emptyForm = { name: '', document: '', city: '', email: '', phone: '', position: '', hourly_rate: '', children: 0, status: 'Activo' };

function EmployeeForm({ initial, onSave, onClose, saving }) {
  const [form, setForm] = useState(initial || emptyForm);
  const change = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const submit = (e) => { e.preventDefault(); onSave({ ...form, hourly_rate: Number(form.hourly_rate), children: Number(form.children) }); };
  return <form onSubmit={submit}>
    <div className="form-grid">
      <label className="span-2">Nombre completo<input required value={form.name} onChange={change('name')} placeholder="Ej. Valentina Rojas Martínez" /></label>
      <label>Número de cédula<input required value={form.document} onChange={change('document')} placeholder="Sin puntos ni espacios" /></label>
      <label>Ciudad<input required value={form.city} onChange={change('city')} placeholder="Ciudad de residencia" /></label>
      <label>Correo corporativo<input required type="email" value={form.email} onChange={change('email')} placeholder="nombre@empresa.co" /></label>
      <label>Celular<input required value={form.phone} onChange={change('phone')} placeholder="300 000 0000" /></label>
      <label>Cargo<input required value={form.position} onChange={change('position')} placeholder="Cargo contractual" /></label>
      <label>Valor por hora<input required min="1" type="number" value={form.hourly_rate} onChange={change('hourly_rate')} placeholder="0" /></label>
      <label>Número de hijos<input required min="0" type="number" value={form.children} onChange={change('children')} /></label>
      <label>Estado<select value={form.status} onChange={change('status')}><option>Activo</option><option>Inactivo</option></select></label>
    </div>
    <div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancelar</button><button className="primary-button" disabled={saving}>{saving ? 'Guardando…' : initial ? 'Guardar cambios' : 'Registrar empleado'}</button></div>
  </form>;
}

export default function Employees({ employees, loading, onCreate, onUpdate }) {
  const [query, setQuery] = useState(''); const [filter, setFilter] = useState('Todos');
  const [modal, setModal] = useState(null); const [saving, setSaving] = useState(false);
  const filtered = useMemo(() => employees.filter((e) => (filter === 'Todos' || e.status === filter) && `${e.name} ${e.document} ${e.position}`.toLowerCase().includes(query.toLowerCase())), [employees, filter, query]);
  const save = async (payload) => { setSaving(true); const ok = modal?.id ? await onUpdate(modal.id, payload) : await onCreate(payload); setSaving(false); if (ok) setModal(null); };
  return <div className="page-stack">
    <section className="page-heading"><div><span className="eyebrow">Directorio laboral</span><h2>Empleados</h2><p>Administre la información contractual usada en cada liquidación.</p></div><button className="primary-button" onClick={() => setModal(emptyForm)}><Plus size={18} />Nuevo empleado</button></section>
    <section className="panel table-panel">
      <div className="toolbar"><div className="search-field"><Search size={18} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar por nombre, cédula o cargo" /></div><div className="filter-field"><SlidersHorizontal size={17} /><select value={filter} onChange={(e) => setFilter(e.target.value)}><option>Todos</option><option>Activo</option><option>Inactivo</option></select></div></div>
      {loading ? <Skeleton /> : filtered.length ? <div className="table-scroll"><table><thead><tr><th>Empleado</th><th>Identificación</th><th>Cargo</th><th>Valor hora</th><th>Hijos</th><th>Estado</th><th /></tr></thead><tbody>{filtered.map((e) => <tr key={e.id}><td><div className="person-cell"><span>{initials(e.name)}</span><div><strong>{e.name}</strong><small>{e.email}</small></div></div></td><td><strong className="regular">CC {e.document}</strong><small>{e.city}</small></td><td>{e.position}</td><td>{money(e.hourly_rate)}</td><td>{e.children}</td><td><span className={`status ${e.status === 'Activo' ? 'status-active' : 'status-inactive'}`}>{e.status}</span></td><td><button className="table-action" onClick={() => setModal(e)} title="Editar empleado"><Edit3 size={17} /></button></td></tr>)}</tbody></table></div> : <EmptyState icon={query ? UserRoundX : Users} title={query ? 'Sin coincidencias' : 'Aún no hay empleados'} description={query ? 'Ajuste la búsqueda o cambie el filtro seleccionado.' : 'Registre el primer empleado para comenzar a liquidar nómina.'} action={!query && <button className="secondary-button" onClick={() => setModal(emptyForm)}><Plus size={17} />Registrar empleado</button>} />}
      {!!filtered.length && <div className="table-foot"><span>Mostrando {filtered.length} de {employees.length} empleados</span><span>Información actualizada</span></div>}
    </section>
    <Modal open={!!modal} title={modal?.id ? 'Editar empleado' : 'Registrar empleado'} subtitle="La información quedará disponible para futuras liquidaciones." onClose={() => setModal(null)} wide><EmployeeForm initial={modal} onSave={save} onClose={() => setModal(null)} saving={saving} /></Modal>
  </div>;
}

