import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { fetchUsage, deleteUsage, TOOL_LABEL, formatNumber, formatCost } from "@/lib/tokenApi";
import { useLang } from "@/lib/i18n";

export default function RecentEntries({ days, refreshKey, onChanged }) {
  const { t } = useLang();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchUsage({ days, limit: 50 });
      setItems(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [days, refreshKey]);

  const remove = async (id) => {
    await deleteUsage(id);
    load();
    onChanged?.();
  };

  return (
    <div
      data-testid="recent-entries-panel"
      className="border border-zinc-800 bg-[#0A0A0A]"
    >
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
          // recent_entries
        </div>
        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
          {loading ? t("recent.loading") : t("recent.shown", { n: items.length })}
        </div>
      </div>
      <div className="max-h-[420px] overflow-y-auto">
        <table className="w-full font-mono text-[11px] tabular-nums">
          <thead className="sticky top-0 bg-[#0A0A0A]">
            <tr className="text-zinc-500 uppercase tracking-[0.2em] text-[10px]">
              <th className="text-left px-4 py-2.5 border-b border-zinc-800 font-medium">when</th>
              <th className="text-left px-4 py-2.5 border-b border-zinc-800 font-medium">tool</th>
              <th className="text-left px-4 py-2.5 border-b border-zinc-800 font-medium">model</th>
              <th className="text-right px-4 py-2.5 border-b border-zinc-800 font-medium">in</th>
              <th className="text-right px-4 py-2.5 border-b border-zinc-800 font-medium">out</th>
              <th className="text-right px-4 py-2.5 border-b border-zinc-800 font-medium">usd</th>
              <th className="px-2 py-2.5 border-b border-zinc-800"></th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && !loading && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-zinc-600">
                  {t("recent.no_entries")}
                </td>
              </tr>
            )}
            {items.map((it, idx) => {
              const ts = typeof it.timestamp === "string" ? it.timestamp : new Date(it.timestamp).toISOString();
              return (
                <tr
                  key={it.id}
                  data-testid={`recent-row-${idx}`}
                  className="border-b border-zinc-900 hover:bg-zinc-950"
                >
                  <td className="px-4 py-2 text-zinc-400">{ts.slice(0, 16).replace("T", " ")}</td>
                  <td className="px-4 py-2 text-zinc-300">{TOOL_LABEL[it.tool] || it.tool}</td>
                  <td className="px-4 py-2 text-white">
                    {it.model}
                    {it.underlying_model && (
                      <span className="text-zinc-500"> ▸ {it.underlying_model}</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right text-zinc-400">{formatNumber(it.input_tokens)}</td>
                  <td className="px-4 py-2 text-right text-zinc-400">{formatNumber(it.output_tokens)}</td>
                  <td className="px-4 py-2 text-right text-white">{formatCost(it.cost_usd)}</td>
                  <td className="px-2 py-2 text-right">
                    <button
                      data-testid={`recent-delete-${idx}`}
                      onClick={() => remove(it.id)}
                      className="text-zinc-600 hover:text-[#FF3B30]"
                      aria-label={t("recent.delete")}
                    >
                      <Trash2 className="h-3.5 w-3.5" strokeWidth={1.5} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
