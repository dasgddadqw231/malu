"use client";

import { useState } from "react";
import { MODULE_CATALOG, validateStrategyJson, DEFAULT_STRATEGY_JSON } from "@/lib/strategy";
import { CheckCircle2Icon, AlertTriangleIcon, RotateCcwIcon, BookOpenIcon } from "lucide-react";

// Direct JSON editor for a bot's strategy_config. The parent owns the text and
// derives validity itself (via validateStrategyJson) to gate submission.
export function StrategyEditor({
  value,
  onChange,
}: {
  value: string;
  onChange: (text: string) => void;
}) {
  const [showRef, setShowRef] = useState(false);
  const result = validateStrategyJson(value);

  const format = () => {
    if (result.valid && result.parsed) {
      onChange(JSON.stringify(result.parsed, null, 2));
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {result.valid ? (
            <span className="flex items-center gap-1 text-xs font-mono text-emerald-400">
              <CheckCircle2Icon className="size-3" /> VALID
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs font-mono text-red-400">
              <AlertTriangleIcon className="size-3" /> INVALID
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={format}
            disabled={!result.valid}
            className="flex items-center gap-1 text-xs font-mono text-jarvis/50 hover:text-jarvis transition-colors disabled:opacity-30"
          >
            <RotateCcwIcon className="size-3" /> FORMAT
          </button>
          <button
            type="button"
            onClick={() => onChange(DEFAULT_STRATEGY_JSON)}
            className="text-xs font-mono text-jarvis/50 hover:text-jarvis transition-colors"
          >
            RESET
          </button>
          <button
            type="button"
            onClick={() => setShowRef((s) => !s)}
            className="flex items-center gap-1 text-xs font-mono text-jarvis/50 hover:text-jarvis transition-colors"
          >
            <BookOpenIcon className="size-3" /> MODULES
          </button>
        </div>
      </div>

      <textarea
        value={value}
        spellCheck={false}
        onChange={(e) => onChange(e.target.value)}
        className={`w-full h-72 resize-y rounded-lg bg-black/40 border px-3 py-2 text-xs font-mono leading-relaxed focus:outline-none ${
          result.valid ? "border-jarvis/15 focus:border-jarvis/40" : "border-red-500/40 focus:border-red-500/60"
        }`}
      />

      {!result.valid && result.error && (
        <p className="text-xs font-mono text-red-400/90">{result.error}</p>
      )}

      {showRef && (
        <div className="rounded-lg border border-jarvis/10 bg-jarvis/5 p-3 space-y-3">
          <p className="text-xs font-mono text-jarvis/50 tracking-wider">
            사용 가능한 모듈 — 각 항목의 <span className="text-jarvis">module</span> 값에 이름을 넣고{" "}
            <span className="text-jarvis">params</span> 로 파라미터를 조정하세요.
          </p>
          {MODULE_CATALOG.map((cat) => (
            <div key={cat.key} className="space-y-1">
              <p className="text-xs font-mono text-jarvis/70 tracking-wider uppercase">{cat.category}</p>
              <div className="flex flex-wrap gap-1.5">
                {cat.modules.map((m) => (
                  <span
                    key={m.name}
                    title={m.desc}
                    className="rounded border border-jarvis/15 bg-jarvis/5 px-2 py-0.5 text-xs font-mono text-foreground/80"
                  >
                    {m.name}
                    <span className="text-muted-foreground/60"> · {m.desc}</span>
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
