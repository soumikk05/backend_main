import { motion } from 'motion/react';
import { Target, Activity, FileText, Zap, ScanFace, Database } from 'lucide-react';

const navItems = [
  { id: 'overview', label: 'Overview', icon: Target },
  { id: 'ocr', label: 'Extracted Data', icon: FileText },
  { id: 'validation', label: 'Validation', icon: Activity },
  { id: 'tampering', label: 'Tampering', icon: Zap },
  { id: 'face', label: 'Biometrics', icon: ScanFace },
  { id: 'timeline', label: 'Metrics', icon: Activity },
  { id: 'audit', label: 'Audit Trail', icon: Database },
];

export const DashboardNav = () => {
  const scrollTo = (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <nav className="dashboard-tabs">
      <div className="dashboard-tabs__label">Sections</div>
      <div className="dashboard-tabs__list">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <motion.button
              key={item.id}
              onClick={() => scrollTo(item.id)}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              className="dashboard-tabs__tab"
            >
              <Icon size={11} />
              <span>{item.label}</span>
            </motion.button>
          );
        })}
      </div>
    </nav>
  );
};
