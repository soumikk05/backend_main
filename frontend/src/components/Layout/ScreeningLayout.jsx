import { motion } from 'motion/react';
import { Sidebar } from './Sidebar';

export function ScreeningLayout({ children }) {
  return (
    <div className="pt-24 min-h-screen container mx-auto px-4 max-w-7xl pb-20">
      <div className="flex flex-col lg:flex-row gap-8 items-start">
        {/* Left Sticky Sidebar */}
        <Sidebar />

        {/* Right Active Module Viewport */}
        <motion.main
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="flex-1 w-full min-w-0"
        >
          {children}
        </motion.main>
      </div>
    </div>
  );
}
