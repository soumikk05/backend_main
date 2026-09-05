import { motion } from 'motion/react';

export function CaptureProgress({ progress = 0 }) {
  const radius = 32;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center p-3 gap-2">
      <div className="relative flex items-center justify-center">
        <svg className="w-20 h-20 transform -rotate-90">
          {/* Background circle */}
          <circle
            cx="40"
            cy="40"
            r={radius}
            stroke="rgba(255, 255, 255, 0.1)"
            strokeWidth="4"
            fill="transparent"
          />
          {/* Animated progress circle */}
          <motion.circle
            cx="40"
            cy="40"
            r={radius}
            stroke="#06B6D4"
            strokeWidth="4"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            transition={{ duration: 0.1, ease: 'linear' }}
          />
        </svg>

        {/* Center percentage / scanning text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center font-mono text-xs font-bold text-cyan-300">
          <span>{progress}%</span>
        </div>
      </div>

      <div className="text-[11px] font-mono text-cyan-400/90 uppercase tracking-wider animate-pulse">
        Sampling Motion Frames…
      </div>
    </div>
  );
}
