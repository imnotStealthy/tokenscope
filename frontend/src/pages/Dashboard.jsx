import { useEffect, useState } from "react";
import Header from "@/components/tokenscope/Header";
import UploadDropzone from "@/components/tokenscope/UploadDropzone";
import UtilizationPanel from "@/components/tokenscope/UtilizationPanel";
import SummaryCards from "@/components/tokenscope/SummaryCards";
import UsageChart from "@/components/tokenscope/UsageChart";
import ToolBreakdownChart from "@/components/tokenscope/ToolBreakdownChart";
import ProjectTable from "@/components/tokenscope/ProjectTable";
import ModelTable from "@/components/tokenscope/ModelTable";
import ThresholdPanel from "@/components/tokenscope/ThresholdPanel";
import RecentEntries from "@/components/tokenscope/RecentEntries";
import SystemTray from "@/components/tokenscope/SystemTray";
import ApiKeyPanel from "@/components/tokenscope/ApiKeyPanel";
import {
  fetchSummary,
  fetchLocalSummary,
  fetchLocalUtilization,
  fetchThreshold,
  clearAllUsage,
} from "@/lib/tokenApi";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import { useLang } from "@/lib/i18n";

export default function Dashboard() {
  const { t: tr } = useLang();
  const [days, setDays] = useState(30);
  const [source, setSource] = useState("local");
  const [summary, setSummary] = useState(null);
  const [utilization, setUtilization] = useState(null);
  const [threshold, setThreshold] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const isLocal = source === "local";

  const loadAll = async () => {
    setLoading(true);
    try {
      if (isLocal) {
        // Independent catches so one failing source still renders the others.
        const [s, u, t] = await Promise.all([
          fetchLocalSummary(days).catch(() => null),
          fetchLocalUtilization().catch(() => null),
          fetchThreshold().catch(() => null),
        ]);
        setSummary(s);
        setUtilization(u);
        setThreshold(t);
        if (!s && !u && !t) {
          toast.error(tr("dashboard.load_failed"), { description: tr("dashboard.local_unavailable") });
        }
      } else {
        const [s, t] = await Promise.all([fetchSummary(days), fetchThreshold()]);
        setSummary(s);
        setUtilization(null);
        setThreshold(t);
      }
    } catch (e) {
      toast.error(tr("dashboard.load_failed"), { description: e.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days, source, refreshKey]);

  const refresh = () => setRefreshKey((k) => k + 1);

  const wipe = async () => {
    if (!window.confirm(tr("dashboard.confirm_wipe"))) return;
    try {
      const r = await clearAllUsage();
      toast.success(tr("dashboard.data_wiped"), { description: tr("dashboard.entries_removed", { n: r.deleted }) });
      refresh();
    } catch (e) {
      toast.error(tr("dashboard.wipe_failed"), { description: e.message });
    }
  };

  return (
    <div className="relative min-h-screen">
      <Header
        days={days}
        setDays={setDays}
        source={source}
        setSource={setSource}
        totalEntries={summary?.totals?.entries}
      />

      <main className="px-6 py-6 space-y-6 max-w-[1600px] mx-auto relative z-10">
        <ApiKeyPanel />

        {isLocal ? (
          <UtilizationPanel utilization={utilization} />
        ) : (
          <UploadDropzone onImported={refresh} />
        )}

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

        {/* Per-project breakdown */}
        <ProjectTable summary={summary} />

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

        {/* Recent entries (stored DB only) */}
        {!isLocal && (
          <RecentEntries days={days} refreshKey={refreshKey} onChanged={refresh} />
        )}

        <div className="flex items-center justify-between pt-6 pb-12 border-t border-zinc-900">
          <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-600">
            TokenScope · {isLocal ? tr("dashboard.src_local") : tr("dashboard.src_stored")} · {tr("dashboard.footer_tail")}
          </div>
          {!isLocal && (
            <button
              data-testid="wipe-data-btn"
              onClick={wipe}
              className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500 hover:text-[#FF3B30] border border-zinc-800 hover:border-[#FF3B30] px-3 py-2"
            >
              <Trash2 className="h-3 w-3" strokeWidth={1.5} />
              {tr("dashboard.wipe_data")}
            </button>
          )}
        </div>
      </main>

      {!isLocal && <SystemTray summary={summary} threshold={threshold} />}
    </div>
  );
}
