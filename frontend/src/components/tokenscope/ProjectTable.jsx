import { TOOL_LABEL, formatNumber, formatCost } from "@/lib/tokenApi";
import { useLang } from "@/lib/i18n";

export default function ProjectTable({ summary }) {
  const { t: tr } = useLang();
  const rows = summary?.by_project || [];
  return (
    <div
      data-testid="project-table-panel"
      className="border border-zinc-800 bg-[#0A0A0A]"
    >
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
          // usage_by_project
        </div>
        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
          {tr("project.count", { n: rows.length })}
        </div>
      </div>
      <div className="overflow-x-auto">
        <table
          data-testid="project-table"
          className="w-full font-mono text-[12px] tabular-nums"
        >
          <thead>
            <tr className="text-zinc-500 uppercase tracking-[0.2em] text-[10px]">
              <th className="text-left px-4 py-3 border-b border-zinc-800 font-medium">project</th>
              <th className="text-left px-4 py-3 border-b border-zinc-800 font-medium">tools</th>
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
                <td colSpan={7} className="px-4 py-8 text-center text-zinc-600">
                  {tr("project.no_data")}
                </td>
              </tr>
            )}
            {rows.map((r, idx) => (
              <tr
                key={r.project || idx}
                data-testid={`project-row-${idx}`}
                className="border-b border-zinc-900 hover:bg-zinc-950"
              >
                <td className="px-4 py-2.5 text-white" title={r.project}>
                  {r.project_name || r.project}
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-1.5">
                    {Object.keys(r.tools || {}).map((t) => (
                      <span
                        key={t}
                        className="border border-zinc-800 px-1.5 py-0.5 text-[9px] uppercase tracking-[0.15em] text-zinc-400"
                      >
                        {TOOL_LABEL[t] || t}
                      </span>
                    ))}
                  </div>
                </td>
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
