import { motion } from 'motion/react';
import { Eye, Smile, ArrowLeft, ArrowRight, Sparkles } from 'lucide-react';

const CHALLENGE_CONFIG = {
  blink: {
    title: 'Please blink naturally',
    subtitle: 'Close and open your eyes once',
    icon: Eye,
    cueAnimation: {
      scale: [1, 0.8, 1.1, 1],
      opacity: [1, 0.5, 1, 1],
      transition: { repeat: Infinity, duration: 1.5, ease: 'easeInOut' },
    },
  },
  smile: {
    title: 'Please smile',
    subtitle: 'Show a clear, natural smile',
    icon: Smile,
    cueAnimation: {
      scale: [1, 1.2, 1],
      rotate: [0, 5, -5, 0],
      transition: { repeat: Infinity, duration: 1.8, ease: 'easeInOut' },
    },
  },
  turn_left: {
    title: 'Please turn your head to the left',
    subtitle: 'Slowly turn your head towards your left side',
    icon: ArrowLeft,
    cueAnimation: {
      x: [0, -12, 0],
      transition: { repeat: Infinity, duration: 1.2, ease: 'easeInOut' },
    },
  },
  turn_right: {
    title: 'Please turn your head to the right',
    subtitle: 'Slowly turn your head towards your right side',
    icon: ArrowRight,
    cueAnimation: {
      x: [0, 12, 0],
      transition: { repeat: Infinity, duration: 1.2, ease: 'easeInOut' },
    },
  },
};

export function ChallengeInstruction({ challenge }) {
  const config = CHALLENGE_CONFIG[challenge] || {
    title: 'Follow the on-screen prompt',
    subtitle: 'Keep your face inside the target box',
    icon: Sparkles,
    cueAnimation: {},
  };

  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="challenge-box"
    >
      <div className="flex items-center gap-3">
        <motion.div
          animate={config.cueAnimation}
          className="w-10 h-10 rounded-xl bg-cyan-500/20 border border-cyan-400/40 flex items-center justify-center text-cyan-300 shadow-[0_0_15px_rgba(6,182,212,0.3)] shrink-0"
        >
          <Icon size={20} />
        </motion.div>

        <div className="flex-1">
          <div className="text-xs font-mono uppercase tracking-wider text-cyan-400 font-bold flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
            <span>ACTIVE CHALLENGE:</span>
          </div>
          <div className="text-sm font-bold font-mono text-white mt-0.5">
            {config.title}
          </div>
          <div className="text-[11px] font-mono text-slate-300">
            {config.subtitle}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
