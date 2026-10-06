import { Calculator, History, LayoutDashboard, LogOut, Menu, Search, Users, X } from 'lucide-react';
import { useState } from 'react';
import Brand from './Brand';

const nav = [
  { id: 'dashboard', label: 'Resumen', icon: LayoutDashboard },
  { id: 'employees', label: 'Empleados', icon: Users },
  { id: 'payroll', label: 'Calcular nómina', icon: Calculator },
  { id: 'history', label: 'Historial', icon: History },
];

export default function Layout({ page, setPage, user, onLogout, children }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const select = (id) => { setPage(id); setMobileOpen(false); };
  return <div className="app-shell top-layout">
    <header className="app-header">
      <div className="header-primary">
        <div className="header-identity"><Brand /></div>
        <nav className={`header-nav ${mobileOpen ? 'nav-open' : ''}`}>{nav.map(({ id, label, icon: Icon }) => <button key={id} className={page === id ? 'active' : ''} onClick={() => select(id)}><Icon size={17} /><span>{label}</span></button>)}</nav>
        <div className="top-actions">
          <div className="global-search"><Search size={18} /><input placeholder="Buscar empleados o liquidaciones" /></div>
          <div className="header-user" title={`${user?.name} · ${user?.role}`}><span>{user?.name?.split(' ').map(x => x[0]).slice(0,2).join('')}</span></div>
          <button className="logout-button" onClick={onLogout} title="Cerrar sesión"><LogOut size={18} /></button>
          <button className="menu-button" onClick={() => setMobileOpen(!mobileOpen)} aria-label="Abrir navegación">{mobileOpen ? <X /> : <Menu />}</button>
        </div>
      </div>
    </header>
    <main className="content">{children}</main>
  </div>;
}
