"use client";

import { useState, useRef, useEffect, useCallback } from "react";

// JARVIS / Iron Man style BGM — cinematic, layered, evolving
function createBGM(ctx: AudioContext) {
  const master = ctx.createGain();
  master.gain.setValueAtTime(0, ctx.currentTime);
  master.connect(ctx.destination);

  const nodes: { stop: () => void }[] = [];
  const intervals: ReturnType<typeof setInterval>[] = [];

  // --- Reverb ---
  const convolver = ctx.createConvolver();
  const reverbLen = Math.floor(ctx.sampleRate * 2.5);
  const reverbBuf = ctx.createBuffer(2, reverbLen, ctx.sampleRate);
  for (let ch = 0; ch < 2; ch++) {
    const data = reverbBuf.getChannelData(ch);
    for (let i = 0; i < reverbLen; i++) {
      data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.9));
    }
  }
  convolver.buffer = reverbBuf;
  const reverbGain = ctx.createGain();
  reverbGain.gain.setValueAtTime(0.25, ctx.currentTime);
  convolver.connect(reverbGain);
  reverbGain.connect(master);

  const dryGain = ctx.createGain();
  dryGain.gain.setValueAtTime(0.75, ctx.currentTime);
  dryGain.connect(master);

  // ============================================================
  // Layer 1: Cinematic power drone (5th interval, warm + wide)
  // — The foundation. Like the arc reactor idling.
  // ============================================================
  const droneNotes = [55, 82.4, 110]; // A1, E2, A2 — open fifth + octave
  droneNotes.forEach((freq, i) => {
    // Two detuned oscillators per note for width
    [-4, 4].forEach((detune) => {
      const osc = ctx.createOscillator();
      osc.type = i === 0 ? "sawtooth" : "triangle";
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      osc.detune.setValueAtTime(detune, ctx.currentTime);
      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.setValueAtTime(250 + i * 100, ctx.currentTime);
      filter.Q.setValueAtTime(1, ctx.currentTime);
      const g = ctx.createGain();
      g.gain.setValueAtTime(i === 0 ? 0.025 : 0.018, ctx.currentTime);
      osc.connect(filter);
      filter.connect(g);
      g.connect(dryGain);
      g.connect(convolver);
      osc.start();
      nodes.push(osc);
    });
  });

  // Drone filter sweep — slow breathing, keeps it alive
  const droneSweep = ctx.createOscillator();
  droneSweep.type = "sine";
  droneSweep.frequency.setValueAtTime(0.04, ctx.currentTime);
  droneSweep.start();
  nodes.push(droneSweep);

  // ============================================================
  // Layer 2: Rhythmic pulse — heartbeat of the suit
  // Syncopated 16th-note pattern, sidechained feel
  // ============================================================
  const bpm = 72;
  const beatSec = 60 / bpm;
  const sixteenth = beatSec / 4;

  // Kick-like pulse
  let pulsePhase = 0;
  intervals.push(setInterval(() => {
    try {
      const pattern = [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0]; // syncopated
      const hit = pattern[pulsePhase % 16];
      pulsePhase++;
      if (!hit) return;

      const t = ctx.currentTime;
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.setValueAtTime(55, t);
      osc.frequency.exponentialRampToValueAtTime(30, t + 0.15);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.06, t);
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.2);
      osc.connect(g);
      g.connect(dryGain);
      osc.start(t);
      osc.stop(t + 0.25);
    } catch {}
  }, sixteenth * 1000));

  // Hi-hat texture — metallic ticks
  let hatPhase = 0;
  intervals.push(setInterval(() => {
    try {
      const pattern = [0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1];
      const hit = pattern[hatPhase % 16];
      hatPhase++;
      if (!hit) return;

      const t = ctx.currentTime;
      const len = Math.floor(ctx.sampleRate * 0.03);
      const buf = ctx.createBuffer(1, len, ctx.sampleRate);
      const data = buf.getChannelData(0);
      for (let i = 0; i < len; i++) data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (len * 0.15));
      const src = ctx.createBufferSource();
      src.buffer = buf;
      const hp = ctx.createBiquadFilter();
      hp.type = "highpass";
      hp.frequency.setValueAtTime(6000, t);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.012 + Math.random() * 0.005, t);
      src.connect(hp);
      hp.connect(g);
      g.connect(dryGain);
      src.start(t);
    } catch {}
  }, sixteenth * 1000));

  // ============================================================
  // Layer 3: Evolving cinematic chord — tension + release
  // Cm → Eb → Ab → Bb (dark, heroic progression)
  // ============================================================
  const chords = [
    [130.8, 155.6, 196.0, 311.1],  // Cm
    [155.6, 196.0, 233.1, 311.1],  // Eb
    [207.7, 261.6, 311.1, 415.3],  // Ab
    [233.1, 293.7, 349.2, 466.2],  // Bb
  ];
  let chordIdx = 0;
  const chordOscs: OscillatorNode[] = [];

  const chordFilter = ctx.createBiquadFilter();
  chordFilter.type = "lowpass";
  chordFilter.frequency.setValueAtTime(800, ctx.currentTime);
  chordFilter.Q.setValueAtTime(0.8, ctx.currentTime);
  chordFilter.connect(convolver);
  chordFilter.connect(dryGain);

  // Filter automation — opens up on chord change, then closes
  for (let i = 0; i < 4; i++) {
    const osc = ctx.createOscillator();
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(chords[0][i], ctx.currentTime);
    osc.detune.setValueAtTime(i % 2 === 0 ? -6 : 6, ctx.currentTime);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.012, ctx.currentTime);
    osc.connect(g);
    g.connect(chordFilter);
    osc.start();
    chordOscs.push(osc);
    nodes.push(osc);
  }

  intervals.push(setInterval(() => {
    try {
      chordIdx = (chordIdx + 1) % chords.length;
      const t = ctx.currentTime;
      const chord = chords[chordIdx];
      for (let i = 0; i < 4; i++) {
        chordOscs[i].frequency.setValueAtTime(chordOscs[i].frequency.value, t);
        chordOscs[i].frequency.linearRampToValueAtTime(chord[i], t + 1.5);
      }
      // Filter opens then closes
      chordFilter.frequency.setValueAtTime(chordFilter.frequency.value, t);
      chordFilter.frequency.linearRampToValueAtTime(1400, t + 0.8);
      chordFilter.frequency.linearRampToValueAtTime(700, t + 6);
    } catch {}
  }, 6500));

  // ============================================================
  // Layer 4: Arpeggiator — JARVIS data-processing feel
  // Fast minor arpeggios that come and go
  // ============================================================
  const arpNotes = [196.0, 233.1, 261.6, 311.1, 392.0, 466.2, 523.3];
  let arpActive = false;

  // Toggle arp sections on/off every ~10s
  intervals.push(setInterval(() => {
    arpActive = !arpActive;
  }, 10000));

  let arpStep = 0;
  intervals.push(setInterval(() => {
    try {
      if (!arpActive) return;
      const t = ctx.currentTime;
      const note = arpNotes[arpStep % arpNotes.length];
      arpStep++;

      const osc = ctx.createOscillator();
      osc.type = "square";
      osc.frequency.setValueAtTime(note, t);
      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.setValueAtTime(1500, t);
      filter.frequency.exponentialRampToValueAtTime(400, t + 0.3);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.015, t);
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.35);
      osc.connect(filter);
      filter.connect(g);
      g.connect(convolver);
      g.connect(dryGain);
      osc.start(t);
      osc.stop(t + 0.4);
    } catch {}
  }, sixteenth * 1000 * 1.5)); // slightly off-grid for organic feel

  // ============================================================
  // Layer 5: Cinematic risers — tension builders every ~20s
  // ============================================================
  intervals.push(setInterval(() => {
    try {
      if (Math.random() > 0.5) return;
      const t = ctx.currentTime;
      const dur = 4 + Math.random() * 3;

      // Rising noise sweep
      const len = Math.floor(ctx.sampleRate * dur);
      const buf = ctx.createBuffer(1, len, ctx.sampleRate);
      const data = buf.getChannelData(0);
      for (let i = 0; i < len; i++) data[i] = (Math.random() * 2 - 1);
      const src = ctx.createBufferSource();
      src.buffer = buf;
      const bp = ctx.createBiquadFilter();
      bp.type = "bandpass";
      bp.frequency.setValueAtTime(200, t);
      bp.frequency.exponentialRampToValueAtTime(4000, t + dur * 0.85);
      bp.frequency.exponentialRampToValueAtTime(300, t + dur);
      bp.Q.setValueAtTime(3, t);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.001, t);
      g.gain.linearRampToValueAtTime(0.02, t + dur * 0.7);
      g.gain.exponentialRampToValueAtTime(0.001, t + dur);
      src.connect(bp);
      bp.connect(g);
      g.connect(convolver);
      src.start(t);
      src.stop(t + dur + 0.1);

      // Accompanying rising tone
      const riser = ctx.createOscillator();
      riser.type = "sawtooth";
      riser.frequency.setValueAtTime(80, t);
      riser.frequency.exponentialRampToValueAtTime(400, t + dur * 0.85);
      const riserFilter = ctx.createBiquadFilter();
      riserFilter.type = "lowpass";
      riserFilter.frequency.setValueAtTime(200, t);
      riserFilter.frequency.exponentialRampToValueAtTime(2000, t + dur * 0.8);
      const rg = ctx.createGain();
      rg.gain.setValueAtTime(0.001, t);
      rg.gain.linearRampToValueAtTime(0.015, t + dur * 0.6);
      rg.gain.exponentialRampToValueAtTime(0.001, t + dur);
      riser.connect(riserFilter);
      riserFilter.connect(rg);
      rg.connect(convolver);
      riser.start(t);
      riser.stop(t + dur + 0.1);
    } catch {}
  }, 18000));

  // ============================================================
  // Layer 6: Stinger accents — dramatic orchestral-style hits
  // ============================================================
  intervals.push(setInterval(() => {
    try {
      if (Math.random() > 0.35) return;
      const t = ctx.currentTime;

      // Low brass stab (layered saws)
      [65.4, 98.0, 130.8].forEach((freq) => {
        const osc = ctx.createOscillator();
        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(freq, t);
        const filter = ctx.createBiquadFilter();
        filter.type = "lowpass";
        filter.frequency.setValueAtTime(1200, t);
        filter.frequency.exponentialRampToValueAtTime(200, t + 1.5);
        const g = ctx.createGain();
        g.gain.setValueAtTime(0.001, t);
        g.gain.linearRampToValueAtTime(0.025, t + 0.05);
        g.gain.exponentialRampToValueAtTime(0.001, t + 1.8);
        osc.connect(filter);
        filter.connect(g);
        g.connect(convolver);
        g.connect(dryGain);
        osc.start(t);
        osc.stop(t + 2);
      });
    } catch {}
  }, 12000));

  return {
    master,
    fadeIn(duration = 3) {
      master.gain.cancelScheduledValues(ctx.currentTime);
      master.gain.setValueAtTime(master.gain.value, ctx.currentTime);
      master.gain.linearRampToValueAtTime(1, ctx.currentTime + duration);
    },
    fadeOut(duration = 1.5) {
      master.gain.cancelScheduledValues(ctx.currentTime);
      master.gain.setValueAtTime(master.gain.value, ctx.currentTime);
      master.gain.linearRampToValueAtTime(0, ctx.currentTime + duration);
    },
    destroy() {
      intervals.forEach((id) => clearInterval(id));
      nodes.forEach((n) => { try { n.stop(); } catch {} });
    },
  };
}

