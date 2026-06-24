import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Legend,
} from "recharts";
import { TOOL_COLORS, TOOL_LABEL, formatNumber } from "@/lib/tokenApi";

const tickStyle = {
  fontFamily: "JetBrains Mono, monospace",
  fontSize: 10,
  fill: "#71717A",
};

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="border border-zinc-700 bg-black p-3 font-mono text-[11px]">
      <div className="text-zinc-400 uppercase tracking-[0.2em] text-[10px] mb-2">
        {label}
      </div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <span
              className="inline-block w-2 h-2"
              style={{ backgroundColor: p.color }}
            />
            <span className="text-zinc-300">{TOOL_LABEL[p.dataKey] || p.dataKey}</span>
          </div>
          <span className="text-white tabular-nums">{formatNumber(p.value)}</span>
        </div>
      ))}
    </div>
  );
}

export default function UsageChart({ summary, threshold }) {
  const data = (summary?.by_day || []).map((d) => ({
    day: d.day?.slice(5) || "",
    claude_api: d.claude_api || 0,
    codex: d.codex || 0,
    antigravity: d.antigravity || 0,
  }));

  return (
    <div
      data-testid="usage-chart-panel"
      className="border border-zinc-800 bg-[#0A0A0A]"
    >
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
          // tokens_over_time
        </div>
        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
          per tool · daily
        </div>
      </div>
      <div className="p-4 h-[320px]" data-testid="usage-chart">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid
              strokeDasharray="2 4"
              stroke="#27272A"
              vertical={false}
            />
            <XAxis dataKey="day" tick={tickStyle} stroke="#27272A" />
            <YAxis
              tick={tickStyle}
              stroke="#27272A"
              tickFormatter={(v) => formatNumber(v)}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: "#3F3F46" }} />
            {threshold?.daily_tokens > 0 && (
              <ReferenceLine
                y={threshold.daily_tokens}
                stroke="#FF3B30"
                strokeDasharray="4 4"
                label={{
                  value: `THRESHOLD ${formatNumber(threshold.daily_tokens)}`,
                  fill: "#FF3B30",
                  fontSize: 10,
                  fontFamily: "JetBrains Mono, monospace",
                  position: "insideTopRight",
                }}
              />
            )}
            <Legend
              wrapperStyle={{
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 10,
                color: "#A1A1AA",
                textTransform: "uppercase",
                letterSpacing: "0.15em",
              }}
              formatter={(v) => TOOL_LABEL[v] || v}
            />
            <Line
              type="monotone"
              dataKey="claude_api"
              stroke={TOOL_COLORS.claude_api}
              strokeWidth={1.5}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="codex"
              stroke={TOOL_COLORS.codex}
              strokeWidth={1.5}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="antigravity"
              stroke={TOOL_COLORS.antigravity}
              strokeWidth={1.5}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
