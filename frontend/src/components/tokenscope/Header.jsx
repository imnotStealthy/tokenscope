import { Activity, Terminal } from "lucide-react";

export default function Header({ days, setDays, totalEntries }) {
  const now = new Date().toISOString().slice(0, 19).replace("T", " ");

  return (
    <header
      data-testid="app-header"
      className="border-b border-zinc-800 bg-black sticky top-0 z-40 relative"
    >
      <div className="px-6 py-4 flex items-center justify-between gap-6 flex-wrap">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Terminal className="h-5 w-5" strokeWidth={1.5} />
            <div
              data-testid="app-title"
              className="font-mono text-base font-semibold tracking-tight"
            >
              TOKENSCOPE
            </div>
            <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500 ml-2">
              v0.1 · token consumption tracker
            </span>
          </div>
        </div>

        <div className="flex items-center gap-6 flex-wrap">
          <div className="hidden md:flex items-center gap-2 font-mono text-xs text-zinc-500">
            <Activity className="h-3.5 w-3.5" strokeWidth={1.5} />
            <span data-testid="header-entry-count">
              {totalEntries ?? 0} entries
            </span>
            <span className="text-zinc-700">·</span>
            <span>{now} UTC</span>
          </div>

          <div className="flex items-center gap-1 border border-zinc-800">
            {[7, 30, 90].map((d) => (
              <button
                key={d}
                data-testid={`range-${d}d-btn`}
                onClick={() => setDays(d)}
                className={`font-mono text-[11px] uppercase tracking-[0.2em] px-3 py-1.5 transition-colors duration-100 ${
                  days === d
                    ? "bg-white text-black"
                    : "text-zinc-400 hover:text-white hover:bg-zinc-900"
                }`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>
      </div>
    </header>
  );
}
