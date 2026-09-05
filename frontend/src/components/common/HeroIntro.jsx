import React, { useRef, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';
import { CyberText } from './CyberText';

gsap.registerPlugin(ScrollTrigger, useGSAP);

const FRAME_COUNT = 1794;

export function HeroIntro({ onComplete }) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const [loaded, setLoaded] = useState(false);

  // Preload images
  const imagesRef = useRef([]);
  const frameRef = useRef({ current: 1 });

  useGSAP(() => {
    // 1. Preload images
    const images = [];
    let loadedCount = 0;
    for (let i = 1; i <= FRAME_COUNT; i++) {
      const img = new Image();
      img.src = `/frames/frame_${i.toString().padStart(4, '0')}.jpg`;
      img.onload = () => {
        loadedCount++;
        if (loadedCount === Math.floor(FRAME_COUNT / 10)) {
          // Start when 10% is loaded to not block UI forever
          setLoaded(true);
        }
      };
      images.push(img);
    }
    imagesRef.current = images;

    // 2. Render function
    const render = () => {
      if (!canvasRef.current || !imagesRef.current[frameRef.current.current - 1]) return;
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      const img = imagesRef.current[frameRef.current.current - 1];

      // Draw covering full canvas
      if (img.complete && img.naturalHeight !== 0) {
        const ratio = Math.max(canvas.width / img.width, canvas.height / img.height);
        const centerShift_x = (canvas.width - img.width * ratio) / 2;
        const centerShift_y = (canvas.height - img.height * ratio) / 2;

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(
          img,
          0,
          0,
          img.width,
          img.height,
          centerShift_x,
          centerShift_y,
          img.width * ratio,
          img.height * ratio
        );
      }
    };

    // Initial render
    const resizeCanvas = () => {
      if (canvasRef.current) {
        canvasRef.current.width = window.innerWidth;
        canvasRef.current.height = window.innerHeight;
        render();
      }
    };
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    // 3. ScrollTrigger GSAP Animation
    // We create a timeline that scrubs through frames
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: containerRef.current,
        start: 'top top',
        end: '+=1000%',
        scrub: 0.5, // buttery smooth scrub
        pin: true,
        onUpdate: render,
        onLeave: () => {
          if (onComplete) onComplete();
        },
        onEnterBack: () => {
          if (onComplete) onComplete(false);
        }
      }
    });

    // Animate the frame index
    tl.to(frameRef.current, {
      current: FRAME_COUNT,
      snap: 'current',
      ease: 'none',
      duration: 1
    }, 0);

    // Fade out the canvas at the very end
    tl.to(canvasRef.current, { opacity: 0, duration: 0.1 }, 0.9);

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      ScrollTrigger.getAll().forEach(t => t.kill());
    };
  }, { scope: containerRef });

  return (
    <div ref={containerRef} className="relative w-full z-50 pointer-events-none" style={{ height: '100vh', background: 'transparent' }}>
      {!loaded && (
        <div className="absolute inset-0 flex items-center justify-center text-white z-50">
          <CyberText text="INITIALIZING SYSTEM..." />
        </div>
      )}
      
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full object-cover z-10"
      />
    </div>
  );
}
