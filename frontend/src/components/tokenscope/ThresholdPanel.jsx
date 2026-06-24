import { useEffect, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Check } from "lucide-react";
import { saveThreshold, formatNumber, formatCost } from "@/lib/tokenApi";

export default function ThresholdPanel({ threshold, summary, onSaved }) {
  const [tokens, setTokens] = useState(1_000_000);
  const [cost, setCost] = useState(10);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (threshold) {
      setTokens(threshold.daily_tokens);
      setCost(threshold.daily_cost_usd);
    }
  }, [threshold]);

  const todayKey = new Date().toISOString().slice(0, 10);
  const today = (summary?.by_day || []).find((d) => d.day === todayKey) || {
    input_tokens: 0,
    output_tokens: 0,
    cost_usd: 0,
  };
  const todayTokens = (today.input_tokens || 0) + (today.output_tokens || 0);
  const tokenPct = threshold ? (todayTokens / Math.max(1, threshold.daily_tokens)) * 100 : 0;
  const costPct = threshold ? (today.cost_usd / Math.max(0.0001, threshold.daily_cost_usd)) * 100 : 0;
  const tokenBreach = tokenPct >= 100;
  const costBreach = costPct >= 100;

  const save = async () => {
    setSaving(true);
    try {
      await saveThreshold({ id: "global", daily_tokens: Number(tokens), daily_cost_usd: Number(cost) });
      toast.success("THRESHOLD UPDATED");
      onSaved?.();
    } catch (e) {
      toast.error("SAVE FAILED", { description: e.message });
    } finally {
      setSaving(false);
    }
  };

  const renderBar = ({ pct, breach, label, current, max, fmt }) => (
    <div data-testid={`threshold-${label}-bar`}>
      <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500 mb-2">
        <span>{label}</span>
        <span className={breach ? "text-[#FF3B30]" : "text-zinc-400"}>
          {fmt(current)} / {fmt(max)}
        </span>
      </div>
      <div className="h-2 bg-zinc-900 relative">
        <div
          className={`h-full transition-all duration-300 ${
            breach ? "bg-[#FF3B30]" : pct > 75 ? "bg-[#FFCC00]" : "bg-white"
          }`}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
    </div>
  );

  return (
    <div
      data-testid="threshold-panel"
      className={`border bg-[#0A0A0A] ${
        tokenBreach || costBreach ? "border-[#FF3B30]" : "border-zinc-800"
      }`}
    >
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
          // daily_threshold
        </div>
        {tokenBreach || costBreach ? (
          <div
            data-testid="threshold-breach-indicator"
            className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.2em] text-[#FF3B30]"
          >
            <AlertTriangle className="h-3 w-3" strokeWidth={2} /> breached
          </div>
        ) : (
          <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
            <Check className="h-3 w-3" strokeWidth={2} /> nominal
          </div>
        )}
      </div>

      <div className="p-4 space-y-6">
        {renderBar({
          pct: tokenPct,
          breach: tokenBreach,
          label: "tokens_today",
          current: todayTokens,
          max: tokens,
          fmt: formatNumber,
        })}
        {renderBar({
          pct: costPct,
          breach: costBreach,
          label: "cost_today",
          current: today.cost_usd,
          max: cost,
          fmt: formatCost,
        })}

        <div className="grid grid-cols-2 gap-3 pt-2 border-t border-zinc-900">
          <label className="block">
            <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500 mb-1.5">
              max tokens / day
            </div>
            <input
              data-testid="threshold-tokens-input"
              type="number"
              value={tokens}
              onChange={(e) => setTokens(e.target.value)}
              className="w-full bg-black border border-zinc-800 px-2.5 py-2 font-mono text-xs text-white focus:outline-none focus:border-white"
            />
          </label>
          <label className="block">
            <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500 mb-1.5">
              max usd / day
            </div>
            <input
              data-testid="threshold-cost-input"
              type="number"
              step="0.01"
              value={cost}
              onChange={(e) => setCost(e.target.value)}
              className="w-full bg-black border border-zinc-800 px-2.5 py-2 font-mono text-xs text-white focus:outline-none focus:border-white"
            />
          </label>
        </div>
        <button
          data-testid="threshold-save-btn"
          onClick={save}
          disabled={saving}
          className="w-full font-mono text-[11px] uppercase tracking-[0.25em] py-2.5 bg-white text-black hover:bg-zinc-200 disabled:opacity-50"
        >
          {saving ? "saving…" : "save threshold"}
        </button>
      </div>
    </div>
  );
}