export function JarvisBGM() {
  const [playing, setPlaying] = useState(false);
  const ctxRef = useRef<AudioContext | null>(null);
  const bgmRef = useRef<ReturnType<typeof createBGM> | null>(null);

  const toggle = useCallback(() => {
    if (playing) {
      bgmRef.current?.fadeOut(1.5);
      setPlaying(false);
    } else {
      if (!ctxRef.current) {
        ctxRef.current = new AudioContext();
      }
      if (ctxRef.current.state === "suspended") {
        ctxRef.current.resume();
      }
      if (!bgmRef.current) {
        bgmRef.current = createBGM(ctxRef.current);
      }
      bgmRef.current.fadeIn(3);
      setPlaying(true);
    }
  }, [playing]);

  useEffect(() => {
    return () => {
      bgmRef.current?.destroy();
      ctxRef.current?.close().catch(() => {});
    };
  }, []);

  return (
    <button
      onClick={toggle}
      className="fixed bottom-5 right-5 z-50 flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-mono tracking-wider transition-all backdrop-blur-sm"
      style={{
        borderColor: playing ? "rgba(0, 212, 255, 0.4)" : "rgba(0, 212, 255, 0.15)",
        background: playing ? "rgba(0, 212, 255, 0.08)" : "rgba(6, 8, 13, 0.8)",
        color: playing ? "#00d4ff" : "rgba(0, 212, 255, 0.4)",
        boxShadow: playing ? "0 0 20px rgba(0, 212, 255, 0.1)" : "none",
      }}
      title={playing ? "Mute BGM" : "Play BGM"}
    >
      <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M11 5L6 9H2v6h4l5 4V5z" />
        {playing ? (
          <>
            <path d="M15.54 8.46a5 5 0 010 7.07" />
            <path d="M19.07 4.93a10 10 0 010 14.14" />
          </>
        ) : (
          <path d="M23 9l-6 6M17 9l6 6" />
        )}
      </svg>
      <span>{playing ? "BGM ON" : "BGM"}</span>
      {playing && (
        <span className="flex items-center gap-0.5">
          <span className="w-0.5 h-2 bg-jarvis/60 rounded-full animate-pulse" style={{ animationDelay: "0s" }} />
          <span className="w-0.5 h-3 bg-jarvis/60 rounded-full animate-pulse" style={{ animationDelay: "0.15s" }} />
          <span className="w-0.5 h-1.5 bg-jarvis/60 rounded-full animate-pulse" style={{ animationDelay: "0.3s" }} />
          <span className="w-0.5 h-2.5 bg-jarvis/60 rounded-full animate-pulse" style={{ animationDelay: "0.1s" }} />
        </span>
      )}
    </button>
  );
}
