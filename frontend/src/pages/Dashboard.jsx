import { useEffect, useState } from "react";
import Header from "@/components/tokenscope/Header";
import UploadDropzone from "@/components/tokenscope/UploadDropzone";
import SummaryCards from "@/components/tokenscope/SummaryCards";
import UsageChart from "@/components/tokenscope/UsageChart";
import ToolBreakdownChart from "@/components/tokenscope/ToolBreakdownChart";
import ModelTable from "@/components/tokenscope/ModelTable";
import ThresholdPanel from "@/components/tokenscope/ThresholdPanel";
import RecentEntries from "@/components/tokenscope/RecentEntries";
import SystemTray from "@/components/tokenscope/SystemTray";
import ApiKeyPanel from "@/components/tokenscope/ApiKeyPanel";
import { fetchSummary, fetchThreshold, clearAllUsage } from "@/lib/tokenApi";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";

export default function Dashboard() {
  const [days, setDays] = useState(30);
  const [summary, setSummary] = useState(null);
  const [threshold, setThreshold] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const loadAll = async () => {
    try {
      const [s, t] = await Promise.all([fetchSummary(days), fetchThreshold()]);
      setSummary(s);
      setThreshold(t);
    } catch (e) {
      toast.error("LOAD FAILED", { description: e.message });
    }
  };

  useEffect(() => {
    loadAll();
  }, [days, refreshKey]);

  const refresh = () => setRefreshKey((k) => k + 1);

  const wipe = async () => {
    if (!window.confirm("Clear ALL imported usage data? This cannot be undone.")) return;
    try {
      const r = await clearAllUsage();
      toast.success("DATA WIPED", { description: `${r.deleted} entries removed` });
      refresh();
    } catch (e) {
      toast.error("WIPE FAILED", { description: e.message });
    }
  };

  return (
    <div className="relative min-h-screen">
      <Header
        days={days}
        setDays={setDays}
        totalEntries={summary?.totals?.entries}
      />

      <main className="px-6 py-6 space-y-6 max-w-[1600px] mx-auto relative z-10">
        <ApiKeyPanel />

        <UploadDropzone onImported={refresh} />

        <SummaryCards summary={summary} threshold={threshold} />

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <UsageChart summary={summary} threshold={threshold} />
          </div>
          <div>
            <ToolBreakdownChart summary={summary} />
          </div>
        </div>

        {/* Table + threshold row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <ModelTable summary={summary} />
          </div>
          <div>
            <ThresholdPanel
              threshold={threshold}
              summary={summary}
              onSaved={refresh}
            />
          </div>
        </div>

        {/* Recent entries */}
        <RecentEntries days={days} refreshKey={refreshKey} onChanged={refresh} />

        <div className="flex items-center justify-between pt-6 pb-12 border-t border-zinc-900">
          <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-600">
            TokenScope · local-first analytics · no external telemetry
          </div>
          <button
            data-testid="wipe-data-btn"
            onClick={wipe}
            className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500 hover:text-[#FF3B30] border border-zinc-800 hover:border-[#FF3B30] px-3 py-2"
          >
            <Trash2 className="h-3 w-3" strokeWidth={1.5} />
            wipe data
          </button>
        </div>
      </main>

      <SystemTray summary={summary} threshold={threshold} />
    </div>
  );
}
