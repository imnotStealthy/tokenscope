import { Gauge, Cpu } from "lucide-react";
import { formatReset } from "@/lib/tokenApi";
import { useLang } from "@/lib/i18n";

function UtilBar({ label, pct, reset, remain }) {
  const { t } = useLang();
  const used = Math.max(0, Math.min(100, Number(pct) || 0));
  const value = remain ? 100 - used : used; // codex shows remaining (100 -> 0 = all used)
  const danger = remain ? value <= 10 : value >= 90;
  const warn = remain ? value <= 25 : value >= 75;
  const color = danger ? "bg-[#FF3B30]" : warn ? "bg-[#FFCC00]" : "bg-white";
  const valColor = danger ? "text-[#FF3B30]" : warn ? "text-[#FFCC00]" : "text-zinc-300";
  return (
    <div data-testid={`util-bar-${label}`}>
      <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500 mb-2">
        <span>{label}</span>
        <span className="flex items-center gap-3">
          {reset && <span className="text-zinc-600 normal-case tracking-normal">{formatReset(reset)}</span>}
          <span className={`tabular-nums ${valColor}`}>
            {remain ? t("util.pct_left", { p: value.toFixed(0) }) : `${value.toFixed(0)}%`}
          </span>
        </span>
      </div>
      <div className="h-2 bg-zinc-900 relative">
        <div
          className={`h-full transition-all duration-300 ${color}`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

function Section({ icon: Icon, title, tag, children }) {
  return (
    <div className="border border-zinc-800 bg-[#0A0A0A]">
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
          <Icon className="h-3.5 w-3.5" strokeWidth={1.5} />
          {title}
        </div>
        {tag && (
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-600">
            {tag}
          </div>
        )}
      </div>
      <div className="p-4 space-y-5">{children}</div>
    </div>
  );
}

function Empty({ msg }) {
  return (
    <div className="font-mono text-[11px] text-zinc-600 py-2">{msg}</div>
  );
}

export default function UtilizationPanel({ utilization }) {
  const { t } = useLang();
  const claude = utilization?.claude;
  const codex = utilization?.codex;

  const clMode = claude?.mode;
  const clTag =
    clMode === "subscription"
      ? t("util.tag_subscription", { plan: claude?.plan || "" })
      : clMode === "api"
      ? t("util.tag_api", { plan: claude?.plan || "" })
      : t("util.na");

  return (
    <div
      data-testid="utilization-panel"
      className="grid grid-cols-1 lg:grid-cols-2 gap-4"
    >
      {/* Claude account */}
      <Section icon={Gauge} title="// claude" tag={clTag}>
        {claude?.available && claude.limits?.length ? (
          claude.limits.map((l) => (
            <UtilBar
              key={l.label}
              label={l.label}
              pct={l.used_percent}
              reset={l.reset}
            />
          ))
        ) : clMode === "api" ? (
          <Empty
            msg={t("util.api_mode_desc", { plan: claude?.plan || "Claude Platform" })}
          />
        ) : clMode === "subscription" ? (
          <Empty msg={t("util.no_usage_limit_data")} />
        ) : (
          <Empty msg={t("util.not_signed_in")} />
        )}
      </Section>

      {/* Codex subscription */}
      <Section
        icon={Cpu}
        title="// codex · subscription"
        tag={codex?.plan_type ? codex.plan_type : codex?.auth_mode || t("util.na")}
      >
        {codex?.available ? (
          <>
            {codex.primary && (
              <UtilBar label="5h" pct={codex.primary.used_percent} reset={codex.primary.reset} remain />
            )}
            {codex.secondary && (
              <UtilBar label="weekly" pct={codex.secondary.used_percent} reset={codex.secondary.reset} remain />
            )}
            {codex.spark_primary && (
              <UtilBar label="spark 5h" pct={codex.spark_primary.used_percent} reset={codex.spark_primary.reset} remain />
            )}
            {codex.spark_secondary && (
              <UtilBar label="spark weekly" pct={codex.spark_secondary.used_percent} reset={codex.spark_secondary.reset} remain />
            )}
            {codex.credits != null && (
              <div className="flex items-center justify-between font-mono text-[11px] pt-1 border-t border-zinc-900">
                <span className="uppercase tracking-[0.2em] text-[10px] text-zinc-500">credits</span>
                <span className="tabular-nums text-white">{codex.credits}</span>
              </div>
            )}
          </>
        ) : (
          <Empty msg={t("util.no_codex_data")} />
        )}
      </Section>
    </div>
  );
}
