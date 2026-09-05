import React, { useRef, useImperativeHandle, forwardRef } from 'react';
import { gsap } from 'gsap';
import { useGSAP } from '@gsap/react';

gsap.registerPlugin(useGSAP);

const CYBER_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*<>';

export const CyberText = forwardRef(({ text, className = '' }, ref) => {
  const containerRef = useRef(null);
  const charsRef = useRef([]);

  const { contextSafe } = useGSAP({ scope: containerRef });

  const scramble = contextSafe(() => {
    // Scramble effect
    charsRef.current.forEach((char, i) => {
      if (!char) return;
      const originalText = text[i];
      if (originalText === ' ') return;

      // Reset any running tweens on this char
      gsap.killTweensOf(char);

      gsap.to(char, {
        duration: 0.5,
        scale: 1.2,
        WebkitTextFillColor: '#0ea5e9',
        ease: 'power2.out',
        yoyo: true,
        repeat: 1,
        delay: i * 0.02,
        onUpdate: function () {
          // Randomly scramble during the first 70% of the tween
          if (this.progress() < 0.7) {
            char.innerText = CYBER_CHARS[Math.floor(Math.random() * CYBER_CHARS.length)];
          } else {
            char.innerText = originalText;
          }
        },
        onComplete: function () {
          char.innerText = originalText;
          gsap.set(char, { clearProps: "all" });
        }
      });
    });
  });

  useImperativeHandle(ref, () => ({
    scramble
  }));

  const handleMouseEnter = () => scramble();

  return (
    <span
      ref={containerRef}
      className={`inline-block cursor-crosshair ${className}`}
      onMouseEnter={handleMouseEnter}
      style={{ willChange: 'transform' }}
    >
      {text.split('').map((char, index) => (
        <span
          key={index}
          ref={(el) => (charsRef.current[index] = el)}
          style={{ display: 'inline-block', minWidth: char === ' ' ? '0.3em' : 'auto' }}
        >
          {char}
        </span>
      ))}
    </span>
  );
});
