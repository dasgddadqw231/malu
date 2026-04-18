"use client";

import { useEffect, useRef } from "react";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
}

interface Arc {
  radius: number;
  speed: number;
  angle: number;
  width: number;
  sweep: number;
  alpha: number;
}

export function JarvisBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let width = 0;
    let height = 0;

    // Particles
    const particles: Particle[] = [];
    const PARTICLE_COUNT = 60;
    const CONNECTION_DIST = 150;

    // Rotating arcs around center
    const arcs: Arc[] = [
      { radius: 120, speed: 0.003, angle: 0, width: 1.5, sweep: Math.PI * 0.6, alpha: 0.25 },
      { radius: 120, speed: -0.003, angle: Math.PI, width: 1.5, sweep: Math.PI * 0.4, alpha: 0.2 },
      { radius: 180, speed: -0.002, angle: 0.5, width: 1, sweep: Math.PI * 0.8, alpha: 0.15 },
      { radius: 180, speed: 0.002, angle: Math.PI + 0.5, width: 1, sweep: Math.PI * 0.3, alpha: 0.12 },
      { radius: 240, speed: 0.0015, angle: 1, width: 0.8, sweep: Math.PI * 0.5, alpha: 0.1 },
      { radius: 240, speed: -0.0015, angle: Math.PI + 1, width: 0.8, sweep: Math.PI * 0.7, alpha: 0.08 },
      { radius: 300, speed: -0.001, angle: 2, width: 0.6, sweep: Math.PI * 0.4, alpha: 0.06 },
    ];

    // Radar sweep
    let radarAngle = 0;

    function resize() {
      const dpr = window.devicePixelRatio || 1;
      width = window.innerWidth;
      height = window.innerHeight;
      canvas!.width = width * dpr;
      canvas!.height = height * dpr;
      canvas!.style.width = `${width}px`;
      canvas!.style.height = `${height}px`;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);

      // Re-init particles on resize
      particles.length = 0;
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.5) * 0.3,
          vy: (Math.random() - 0.5) * 0.3,
          size: Math.random() * 2 + 0.5,
          alpha: Math.random() * 0.4 + 0.1,
        });
      }
    }

    function drawParticles() {
      if (!ctx) return;

      for (const p of particles) {
        // Move
        p.x += p.vx;
        p.y += p.vy;

        // Wrap around
        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        // Draw dot
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 212, 255, ${p.alpha})`;
        ctx.fill();
      }

      // Connection lines
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < CONNECTION_DIST) {
            const alpha = (1 - dist / CONNECTION_DIST) * 0.08;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(0, 212, 255, ${alpha})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
    }

    function drawArcs() {
      if (!ctx) return;

      const cx = width / 2;
      const cy = height / 2;

      for (const arc of arcs) {
        arc.angle += arc.speed;

        ctx.beginPath();
        ctx.arc(cx, cy, arc.radius, arc.angle, arc.angle + arc.sweep);
        ctx.strokeStyle = `rgba(0, 212, 255, ${arc.alpha})`;
        ctx.lineWidth = arc.width;
        ctx.stroke();
      }

      // Center dot
      ctx.beginPath();
      ctx.arc(cx, cy, 3, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(0, 212, 255, 0.3)";
      ctx.fill();

      // Center crosshair
      const crossSize = 15;
      ctx.beginPath();
      ctx.moveTo(cx - crossSize, cy);
      ctx.lineTo(cx + crossSize, cy);
      ctx.moveTo(cx, cy - crossSize);
      ctx.lineTo(cx, cy + crossSize);
      ctx.strokeStyle = "rgba(0, 212, 255, 0.1)";
      ctx.lineWidth = 0.5;
      ctx.stroke();
    }

    function drawRadarSweep() {
      if (!ctx) return;

      const cx = width / 2;
      const cy = height / 2;
      const maxRadius = 300;
      radarAngle += 0.005;

      // Sweep gradient
      const gradient = ctx.createConicGradient(radarAngle, cx, cy);
      gradient.addColorStop(0, "rgba(0, 212, 255, 0.06)");
      gradient.addColorStop(0.1, "rgba(0, 212, 255, 0)");
      gradient.addColorStop(1, "rgba(0, 212, 255, 0)");

      ctx.beginPath();
      ctx.arc(cx, cy, maxRadius, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();
    }

    function drawCornerHUD() {
      if (!ctx) return;

      const padding = 30;
      const lineLen = 50;
      const alpha = 0.12;

      ctx.strokeStyle = `rgba(0, 212, 255, ${alpha})`;
      ctx.lineWidth = 1;

      // Top-left
      ctx.beginPath();
      ctx.moveTo(padding, padding + lineLen);
      ctx.lineTo(padding, padding);
      ctx.lineTo(padding + lineLen, padding);
      ctx.stroke();

      // Top-right
      ctx.beginPath();
      ctx.moveTo(width - padding - lineLen, padding);
      ctx.lineTo(width - padding, padding);
      ctx.lineTo(width - padding, padding + lineLen);
      ctx.stroke();

      // Bottom-left
      ctx.beginPath();
      ctx.moveTo(padding, height - padding - lineLen);
      ctx.lineTo(padding, height - padding);
      ctx.lineTo(padding + lineLen, height - padding);
      ctx.stroke();

      // Bottom-right
      ctx.beginPath();
      ctx.moveTo(width - padding - lineLen, height - padding);
      ctx.lineTo(width - padding, height - padding);
      ctx.lineTo(width - padding, height - padding - lineLen);
      ctx.stroke();
    }

    function animate() {
      if (!ctx) return;

      ctx.clearRect(0, 0, width, height);

      drawRadarSweep();
      drawArcs();
      drawParticles();
      drawCornerHUD();

      animationId = requestAnimationFrame(animate);
    }

    resize();
    animate();
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(animationId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0 }}
      aria-hidden="true"
    />
  );
}
