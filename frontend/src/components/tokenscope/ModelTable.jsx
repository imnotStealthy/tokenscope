import { TOOL_LABEL, formatNumber, formatCost } from "@/lib/tokenApi";

export default function ModelTable({ summary }) {
  const rows = summary?.by_model || [];
  return (
    <div
      data-testid="model-table-panel"
      className="border border-zinc-800 bg-[#0A0A0A]"
    >
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
          // breakdown_by_model
        </div>
        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
          {rows.length} models
        </div>
      </div>
      <div className="overflow-x-auto">
        <table
          data-testid="model-table"
          className="w-full font-mono text-[12px] tabular-nums"
        >
          <thead>
            <tr className="text-zinc-500 uppercase tracking-[0.2em] text-[10px]">
              <th className="text-left px-4 py-3 border-b border-zinc-800 font-medium">tool</th>
              <th className="text-left px-4 py-3 border-b border-zinc-800 font-medium">model</th>
              <th className="text-left px-4 py-3 border-b border-zinc-800 font-medium">under</th>
              <th className="text-right px-4 py-3 border-b border-zinc-800 font-medium">in</th>
              <th className="text-right px-4 py-3 border-b border-zinc-800 font-medium">out</th>
              <th className="text-right px-4 py-3 border-b border-zinc-800 font-medium">total</th>
              <th className="text-right px-4 py-3 border-b border-zinc-800 font-medium">calls</th>
              <th className="text-right px-4 py-3 border-b border-zinc-800 font-medium">cost</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-zinc-600">
                  no data · import a CSV/JSON or load demo data
                </td>
              </tr>
            )}
            {rows.map((r, idx) => (
              <tr
                key={idx}
                data-testid={`model-row-${idx}`}
                className="border-b border-zinc-900 hover:bg-zinc-950"
              >
                <td className="px-4 py-2.5 text-zinc-300">
                  {TOOL_LABEL[r.tool] || r.tool}
                </td>
                <td className="px-4 py-2.5 text-white">{r.model}</td>
                <td className="px-4 py-2.5 text-zinc-500">{r.underlying_model || "—"}</td>
                <td className="px-4 py-2.5 text-right text-zinc-400">
                  {formatNumber(r.input_tokens)}
                </td>
                <td className="px-4 py-2.5 text-right text-zinc-400">
                  {formatNumber(r.output_tokens)}
                </td>
                <td className="px-4 py-2.5 text-right text-white">
                  {formatNumber((r.input_tokens || 0) + (r.output_tokens || 0))}
                </td>
                <td className="px-4 py-2.5 text-right text-zinc-500">{r.entries}</td>
                <td className="px-4 py-2.5 text-right text-white">
                  {formatCost(r.cost_usd)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
