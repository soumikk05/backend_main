import { motion } from 'motion/react';
import {
  ArrowLeft,
  Activity,
  BarChart3,
  FileText,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { Card, ProgressBar, Badge } from '../common';
import { RiskGauge } from './RiskGauge';
import { OcrResults } from './OcrResults';
import { ValidationPanel } from './ValidationPanel';
import { TamperingPanel } from './TamperingPanel';
import { FacePanel } from './FacePanel';
import { FlagsList } from './FlagsList';
import { DashboardNav } from './DashboardNav';
import { AuditPanel, TimelinePanel } from './OperationsPanels';
import { scoreToHex } from '../../utils/helpers';
import { AnimatedCounter } from '../common/AnimatedBg';
import './Dashboard.css';

export function Dashboard({ result, onBack }) {
  if (!result) return null;

  const risk_score = result.risk_score ?? result.risk_summary?.risk_score ?? 0;
  const risk_label = result.risk_label ?? result.risk_summary?.risk_label ?? 'LOW';
  const flags = result.flags ?? result.risk_summary?.flags ?? [];

  const ocr = result.module_outputs?.ocr || result.ocr || {};
  const validation = result.module_outputs?.validation || result.modules?.validation;
  const tampering = result.module_outputs?.tampering || result.modules?.tampering;
  const face = result.module_outputs?.face || result.modules?.face;
  const timeline = result.timeline || {};
  const audit = result.audit || {};

  const component_scores = result.component_scores || {
    validation: validation?.overall_valid ? 100 : 0,
    tampering: tampering?.tampering_score || 0,
    face: face?.match ? 100 : 0
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="dashboard"
    >
      {/* Top bar */}
      <div className="dashboard__header-row">
        <motion.button
          whileHover={{ x: -3 }}
          whileTap={{ scale: 0.97 }}
          className="dashboard__back-btn"
          onClick={onBack}
        >
          <ArrowLeft size={15} />
          <span>New Scan</span>
        </motion.button>

        <div className="dashboard__timestamp-pill">
          <Activity size={12} />
          <span>{new Date().toLocaleTimeString()}</span>
        </div>
      </div>

      {/* Horizontal section tabs */}
      <DashboardNav />

      {/* Dashboard content — single column, dense */}
      <div className="dashboard__content">
        {/* Overview: gauge + scores + flags */}
        <div id="overview" className="scroll-mt-16">
          <div className="dashboard__hero-row">
            <Card>
              <RiskGauge score={risk_score} label={risk_label} />

              <div className="component-scores">
                {[
                  { key: 'validation', label: 'Rule Validation', weight: '30%', icon: ShieldCheck },
                  { key: 'tampering', label: 'Tampering / Forgery', weight: '35%', icon: Zap },
                  { key: 'face', label: 'Face Verification', weight: '25%', icon: Activity },
                  { key: 'ocr_confidence', label: 'OCR Extraction', weight: '10%', icon: FileText },
                ].map(({ key, label, weight, icon: ScoreIcon }, idx) => {
                  const val = component_scores[key] ?? 0;
                  const color = scoreToHex(val);
                  return (
                    <motion.div
                      key={key}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.2 + idx * 0.08 }}
                      whileHover={{ scale: 1.01 }}
                      className="component-score"
                    >
                      <div className="component-score__header">
                        <ScoreIcon size={13} style={{ color }} />
                        <span className="component-score__label">{label}</span>
                        <span className="component-score__weight">{weight}</span>
                      </div>
                      <div className="component-score__val-row">
                        <span className="component-score__value" style={{ color }}>
                          <AnimatedCounter value={val} duration={1.2} />
                        </span>
                        <span className="component-score__max">/100</span>
                      </div>
                      <ProgressBar value={val} color={color} />
                    </motion.div>
                  );
                })}
              </div>
            </Card>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <FlagsList flags={flags} />

              <Card
                icon={BarChart3}
                title="Summary"
                subtitle="Aggregated risk assessment"
              >
                <div className="summary-stats-grid">
                  <div className="summary-stat">
                    <div className="summary-stat__label">Risk Score</div>
                    <div className="summary-stat__val" style={{ color: scoreToHex(risk_score) }}>
                      <AnimatedCounter value={risk_score} duration={1.2} />
                      <span className="summary-stat__unit">/100</span>
                    </div>
                  </div>

                  <div className="summary-stat">
                    <div className="summary-stat__label">Verdict</div>
                    <div className="summary-stat__val">
                      <Badge label={risk_label} variant={risk_label.toLowerCase()} />
                    </div>
                  </div>

                  <div className="summary-stat">
                    <div className="summary-stat__label">Document</div>
                    <div className="summary-stat__val mono" style={{ fontSize: '0.75rem' }}>
                      {ocr?.document_type || 'Unknown'}
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>

        <div id="ocr" className="scroll-mt-16">
          <OcrResults ocr={ocr} />
        </div>

        <div id="validation" className="scroll-mt-16">
          <ValidationPanel validation={validation} />
        </div>

        <div id="tampering" className="scroll-mt-16">
          <TamperingPanel tampering={tampering} />
        </div>

        <div id="face" className="scroll-mt-16">
          <FacePanel face={face} />
        </div>

        <TimelinePanel timeline={timeline} />
        <AuditPanel audit={audit} />
      </div>
    </motion.div>
  );
}
