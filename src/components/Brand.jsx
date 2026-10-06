import { Landmark } from 'lucide-react';

export default function Brand({ compact = false, light = false }) {
  return <div className={`brand ${light ? 'brand-light' : ''}`}>
    <span className="brand-mark"><Landmark size={21} strokeWidth={2.2} /></span>
    {!compact && <span><strong>Nómina</strong> Clara</span>}
  </div>;
}

