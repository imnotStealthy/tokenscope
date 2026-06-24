import { useEffect, useState } from "react";
import { Minus, Square, ChevronRight } from "lucide-react";
import { fetchLive, TOOL_LABEL, formatNumber, formatCost } from "@/lib/tokenApi";

/**
 * Floating "system tray" widget - bottom-right.
 * Shows the latest model in use, terminal-style.
 */
export default function SystemTray({ summary, threshold }) {
  const [live, setLive] = useState(null);
  const [open, setOpen] = useState(true);

  const loadLive = async () => {
    try {
      const r = await fetchLive();
      setLive(r.live);
    } catch (e) {
      // silent
    }
  };

  useEffect(() => {
    loadLive();
    const id = setInterval(loadLive, 5000);
    return () => clearInterval(id);
  }, []);

  // Recompute on summary change too
  useEffect(() => {
    loadLive();
  }, [summary]);

  const todayKey = new Date().toISOString().slice(0, 10);
  const today = (summary?.by_day || []).find((d) => d.day === todayKey) || {
    input_tokens: 0,
    output_tokens: 0,
    cost_usd: 0,
  };
  const todayTokens = (today.input_tokens || 0) + (today.output_tokens || 0);
  const breach = threshold && (todayTokens >= threshold.daily_tokens || today.cost_usd >= threshold.daily_cost_usd);

  if (!open) {
    return (
      <button
        data-testid="system-tray-reopen"
        onClick={() => setOpen(true)}
        className="fixed bottom-4 right-44 z-50 border border-zinc-800 bg-black px-3 py-2 font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-400 hover:text-white hover:border-white"
      >
        <ChevronRight className="h-3 w-3 inline mr-1.5" strokeWidth={2} />
        tray
      </button>
    );
  }

  const modelLabel = live
    ? live.underlying_model
      ? `${live.model} ▸ ${live.underlying_model}`
      : live.model
    : "idle";

  const toolLabel = live ? TOOL_LABEL[live.tool] || live.tool : "—";

  return (
    <div
      data-testid="system-tray"
      className={`fixed bottom-4 right-4 z-50 w-[320px] bg-black border ${
        breach ? "border-[#FF3B30]" : "border-zinc-700"
      } shadow-[0_0_0_1px_rgba(0,0,0,0.6)]`}
    >
      {/* terminal title bar */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-zinc-800 bg-[#0A0A0A]">
        <div className="flex items-center gap-2">
          <span
            data-testid="system-tray-live-dot"
            className={`live-dot inline-block w-2 h-2 ${
              breach ? "bg-[#FF3B30]" : live ? "bg-white" : "bg-zinc-600"
            }`}
          />
          <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-400">
            tray · live
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            data-testid="system-tray-minimize"
            onClick={() => setOpen(false)}
            className="text-zinc-500 hover:text-white"
            aria-label="minimize"
          >
            <Minus className="h-3 w-3" strokeWidth={2} />
          </button>
          <Square className="h-2.5 w-2.5 text-zinc-700" strokeWidth={2} />
        </div>
      </div>

      <div className="p-3 font-mono text-[11px] space-y-2">
        <div className="text-zinc-500">
          $ <span className="text-zinc-300">tokenscope --live</span>
        </div>
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-zinc-500">tool:</span>
          <span data-testid="tray-tool" className="text-white text-right truncate">
            {toolLabel}
          </span>
        </div>
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-zinc-500">model:</span>
          <span data-testid="tray-model" className="text-white text-right truncate">
            {modelLabel}
          </span>
        </div>
        {live && (
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-zinc-500">last:</span>
            <span className="text-zinc-300 tabular-nums">
              {formatNumber((live.input_tokens || 0) + (live.output_tokens || 0))} tok ·{" "}
              {formatCost(live.cost_usd)}
            </span>
          </div>
        )}
        <div className="border-t border-zinc-800 pt-2 mt-1 space-y-1">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-zinc-500">today_tok:</span>
            <span
              data-testid="tray-today-tokens"
              className={`tabular-nums ${
                breach ? "text-[#FF3B30]" : "text-white"
              }`}
            >
              {formatNumber(todayTokens)}
              {threshold && (
                <span className="text-zinc-600">
                  {" "}
                  / {formatNumber(threshold.daily_tokens)}
                </span>
              )}
            </span>
          </div>
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-zinc-500">today_usd:</span>
            <span
              data-testid="tray-today-cost"
              className={`tabular-nums ${
                breach ? "text-[#FF3B30]" : "text-white"
              }`}
            >
              {formatCost(today.cost_usd)}
              {threshold && (
                <span className="text-zinc-600">
                  {" "}
                  / {formatCost(threshold.daily_cost_usd)}
                </span>
              )}
            </span>
          </div>
        </div>
        <div className="text-zinc-600 cli-caret pt-1">_</div>
      </div>
    </div>
  );
}
