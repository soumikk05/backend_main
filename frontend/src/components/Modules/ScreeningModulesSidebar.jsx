import React, { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import {
  ShieldCheck,
  FileText,
  CheckCircle2,
  Scan,
  ScanFace,
  Activity,
  Zap,
} from 'lucide-react';
import { screeningApi } from '../../api/screening.api';
import './ScreeningModulesSidebar.css';

export const MODULE_LIST = [
  {
    id: 'pipeline',
    path: '/pipeline',
    label: 'Risk Pipeline',
    sublabel: 'Full Assessment',
    badge: 'PRIMARY',
    icon: ShieldCheck,
  },
  {
    id: 'ocr',
    path: '/ocr',
    label: 'OCR Extraction',
    sublabel: 'Neural Text & MRZ',
    badge: 'OCR',
    icon: FileText,
  },
  {
    id: 'validation',
    path: '/validation',
    label: 'Doc Validation',
    sublabel: 'Rule Engine & ICAO',
    badge: 'RULES',
    icon: CheckCircle2,
  },
  {
    id: 'tampering',
    path: '/tampering',
    label: 'Tampering Anal',
    sublabel: 'ELA + CNN Forgery',
    badge: 'FORENSIC',
    icon: Scan,
  },
  {
    id: 'face',
    path: '/face',
    label: 'Face Verificat',
    sublabel: 'Biometrics & Livenes',
    badge: 'DEEPFACE',
    icon: ScanFace,
  },
];

export function ScreeningModulesSidebar({ activeId = 'pipeline', onSelectModule }) {
  const [healthStatus, setHealthStatus] = useState({
    online: true,
    pingMs: 34,
    version: '0.3.0',
  });

  const probeHealth = async () => {
    const start = performance.now();
    try {
      const data = await screeningApi.checkHealth();
      const elapsed = Math.round(performance.now() - start);
      setHealthStatus({
        online: true,
        pingMs: elapsed,
        version: data?.version || '0.3.0',
      });
    } catch {
      setHealthStatus((prev) => ({
        ...prev,
        online: false,
      }));
    }
  };

  useEffect(() => {
    probeHealth();
    const timer = setInterval(probeHealth, 20000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="screening-modules-panel">
      {/* Top Header */}
      <div className="screening-modules-panel__header">
        <div className="flex items-center gap-2">
          <Zap size={14} className="text-cyan-400" />
          <span className="screening-modules-panel__title">SCREENING MODULES</span>
        </div>
        <span className="screening-modules-panel__active-badge">
          5 ACTIVE
        </span>
      </div>

      {/* Nav List */}
      <div className="screening-modules-panel__nav">
        {MODULE_LIST.map((item) => {
          const isActive = activeId === item.id;
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectModule && onSelectModule(item.id)}
              className={`screening-modules-panel__item ${isActive ? 'screening-modules-panel__item--active' : ''}`}
            >
              {isActive && (
                <motion.div
                  layoutId="activeModuleIndicator"
                  className="screening-modules-panel__active-indicator"
                  transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                />
              )}

              <Icon size={18} className="screening-modules-panel__icon" />

              <div className="screening-modules-panel__label-col">
                <span className="screening-modules-panel__label-title">{item.label}</span>
                <span className="screening-modules-panel__label-sub">{item.sublabel}</span>
              </div>

              <span className="screening-modules-panel__badge">{item.badge}</span>
            </button>
          );
        })}
      </div>

      {/* Health & Latency Info at Bottom */}
      <div className="screening-modules-panel__footer">
        <div className="screening-modules-panel__footer-row">
          <span className="flex items-center gap-1.5 text-slate-400">
            <Activity size={12} className="text-emerald-400" /> Latency
          </span>
          <span className="font-mono text-emerald-400 font-semibold">
            {healthStatus.online ? `${healthStatus.pingMs}ms` : 'Offline'}
          </span>
        </div>
        <div className="screening-modules-panel__footer-row">
          <span className="text-slate-400">Engine</span>
          <span className="font-mono text-cyan-400 font-semibold">
            {healthStatus.version}
          </span>
        </div>
      </div>
    </div>
  );
}
