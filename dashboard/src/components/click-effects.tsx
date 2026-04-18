"use client";

import { useEffect, useCallback } from "react";

export function ClickEffects() {
  const spawnParticles = useCallback((x: number, y: number) => {
    const count = 6;
    for (let i = 0; i < count; i++) {
      const particle = document.createElement("div");
      particle.className = "click-particle";
      const angle = (360 / count) * i + Math.random() * 30;
      const distance = 30 + Math.random() * 40;
      const tx = Math.cos((angle * Math.PI) / 180) * distance;
      const ty = Math.sin((angle * Math.PI) / 180) * distance;
      particle.style.left = `${x}px`;
      particle.style.top = `${y}px`;
      particle.style.setProperty("--tx", `${tx}px`);
      particle.style.setProperty("--ty", `${ty}px`);
      document.body.appendChild(particle);
      setTimeout(() => particle.remove(), 600);
    }
  }, []);

  const spawnRipple = useCallback((target: HTMLElement, x: number, y: number) => {
    const rect = target.getBoundingClientRect();
    const ripple = document.createElement("div");
    ripple.className = "touch-ripple";
    ripple.style.left = `${x - rect.left}px`;
    ripple.style.top = `${y - rect.top}px`;
    target.appendChild(ripple);
    setTimeout(() => ripple.remove(), 600);
  }, []);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      spawnParticles(e.clientX, e.clientY);
    };

    const handleTouchStart = (e: TouchEvent) => {
      const touch = e.touches[0];
      const target = e.target as HTMLElement;
      const card = target.closest(".jarvis-card-interactive, .hud-stat-interactive, .jarvis-btn-interactive");
      if (card) {
        spawnRipple(card as HTMLElement, touch.clientX, touch.clientY);
      }
      spawnParticles(touch.clientX, touch.clientY);
    };

    // Button glow tracking
    const handleBtnMove = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const btn = target.closest(".jarvis-btn-interactive, .hud-stat-interactive") as HTMLElement;
      if (btn) {
        const rect = btn.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        btn.style.setProperty("--glow-x", `${x}%`);
        btn.style.setProperty("--glow-y", `${y}%`);
      }
    };

    window.addEventListener("click", handleClick);
    window.addEventListener("touchstart", handleTouchStart, { passive: true });
    window.addEventListener("mousemove", handleBtnMove, { passive: true });

    return () => {
      window.removeEventListener("click", handleClick);
      window.removeEventListener("touchstart", handleTouchStart);
      window.removeEventListener("mousemove", handleBtnMove);
    };
  }, [spawnParticles, spawnRipple]);

  return null;
}
