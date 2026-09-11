import React, { useEffect, useRef } from 'react';

interface ThreeOrbViewProps {
  isSpeaking?: boolean;
  activeAgentsCount?: number;
}

export const ThreeOrbView: React.FC<ThreeOrbViewProps> = ({ isSpeaking = false, activeAgentsCount = 0 }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let angle = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const radius = 35 + (isSpeaking ? Math.sin(angle * 5) * 8 : Math.sin(angle) * 3);

      // Core Glowing Sphere
      const gradient = ctx.createRadialGradient(centerX, centerY, 5, centerX, centerY, radius);
      gradient.addColorStop(0, '#60a5fa');
      gradient.addColorStop(0.5, '#3b82f6');
      gradient.addColorStop(1, 'rgba(15, 23, 42, 0)');

      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();

      // Particle Rings
      const particleCount = 24 + activeAgentsCount * 6;
      for (let i = 0; i < particleCount; i++) {
        const particleAngle = angle + (i * (Math.PI * 2)) / particleCount;
        const particleDist = radius + 12 + Math.sin(angle * 2 + i) * 6;
        const px = centerX + Math.cos(particleAngle) * particleDist;
        const py = centerY + Math.sin(particleAngle) * particleDist;

        ctx.beginPath();
        ctx.arc(px, py, 2, 0, Math.PI * 2);
        ctx.fillStyle = i % 2 === 0 ? '#38bdf8' : '#818cf8';
        ctx.fill();
      }

      angle += 0.03;
      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [isSpeaking, activeAgentsCount]);

  return (
    <div className="flex items-center justify-center p-2">
      <canvas ref={canvasRef} width={120} height={120} className="rounded-full shadow-lg border border-cyan-500/30" />
    </div>
  );
};

export default ThreeOrbView;
