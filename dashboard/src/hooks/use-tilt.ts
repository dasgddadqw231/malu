"use client";

import { useRef, useCallback, type RefObject } from "react";

export function useTilt<T extends HTMLElement>(enabled = true): {
  ref: RefObject<T | null>;
  handlers: {
    onMouseMove: (e: React.MouseEvent) => void;
    onMouseLeave: () => void;
    onTouchMove: (e: React.TouchEvent) => void;
    onTouchEnd: () => void;
  };
} {
  const ref = useRef<T>(null);

  const applyTilt = useCallback((clientX: number, clientY: number) => {
    const el = ref.current;
    if (!el || !enabled) return;

    const rect = el.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    const rotateX = ((y - centerY) / centerY) * -8;
    const rotateY = ((x - centerX) / centerX) * 8;

    const glowX = (x / rect.width) * 100;
    const glowY = (y / rect.height) * 100;

    el.style.transform = `perspective(600px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
    el.style.setProperty("--glow-x", `${glowX}%`);
    el.style.setProperty("--glow-y", `${glowY}%`);
  }, [enabled]);

  const resetTilt = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    el.style.transform = "perspective(600px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)";
    el.style.setProperty("--glow-x", "50%");
    el.style.setProperty("--glow-y", "50%");
  }, []);

  const onMouseMove = useCallback(
    (e: React.MouseEvent) => applyTilt(e.clientX, e.clientY),
    [applyTilt]
  );

  const onTouchMove = useCallback(
    (e: React.TouchEvent) => {
      const touch = e.touches[0];
      applyTilt(touch.clientX, touch.clientY);
    },
    [applyTilt]
  );

  return {
    ref,
    handlers: {
      onMouseMove,
      onMouseLeave: resetTilt,
      onTouchMove,
      onTouchEnd: resetTilt,
    },
  };
}
