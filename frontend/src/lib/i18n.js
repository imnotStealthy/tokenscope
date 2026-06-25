// Lightweight FR/EN i18n. Only human-readable prose is translated; technical
// labels (snake_case, // section comments, table headers, TOOL_LABEL) stay EN.
// Preference persists in localStorage["tokenscope.lang"] (same key as the desktop app).
import { createContext, useContext, useState, useCallback, useEffect } from "react";

const LS_LANG = "tokenscope.lang";

export function getStoredLang() {
  try {
    return localStorage.getItem(LS_LANG) === "fr" ? "fr" : "en";
  } catch {
    return "en";
  }
}

function storeLang(l) {
  try {
    localStorage.setItem(LS_LANG, l);
  } catch {
    /* ignore */
  }
}

// Translation table. Keys are namespaced by component (e.g. "header.entries").
// Add entries here; missing fr keys fall back to en, missing en keys fall back
// to the raw key (so the UI never shows blank).
export const dict = {
  en: {
    "header.tagline": "token consumption tracker",
    "header.entries": "entries",
    "dashboard.confirm_wipe": "Clear ALL imported usage data? This cannot be undone.",
    "dashboard.load_failed": "LOAD FAILED",
    "dashboard.local_unavailable": "local source unavailable",
    "dashboard.data_wiped": "DATA WIPED",
    "dashboard.entries_removed": "{n} entries removed",
    "dashboard.wipe_failed": "WIPE FAILED",
    "dashboard.src_local": "live from ~/.claude & ~/.codex",
    "dashboard.src_stored": "stored usage",
    "dashboard.footer_tail": "local-first · no external telemetry",
    "dashboard.wipe_data": "wipe data",
    "util.pct_left": "{p}% left",
    "util.tag_subscription": "subscription · {plan}",
    "util.tag_api": "api · {plan}",
    "util.na": "n/a",
    "util.api_mode_desc": "API mode ({plan}) · pay-as-you-go — no 5h/weekly quota; cost shown is real spend",
    "util.no_usage_limit_data": "no usage-limit data yet · open claude usage page to refresh",
    "util.not_signed_in": "not signed in to claude (no subscription or API key detected)",
    "util.no_codex_data": "no codex rate-limit data in recent sessions (run codex once to populate)",
    "summary.entries_range": "{n} entries · selected range",
    "summary.prompt_tokens": "prompt tokens",
    "summary.completion_tokens": "completion tokens",
    "summary.today_cost_tok": "today: {cost} / {tok} tok",
    "project.count": "{n} projects",
    "project.no_data": "no project data · ensure ~/.claude or ~/.codex sessions exist",
    "model.count": "{n} models",
    "model.no_data": "no data · import a CSV/JSON or load demo data",
    "chart.per_tool_daily": "per tool · daily",
    "chart.threshold": "THRESHOLD {value}",
    "threshold.breached": "breached",
    "threshold.nominal": "nominal",
    "threshold.max_tokens_day": "max tokens / day",
    "threshold.max_usd_day": "max usd / day",
    "threshold.saving": "saving…",
    "threshold.save": "save threshold",
    "threshold.toast_updated": "THRESHOLD UPDATED",
    "threshold.toast_save_failed": "SAVE FAILED",
    "recent.loading": "loading…",
    "recent.shown": "{n} shown",
    "recent.no_entries": "no entries yet",
    "recent.delete": "delete",
    "apikey.open_no_key": "api: open · no key required",
    "apikey.authenticated": "authenticated",
    "apikey.key_required": "key required",
    "apikey.placeholder": "paste X-API-Key…",
    "apikey.toggle_visibility": "toggle visibility",
    "apikey.save": "save",
    "apikey.clear": "clear",
    "apikey.toast_saved": "API KEY SAVED",
    "apikey.toast_cleared": "API KEY CLEARED",
    "upload.imported": "IMPORTED {filename}",
    "upload.imported_desc": "{inserted} inserted · {skipped} skipped",
    "upload.import_failed": "IMPORT FAILED",
    "upload.demo_loaded": "DEMO DATA LOADED",
    "upload.demo_loaded_desc": "{n} synthetic entries created",
    "upload.seed_failed": "SEED FAILED",
    "upload.loading": "loading…",
    "upload.load_demo": "load demo data",
    "upload.parsing": "PARSING FILE…",
    "upload.drop_here": "DROP CSV / JSON HERE",
    "upload.expected_fields": "expected fields:",
    "tray.label": "tray",
    "tray.title_live": "tray · live",
    "tray.idle": "idle",
    "tray.minimize": "minimize",
    "tray.last": "last:",
  },
  fr: {
    "header.tagline": "suivi de consommation de tokens",
    "header.entries": "entrées",
    "dashboard.confirm_wipe": "Effacer TOUTES les données d'usage importées ? Action irréversible.",
    "dashboard.load_failed": "ÉCHEC CHARGEMENT",
    "dashboard.local_unavailable": "source locale indisponible",
    "dashboard.data_wiped": "DONNÉES EFFACÉES",
    "dashboard.entries_removed": "{n} entrées supprimées",
    "dashboard.wipe_failed": "ÉCHEC EFFACEMENT",
    "dashboard.src_local": "en direct depuis ~/.claude & ~/.codex",
    "dashboard.src_stored": "usage stocké",
    "dashboard.footer_tail": "local-first · aucune télémétrie externe",
    "dashboard.wipe_data": "effacer données",
    "util.pct_left": "{p}% restant",
    "util.tag_subscription": "abonnement · {plan}",
    "util.tag_api": "api · {plan}",
    "util.na": "n/d",
    "util.api_mode_desc": "mode API ({plan}) · paiement à l'usage — pas de quota 5h/hebdo; le coût affiché est la dépense réelle",
    "util.no_usage_limit_data": "aucune donnée de limite d'usage · ouvrir la page d'usage claude pour actualiser",
    "util.not_signed_in": "non connecté à claude (aucun abonnement ni clé API détecté)",
    "util.no_codex_data": "aucune donnée de limite codex dans les sessions récentes (lancer codex une fois pour la remplir)",
    "summary.entries_range": "{n} entrées · plage sélectionnée",
    "summary.prompt_tokens": "tokens du prompt",
    "summary.completion_tokens": "tokens de complétion",
    "summary.today_cost_tok": "aujourd'hui : {cost} / {tok} tok",
    "project.count": "{n} projets",
    "project.no_data": "aucune donnée de projet · vérifie que des sessions ~/.claude ou ~/.codex existent",
    "model.count": "{n} modèles",
    "model.no_data": "aucune donnée · importez un CSV/JSON ou chargez les données de démo",
    "chart.per_tool_daily": "par outil · quotidien",
    "chart.threshold": "SEUIL {value}",
    "threshold.breached": "dépassé",
    "threshold.nominal": "nominal",
    "threshold.max_tokens_day": "tokens max / jour",
    "threshold.max_usd_day": "usd max / jour",
    "threshold.saving": "enregistrement…",
    "threshold.save": "enregistrer le seuil",
    "threshold.toast_updated": "SEUIL MIS À JOUR",
    "threshold.toast_save_failed": "ÉCHEC DE L'ENREGISTREMENT",
    "recent.loading": "chargement…",
    "recent.shown": "{n} affichés",
    "recent.no_entries": "aucune entrée pour l'instant",
    "recent.delete": "supprimer",
    "apikey.open_no_key": "api : ouverte · aucune clé requise",
    "apikey.authenticated": "authentifié",
    "apikey.key_required": "clé requise",
    "apikey.placeholder": "coller X-API-Key…",
    "apikey.toggle_visibility": "basculer la visibilité",
    "apikey.save": "enregistrer",
    "apikey.clear": "effacer",
    "apikey.toast_saved": "CLÉ API ENREGISTRÉE",
    "apikey.toast_cleared": "CLÉ API EFFACÉE",
    "upload.imported": "IMPORTÉ {filename}",
    "upload.imported_desc": "{inserted} insérés · {skipped} ignorés",
    "upload.import_failed": "ÉCHEC DE L'IMPORT",
    "upload.demo_loaded": "DONNÉES DÉMO CHARGÉES",
    "upload.demo_loaded_desc": "{n} entrées synthétiques créées",
    "upload.seed_failed": "ÉCHEC DU SEED",
    "upload.loading": "chargement…",
    "upload.load_demo": "charger données démo",
    "upload.parsing": "ANALYSE DU FICHIER…",
    "upload.drop_here": "DÉPOSER CSV / JSON ICI",
    "upload.expected_fields": "champs attendus :",
    "tray.label": "tray",
    "tray.title_live": "tray · live",
    "tray.idle": "inactif",
    "tray.minimize": "réduire",
    "tray.last": "last:",
  },
};

const Ctx = createContext({ lang: "en", setLang: () => {}, t: (k) => k });

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(getStoredLang());

  useEffect(() => {
    try {
      document.documentElement.lang = lang;
    } catch {
      /* ignore */
    }
  }, [lang]);

  const setLang = useCallback((l) => {
    const v = l === "fr" ? "fr" : "en";
    storeLang(v);
    setLangState(v);
  }, []);

  const t = useCallback(
    (key, vars = {}) => {
      const d = dict[lang] || dict.en;
      const s = key in d ? d[key] : key in dict.en ? dict.en[key] : key;
      return String(s).replace(/\{(\w+)\}/g, (_, n) => (vars[n] != null ? vars[n] : ""));
    },
    [lang]
  );

  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>;
}

export function useLang() {
  return useContext(Ctx);
}
