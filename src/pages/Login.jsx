import { useState } from 'react';
import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail, ShieldCheck } from 'lucide-react';
import Brand from '../components/Brand';
import { api } from '../lib/api';

export default function Login({ onLogin }) {
  const [form, setForm] = useState({ email: 'admin@nominaclara.co', password: 'Nomina2026!' });
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const submit = async (e) => {
    e.preventDefault(); setLoading(true); setError('');
    try { const data = await api.login(form); localStorage.setItem('nomina_token', data.token); onLogin(data.user); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };
  return <main className="login-shell">
    <div className="login-orb orb-one" /><div className="login-orb orb-two" />
    <section className="login-story">
      <Brand light />
      <div className="story-copy">
        <span className="eyebrow light">Gestión laboral confiable</span>
        <h1>La nómina de su equipo, clara y bajo control.</h1>
        <p>Administre empleados, liquide periodos y conserve un historial verificable desde un solo lugar.</p>
        <div className="trust-line"><ShieldCheck size={19} /><span>Información protegida y trazable</span></div>
      </div>
      <small>© 2026 Nómina Clara · Uso administrativo</small>
    </section>
    <section className="login-panel">
      <form className="login-card" onSubmit={submit}>
        <div className="mobile-brand"><Brand /></div>
        <span className="eyebrow">Acceso administrativo</span>
        <h2>Bienvenido de nuevo</h2>
        <p className="form-intro">Ingrese sus credenciales para continuar al panel de nómina.</p>
        <label>Correo corporativo<div className="input-icon"><Mail size={18} /><input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div></label>
        <label>Contraseña<div className="input-icon"><LockKeyhole size={18} /><input type={show ? 'text' : 'password'} required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /><button type="button" onClick={() => setShow(!show)} aria-label="Mostrar contraseña">{show ? <EyeOff size={18} /> : <Eye size={18} />}</button></div></label>
        <div className="login-options"><label className="check-label"><input type="checkbox" defaultChecked /> <span>Recordar sesión</span></label><button type="button" className="text-button">Soporte de acceso</button></div>
        {error && <div className="form-error">{error}</div>}
        <button className="primary-button login-button" disabled={loading}>{loading ? <span className="spinner" /> : <><span>Ingresar al panel</span><ArrowRight size={18} /></>}</button>
        <p className="demo-note">Acceso de demostración diligenciado para evaluación local.</p>
      </form>
    </section>
  </main>;
}

