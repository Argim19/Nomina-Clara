import { useCallback, useEffect, useState } from 'react';
import Layout from './components/Layout';
import Toast from './components/Toast';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Employees from './pages/Employees';
import Payroll from './pages/Payroll';
import History from './pages/History';
import { api } from './lib/api';

export default function App() {
  const [user, setUser] = useState(localStorage.getItem('nomina_token') ? { name: 'Catalina Gómez', role: 'Administradora de nómina' } : null);
  const [page, setPage] = useState('dashboard'); const [employees, setEmployees] = useState([]); const [payrolls, setPayrolls] = useState([]);
  const [dashboard, setDashboard] = useState({}); const [deductions, setDeductions] = useState({ eps_percent: 4, pension_percent: 4, arl_percent: 0 });
  const [loading, setLoading] = useState(true); const [toast, setToast] = useState(null);
  const notify = (message, type = 'success') => { setToast({ message, type }); window.setTimeout(() => setToast(null), 3800); };
  const load = useCallback(async () => { if (!user) return; setLoading(true); try { const [e, p, d, c] = await Promise.all([api.employees(), api.payrolls(), api.dashboard(), api.deductions()]); setEmployees(e); setPayrolls(p); setDashboard(d); setDeductions(c); } catch (err) { notify(err.message, 'error'); if (!localStorage.getItem('nomina_token')) setUser(null); } finally { setLoading(false); } }, [user]);
  useEffect(() => { load(); }, [load]);
  const createEmployee = async (payload) => { try { const result = await api.createEmployee(payload); setEmployees((old) => [result, ...old]); notify('Empleado registrado correctamente.'); return true; } catch (err) { notify(err.message, 'error'); return false; } };
  const updateEmployee = async (id, payload) => { try { const result = await api.updateEmployee(id, payload); setEmployees(old => old.map(e => e.id === id ? result : e)); notify('Información del empleado actualizada.'); return true; } catch (err) { notify(err.message, 'error'); return false; } };
  const createPayroll = async (payload) => {
    try {
      const result = await api.createPayroll(payload);
      setPayrolls(old => [result, ...old]);
      setDashboard(old => ({ ...old, payroll_count: (old.payroll_count || 0) + 1, current_payroll: (old.current_payroll || 0) + result.net_pay }));
      const emailDetail = result.email_dispatch?.message ? ` (${result.email_dispatch.message})` : '';
      notify(`Liquidación guardada en el histórico.${emailDetail}`);
      return result;
    } catch (err) {
      notify(err.message, 'error');
      return null;
    }
  };
  const prepareEmail = async (payroll) => {
    try {
      const result = await api.prepareEmail(payroll.id);
      notify(result.message || `Comprobante tramitado para ${payroll.employee_email}`);
    } catch (err) {
      notify(err.message, 'error');
    }
  };
  const logout = () => { localStorage.removeItem('nomina_token'); setUser(null); };
  if (!user) return <><Login onLogin={setUser} /><Toast toast={toast} onClose={() => setToast(null)} /></>;
  const pages = {
    dashboard: <Dashboard data={dashboard} loading={loading} goTo={setPage} />,
    employees: <Employees employees={employees} loading={loading} onCreate={createEmployee} onUpdate={updateEmployee} />,
    payroll: <Payroll employees={employees} deductions={deductions} onCreate={createPayroll} goHistory={() => setPage('history')} />,
    history: <History payrolls={payrolls} loading={loading} onEmail={prepareEmail} />,
  };
  return <><Layout page={page} setPage={setPage} user={user} onLogout={logout}>{pages[page]}</Layout><Toast toast={toast} onClose={() => setToast(null)} /></>;
}

