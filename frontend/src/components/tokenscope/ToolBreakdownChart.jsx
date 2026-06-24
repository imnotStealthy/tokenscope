import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from "recharts";
import { TOOL_COLORS, TOOL_LABEL, formatNumber, formatCost } from "@/lib/tokenApi";

const tickStyle = {
  fontFamily: "JetBrains Mono, monospace",
  fontSize: 10,
  fill: "#71717A",
};

function CostTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  return (
    <div className="border border-zinc-700 bg-black p-3 font-mono text-[11px]">
      <div className="text-zinc-400 uppercase tracking-[0.2em] text-[10px] mb-2">
        {label}
      </div>
      <div className="text-white tabular-nums">
        cost: {formatCost(p.value)}
      </div>
      <div className="text-zinc-400 tabular-nums">
        tokens: {formatNumber((p.payload.input_tokens || 0) + (p.payload.output_tokens || 0))}
      </div>
    </div>
  );
}

export default function ToolBreakdownChart({ summary }) {
  const data = (summary?.by_tool || []).map((t) => ({
    tool: TOOL_LABEL[t.tool] || t.tool,
    tool_key: t.tool,
    cost_usd: t.cost_usd,
    input_tokens: t.input_tokens,
    output_tokens: t.output_tokens,
  }));

  return (
    <div
      data-testid="tool-breakdown-chart"
      className="border border-zinc-800 bg-[#0A0A0A]"
    >
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
          // cost_by_tool
        </div>
        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
          usd
        </div>
      </div>
      <div className="p-4 h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="2 4" stroke="#27272A" vertical={false} />
            <XAxis dataKey="tool" tick={tickStyle} stroke="#27272A" />
            <YAxis tick={tickStyle} stroke="#27272A" tickFormatter={(v) => `$${v}`} />
            <Tooltip content={<CostTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
            <Bar dataKey="cost_usd">
              {data.map((entry, idx) => (
                <Cell key={idx} fill={TOOL_COLORS[entry.tool_key] || "#FFFFFF"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
