import { useEffect, useState, useRef } from 'react';
import { gsap } from 'gsap';
import { useGSAP } from '@gsap/react';

gsap.registerPlugin(useGSAP);

/**
 * Word-by-word staggered text reveal using GSAP and useGSAP.
 */
export function AnimatedText({ text, className = '', delay = 0 }) {
  const containerRef = useRef(null);
  const words = text.split(' ');

  useGSAP(() => {
    gsap.from('.anim-word-gsap', {
      y: 15,
      opacity: 0,
      filter: 'blur(4px)',
      duration: 0.6,
      stagger: 0.05,
      delay: delay,
      ease: 'back.out(1.7)',
    });
  }, { scope: containerRef });

  return (
    <span ref={containerRef} className={`animated-text ${className}`}>
      {words.map((word, index) => (
        <span
          key={index}
          className="anim-word-gsap"
          style={{ display: 'inline-block', marginRight: '0.28em' }}
        >
          {word}
        </span>
      ))}
    </span>
  );
}

/**
 * Animated number counter using requestAnimationFrame.
 */
export function AnimatedCounter({ value, duration = 1.4, decimals = 0, className = '' }) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    let startTimestamp = null;
    const target = Number(value) || 0;
    const durationMs = duration * 1000;
    let frameId;

    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / durationMs, 1);
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      const current = eased * target;

      setDisplayValue(decimals > 0 ? Number(current.toFixed(decimals)) : Math.round(current));

      if (progress < 1) {
        frameId = requestAnimationFrame(step);
      } else {
        setDisplayValue(decimals > 0 ? Number(target.toFixed(decimals)) : target);
      }
    };

    frameId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameId);
  }, [value, duration, decimals]);

  return <span className={className}>{displayValue}</span>;
}
