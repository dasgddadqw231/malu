"use client";

import { useEffect, useCallback, useRef } from "react";

// JARVIS UI sound generator - metallic clicks + power-up swoosh
function createJarvisAudio() {
  let ctx: AudioContext | null = null;

  const getCtx = () => {
    if (!ctx) ctx = new AudioContext();
    return ctx;
  };

  // Short noise buffer for metallic transients (50ms)
  let noiseBuffer: AudioBuffer | null = null;
  const getNoise = (c: AudioContext) => {
    if (noiseBuffer && noiseBuffer.sampleRate === c.sampleRate) return noiseBuffer;
    const len = Math.floor(c.sampleRate * 0.05);
    noiseBuffer = c.createBuffer(1, len, c.sampleRate);
    const data = noiseBuffer.getChannelData(0);
    for (let i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
    return noiseBuffer;
  };

  // Long noise buffer for boot swoosh (1.5s)
  let swooshBuffer: AudioBuffer | null = null;
  const getSwoosh = (c: AudioContext) => {
    if (swooshBuffer && swooshBuffer.sampleRate === c.sampleRate) return swooshBuffer;
    const len = Math.floor(c.sampleRate * 1.5);
    swooshBuffer = c.createBuffer(1, len, c.sampleRate);
    const data = swooshBuffer.getChannelData(0);
    for (let i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
    return swooshBuffer;
  };

  return {
    // Iron Man boot-up "슈우우웅" power-up swoosh (~1.4s)
    boot() {
      try {
        const c = getCtx();
        const t = c.currentTime;
        const dur = 1.4;

        // Layer 1: Rising sawtooth sweep — the core "슈우웅"
        const sweep = c.createOscillator();
        sweep.type = "sawtooth";
        sweep.frequency.setValueAtTime(80, t);
        sweep.frequency.exponentialRampToValueAtTime(600, t + dur * 0.7);
        sweep.frequency.exponentialRampToValueAtTime(400, t + dur);
        const sweepFilter = c.createBiquadFilter();
        sweepFilter.type = "lowpass";
        sweepFilter.frequency.setValueAtTime(200, t);
        sweepFilter.frequency.exponentialRampToValueAtTime(4000, t + dur * 0.6);
        sweepFilter.frequency.exponentialRampToValueAtTime(1500, t + dur);
        sweepFilter.Q.setValueAtTime(3, t);
        const sweepGain = c.createGain();
        sweepGain.gain.setValueAtTime(0.001, t);
        sweepGain.gain.linearRampToValueAtTime(0.07, t + dur * 0.3);
        sweepGain.gain.linearRampToValueAtTime(0.05, t + dur * 0.7);
        sweepGain.gain.exponentialRampToValueAtTime(0.001, t + dur);
        sweep.connect(sweepFilter);
        sweepFilter.connect(sweepGain);
        sweepGain.connect(c.destination);
        sweep.start(t);
        sweep.stop(t + dur + 0.1);

        // Layer 2: Filtered noise whoosh — the "air" texture
        const whoosh = c.createBufferSource();
        whoosh.buffer = getSwoosh(c);
        const whooshBp = c.createBiquadFilter();
        whooshBp.type = "bandpass";
        whooshBp.frequency.setValueAtTime(300, t);
        whooshBp.frequency.exponentialRampToValueAtTime(3000, t + dur * 0.5);
        whooshBp.frequency.exponentialRampToValueAtTime(1200, t + dur);
        whooshBp.Q.setValueAtTime(1.5, t);
        const whooshGain = c.createGain();
        whooshGain.gain.setValueAtTime(0.001, t);
        whooshGain.gain.linearRampToValueAtTime(0.06, t + dur * 0.4);
        whooshGain.gain.exponentialRampToValueAtTime(0.001, t + dur);
        whoosh.connect(whooshBp);
        whooshBp.connect(whooshGain);
        whooshGain.connect(c.destination);
        whoosh.start(t);
        whoosh.stop(t + dur + 0.1);

        // Layer 3: Sub bass hum — the reactor power feel
        const sub = c.createOscillator();
        sub.type = "sine";
        sub.frequency.setValueAtTime(50, t);
        sub.frequency.linearRampToValueAtTime(120, t + dur * 0.8);
        sub.frequency.linearRampToValueAtTime(80, t + dur);
        const subGain = c.createGain();
        subGain.gain.setValueAtTime(0.001, t);
        subGain.gain.linearRampToValueAtTime(0.06, t + dur * 0.3);
        subGain.gain.linearRampToValueAtTime(0.04, t + dur * 0.8);
        subGain.gain.exponentialRampToValueAtTime(0.001, t + dur);
        sub.connect(subGain);
        subGain.connect(c.destination);
        sub.start(t);
        sub.stop(t + dur + 0.1);

        // Layer 4: High shimmer — the "energy" sparkle at the peak
        const shimmer = c.createOscillator();
        shimmer.type = "sine";
        shimmer.frequency.setValueAtTime(1200, t + dur * 0.3);
        shimmer.frequency.exponentialRampToValueAtTime(2400, t + dur * 0.7);
        shimmer.frequency.exponentialRampToValueAtTime(1800, t + dur);
        const shimmerGain = c.createGain();
        shimmerGain.gain.setValueAtTime(0.001, t);
        shimmerGain.gain.setValueAtTime(0.001, t + dur * 0.25);
        shimmerGain.gain.linearRampToValueAtTime(0.02, t + dur * 0.5);
        shimmerGain.gain.exponentialRampToValueAtTime(0.001, t + dur);
        shimmer.connect(shimmerGain);
        shimmerGain.connect(c.destination);
        shimmer.start(t);
        shimmer.stop(t + dur + 0.1);
      } catch {}
    },
    // Metallic "철컥" click
    click() {
      try {
        const c = getCtx();
        const t = c.currentTime;

        const noiseSrc = c.createBufferSource();
        noiseSrc.buffer = getNoise(c);
        const bp = c.createBiquadFilter();
        bp.type = "bandpass";
        bp.frequency.setValueAtTime(4000, t);
        bp.Q.setValueAtTime(8, t);
        const noiseGain = c.createGain();
        noiseGain.gain.setValueAtTime(0.12, t);
        noiseGain.gain.exponentialRampToValueAtTime(0.001, t + 0.035);
        noiseSrc.connect(bp);
        bp.connect(noiseGain);
        noiseGain.connect(c.destination);
        noiseSrc.start(t);
        noiseSrc.stop(t + 0.04);

        const thump = c.createOscillator();
        thump.type = "sine";
        thump.frequency.setValueAtTime(150, t);
        thump.frequency.exponentialRampToValueAtTime(60, t + 0.04);
        const thumpGain = c.createGain();
        thumpGain.gain.setValueAtTime(0.08, t);
        thumpGain.gain.exponentialRampToValueAtTime(0.001, t + 0.05);
        thump.connect(thumpGain);
        thumpGain.connect(c.destination);
        thump.start(t);
        thump.stop(t + 0.06);

        const snap = c.createOscillator();
        snap.type = "square";
        snap.frequency.setValueAtTime(3200, t);
        snap.frequency.exponentialRampToValueAtTime(800, t + 0.015);
        const snapGain = c.createGain();
        snapGain.gain.setValueAtTime(0.04, t);
        snapGain.gain.exponentialRampToValueAtTime(0.001, t + 0.02);
        snap.connect(snapGain);
        snapGain.connect(c.destination);
        snap.start(t);
        snap.stop(t + 0.025);
      } catch {}
    },
    // Soft metallic hover tick
    hover() {
      try {
        const c = getCtx();
        const t = c.currentTime;

        const noiseSrc = c.createBufferSource();
        noiseSrc.buffer = getNoise(c);
        const hp = c.createBiquadFilter();
        hp.type = "highpass";
        hp.frequency.setValueAtTime(6000, t);
        hp.Q.setValueAtTime(4, t);
        const gain = c.createGain();
        gain.gain.setValueAtTime(0.025, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.02);
        noiseSrc.connect(hp);
        hp.connect(gain);
        gain.connect(c.destination);
        noiseSrc.start(t);
        noiseSrc.stop(t + 0.025);
      } catch {}
    },
  };
}

// Singleton so boot sound shares AudioContext with click effects
let sharedAudio: ReturnType<typeof createJarvisAudio> | null = null;
function getSharedAudio() {
  if (!sharedAudio) sharedAudio = createJarvisAudio();
  return sharedAudio;
}

// Component that plays boot swoosh on mount — disabled
export function BootSound() {
  return null;
}

export function ClickEffects() {
  const lastHoverTarget = useRef<Element | null>(null);

  const getAudio = useCallback(() => getSharedAudio(), []);

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
      getAudio().click();
    };

    const handleTouchStart = (e: TouchEvent) => {
      const touch = e.touches[0];
      const target = e.target as HTMLElement;
      const card = target.closest(".jarvis-card-interactive, .hud-stat-interactive, .jarvis-btn-interactive");
      if (card) {
        spawnRipple(card as HTMLElement, touch.clientX, touch.clientY);
      }
      spawnParticles(touch.clientX, touch.clientY);
      getAudio().click();
    };

    const handleMouseMove = (e: MouseEvent) => {
      const target = e.target as HTMLElement;

      const btn = target.closest(".jarvis-btn-interactive, .hud-stat-interactive") as HTMLElement;
      if (btn) {
        const rect = btn.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        btn.style.setProperty("--glow-x", `${x}%`);
        btn.style.setProperty("--glow-y", `${y}%`);
      }

      const interactive = target.closest(
        "button, a, .jarvis-card-interactive, .jarvis-btn-interactive, .hud-stat-interactive, .jarvis-nav-link"
      );
      if (interactive && interactive !== lastHoverTarget.current) {
        lastHoverTarget.current = interactive;
        getAudio().hover();
      } else if (!interactive) {
        lastHoverTarget.current = null;
      }
    };

    window.addEventListener("click", handleClick);
    window.addEventListener("touchstart", handleTouchStart, { passive: true });
    window.addEventListener("mousemove", handleMouseMove, { passive: true });

    return () => {
      window.removeEventListener("click", handleClick);
      window.removeEventListener("touchstart", handleTouchStart);
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, [spawnParticles, spawnRipple, getAudio]);

  return null;
}
