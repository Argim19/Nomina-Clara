import { CheckCircle2, XCircle, X } from 'lucide-react';

export default function Toast({ toast, onClose }) {
  if (!toast) return null;
  return <div className={`toast ${toast.type === 'error' ? 'toast-error' : ''}`} role="status">
    {toast.type === 'error' ? <XCircle size={20} /> : <CheckCircle2 size={20} />}
    <span>{toast.message}</span>
    <button onClick={onClose} aria-label="Cerrar notificación"><X size={16} /></button>
  </div>;
}

