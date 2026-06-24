import { formatNumber, formatCost } from "@/lib/tokenApi";
import { ArrowDownToLine, ArrowUpFromLine, Coins, Database, AlertTriangle } from "lucide-react";

function Stat({ label, value, sub, icon: Icon, testid, breached }) {
  return (
    <div
      data-testid={testid}
      className={`border border-zinc-800 bg-[#0A0A0A] p-5 flex flex-col gap-3 ${
        breached ? "border-[#FF3B30] flash-red" : ""
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
          {label}
        </div>
        <Icon
          className={`h-4 w-4 ${breached ? "text-[#FF3B30]" : "text-zinc-600"}`}
          strokeWidth={1.5}
        />
      </div>
      <div className="font-mono text-3xl tracking-tight tabular-nums">{value}</div>
      {sub && (
        <div className="font-mono text-[11px] text-zinc-500 tabular-nums">{sub}</div>
      )}
    </div>
  );
}

export default function SummaryCards({ summary, threshold }) {
  const totals = summary?.totals || {
    input_tokens: 0,
    output_tokens: 0,
    total_tokens: 0,
    cost_usd: 0,
    entries: 0,
  };

  const todayKey = new Date().toISOString().slice(0, 10);
  const today = (summary?.by_day || []).find((d) => d.day === todayKey) || {
    input_tokens: 0,
    output_tokens: 0,
    cost_usd: 0,
  };
  const todayTokens = (today.input_tokens || 0) + (today.output_tokens || 0);
  const tokenBreached = threshold && todayTokens >= threshold.daily_tokens;
  const costBreached = threshold && today.cost_usd >= threshold.daily_cost_usd;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <Stat
        testid="stat-total-tokens"
        label="total_tokens"
        value={formatNumber(totals.total_tokens)}
        sub={`${totals.entries} entries · selected range`}
        icon={Database}
      />
      <Stat
        testid="stat-input-tokens"
        label="input_tokens"
        value={formatNumber(totals.input_tokens)}
        sub="prompt tokens"
        icon={ArrowDownToLine}
      />
      <Stat
        testid="stat-output-tokens"
        label="output_tokens"
        value={formatNumber(totals.output_tokens)}
        sub="completion tokens"
        icon={ArrowUpFromLine}
      />
      <Stat
        testid="stat-total-cost"
        label="total_cost_usd"
        value={formatCost(totals.cost_usd)}
        sub={`today: ${formatCost(today.cost_usd)} / ${formatNumber(todayTokens)} tok`}
        icon={tokenBreached || costBreached ? AlertTriangle : Coins}
        breached={tokenBreached || costBreached}
      />
    </div>
  );
}
