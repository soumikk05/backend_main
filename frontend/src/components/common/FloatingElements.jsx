import { useEffect, useState } from 'react';
import { motion } from 'motion/react';

const ELEMENTS = [
  "[ DATA STREAM ACTIVE ]",
  "SYS_OP_0991",
  "01001011 01100101",
  "AUTH_OK",
  "ENCRYPT_LAYER_7",
  "0x8F9A2B",
  "[ PACKET TRACE ]",
  "192.168.1.104",
  "SECURE_CONN_ESTABLISHED",
  "< SYNCING >",
  "CYBER_PROTOCOL_01",
  "[ FORENSIC_SCAN_RUNNING ]"
];

export function FloatingElements() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    // Generate random elements on mount
    const newItems = Array.from({ length: 8 }).map((_, i) => ({
      id: i,
      text: ELEMENTS[Math.floor(Math.random() * ELEMENTS.length)],
      startX: Math.random() * 100,
      startY: Math.random() * 100,
      duration: Math.random() * 20 + 20, // 20-40s
      delay: Math.random() * -20, // Negative delay to start mid-animation
      direction: Math.random() > 0.5 ? 1 : -1,
      scale: Math.random() * 0.5 + 0.5,
      color: Math.random() > 0.8 ? 'text-emerald-400' : 'text-cyan-500'
    }));
    setItems(newItems);
  }, []);

  return (
    <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
      {items.map((item) => (
        <motion.div
          key={item.id}
          className={`absolute whitespace-nowrap font-mono text-xs opacity-20 drop-shadow-[0_0_8px_rgba(34,211,238,0.5)] ${item.color}`}
          initial={{ 
            x: `${item.startX}vw`, 
            y: `${item.startY}vh`,
            opacity: 0
          }}
          animate={{
            x: [`${item.startX}vw`, `${item.startX + (20 * item.direction)}vw`, `${item.startX + (40 * item.direction)}vw`],
            y: [`${item.startY}vh`, `${item.startY - 10}vh`, `${item.startY + 20}vh`],
            opacity: [0, 0.4, 0.2, 0]
          }}
          transition={{
            duration: item.duration,
            repeat: Infinity,
            ease: "linear",
            delay: item.delay,
            times: [0, 0.5, 1]
          }}
          style={{ scale: item.scale }}
        >
          {item.text}
        </motion.div>
      ))}
    </div>
  );
}
