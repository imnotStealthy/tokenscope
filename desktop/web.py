"""Embedded single-file dashboard served by the tray app (no React build needed)."""

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>TokenScope · Tray</title>
<style>
  :root{
    --bg:#000;--surface:#0A0A0A;--surface2:#121212;--border:#27272A;
    --tx:#fff;--tx2:#A1A1AA;--tx3:#52525B;--red:#FF3B30;--yellow:#FFCC00;
    --mono:'JetBrains Mono','IBM Plex Mono',ui-monospace,Consolas,monospace;
    --barTrack:#18181b;--barFill:#fff;--rowLine:#161618;--rowHover:#0d0d0d;
    --segBg:rgba(255,255,255,.012);--segHover:rgba(255,255,255,.05);
    --segActiveBg:#fff;--segActiveFg:#000;--inputBg:#000;
    --headFrom:rgba(0,0,0,.92);--headTo:rgba(0,0,0,.72);
    --headInset:rgba(255,255,255,.04);--headShadow:rgba(0,0,0,.9);
    --brandFrom:#fff;--brandTo:#c4c4c8;--brandDot1:#fff;--brandDot2:#52525b;--brandGlow:rgba(255,255,255,.35);
    --scrollThumb:#1d1d20;--scrollEdge:#000;--scrollHover:#34343a;--selBg:rgba(255,255,255,.16);
    --cClaude:#fff;--cCodex:#71717A;--cAg:#FFCC00;--gridLine:#1a1a1c;
  }
  html[data-theme="light"]{
    --bg:#fff;--surface:#fff;--surface2:#F4F4F5;--border:#E4E4E7;
    --tx:#09090B;--tx2:#52525B;--tx3:#71717A;
    --barTrack:#E4E4E7;--barFill:#09090B;--rowLine:#EDEDF0;--rowHover:#F4F4F5;
    --segBg:rgba(0,0,0,.015);--segHover:rgba(0,0,0,.05);
    --segActiveBg:#09090B;--segActiveFg:#fff;--inputBg:#fff;
    --headFrom:rgba(255,255,255,.92);--headTo:rgba(255,255,255,.72);
    --headInset:rgba(0,0,0,.04);--headShadow:rgba(0,0,0,.12);
    --brandFrom:#09090B;--brandTo:#52525B;--brandDot1:#09090B;--brandDot2:#a1a1aa;--brandGlow:rgba(0,0,0,.18);
    --scrollThumb:#c4c4c8;--scrollEdge:#fff;--scrollHover:#a1a1aa;--selBg:rgba(0,0,0,.12);
    --cClaude:#09090B;--cCodex:#A1A1AA;--cAg:#EAB308;--gridLine:#EDEDF0;
  }
  *{box-sizing:border-box}
  html{scrollbar-width:thin;scrollbar-color:var(--scrollThumb) var(--scrollEdge)}
  body{margin:0;background:var(--bg);color:var(--tx);font-family:var(--mono);
       font-size:12px;-webkit-font-smoothing:antialiased;overflow-y:scroll;
       transition:background .25s,color .25s}
  a{color:inherit}
  /* scrollbar — invisible track, slim self-fading thumb (theme-aware) */
  ::-webkit-scrollbar{width:10px;height:10px;background:transparent}
  ::-webkit-scrollbar-track{background:transparent}
  ::-webkit-scrollbar-thumb{background:var(--scrollThumb);border:3px solid var(--scrollEdge);border-radius:8px;
       background-clip:padding-box;min-height:40px}
  ::-webkit-scrollbar-thumb:hover{background:var(--scrollHover);background-clip:padding-box}
  ::-webkit-scrollbar-corner{background:transparent}
  ::selection{background:var(--selBg)}
  .wrap{max-width:1400px;margin:0 auto;padding:0 24px 64px}
  header{position:sticky;top:0;z-index:10;
      background:linear-gradient(180deg,var(--headFrom) 0%,var(--headTo) 100%);
      backdrop-filter:blur(14px) saturate(150%);-webkit-backdrop-filter:blur(14px) saturate(150%);
      border-bottom:1px solid var(--border);
      box-shadow:inset 0 1px 0 var(--headInset),0 10px 30px -16px var(--headShadow)}
  .hd{display:flex;align-items:center;justify-content:space-between;gap:16px;
      flex-wrap:wrap;padding:14px 24px;max-width:1400px;margin:0 auto}
  .brand{display:flex;align-items:center;gap:10px}
  .brand::before{content:"";width:8px;height:8px;border-radius:2px;
      background:linear-gradient(135deg,var(--brandDot1),var(--brandDot2));box-shadow:0 0 10px var(--brandGlow)}
  .brand .title{font-size:15px;font-weight:600;letter-spacing:.02em;
      background:linear-gradient(180deg,var(--brandFrom),var(--brandTo));-webkit-background-clip:text;
      background-clip:text;-webkit-text-fill-color:transparent}
  .brand .sub{font-size:10px;text-transform:uppercase;letter-spacing:.25em;color:var(--tx3)}
  .controls{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
  .meta{font-size:11px;color:var(--tx2);display:flex;align-items:center;gap:8px}
  .dot{width:7px;height:7px;border-radius:50%;background:var(--red);
      box-shadow:0 0 8px currentColor;transition:background .3s}
  .dot.ok{background:#22c55e}
  .dot.busy{background:var(--yellow)}
  .seg{display:flex;border:1px solid var(--border);border-radius:7px;overflow:hidden;
      background:var(--segBg)}
  .seg button{font-family:var(--mono);font-size:11px;text-transform:uppercase;
      letter-spacing:.2em;padding:6px 12px;background:transparent;color:var(--tx2);
      border:0;cursor:pointer;transition:background .12s,color .12s}
  .seg button:hover{background:var(--segHover);color:var(--tx)}
  .seg button.active{background:var(--segActiveBg);color:var(--segActiveFg)}
  .seg button.active:hover{background:var(--segActiveBg);color:var(--segActiveFg)}
  .car{color:var(--tx3);font-size:11px;margin-right:6px;display:inline-block;user-select:none}
  .card .head{cursor:pointer}
  .card.collapsed > *:not(.head){display:none}
  .lbl{font-size:10px;text-transform:uppercase;letter-spacing:.25em;color:var(--tx3)}
  .grid{display:grid;gap:16px}
  .g2{grid-template-columns:1fr}
  .g4{grid-template-columns:repeat(2,1fr)}
  @media(min-width:900px){.g2{grid-template-columns:1fr 1fr}.g4{grid-template-columns:repeat(4,1fr)}}
  section{margin-top:24px}
  .card{border:1px solid var(--border);background:var(--surface)}
  .card .head{display:flex;align-items:center;justify-content:space-between;
      padding:12px 16px;border-bottom:1px solid var(--border)}
  .card .body{padding:16px}
  .stat{border:1px solid var(--border);background:var(--surface);padding:20px;
        display:flex;flex-direction:column;gap:12px}
  .stat .v{font-size:30px;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
  .stat .s{font-size:11px;color:var(--tx2);font-variant-numeric:tabular-nums}
  .bar{height:8px;background:var(--barTrack);position:relative;margin-top:6px}
  .bar > i{display:block;height:100%;background:var(--barFill);transition:width .3s}
  .bar.warn > i{background:var(--yellow)} .bar.bad > i{background:var(--red)}
  .barhd{display:flex;justify-content:space-between;align-items:center;
         font-size:10px;text-transform:uppercase;letter-spacing:.2em;color:var(--tx3)}
  .barhd .r{color:var(--tx3);text-transform:none;letter-spacing:normal}
  .barhd .p{font-variant-numeric:tabular-nums}
  .b5{margin-bottom:18px}
  input.num{background:var(--inputBg);border:1px solid var(--border);color:var(--tx);font-family:var(--mono);
            font-size:12px;padding:6px 8px;width:100%}
  input.num:focus{outline:none;border-color:var(--tx)}
  table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
  th{font-size:10px;text-transform:uppercase;letter-spacing:.2em;color:var(--tx3);
     font-weight:500;text-align:right;padding:12px 16px;border-bottom:1px solid var(--border)}
  th[data-k]{cursor:pointer;user-select:none;transition:color .12s}
  th[data-k]:hover{color:var(--tx)}
  th.s-asc::after{content:" ▲";font-size:8px} th.s-desc::after{content:" ▼";font-size:8px}
  .upd{display:none;align-items:center;gap:6px;border:1px solid var(--yellow);border-radius:7px;
       padding:6px 12px;font-size:11px;letter-spacing:.06em;color:var(--yellow);text-decoration:none}
  .upd:hover{background:rgba(255,204,0,.1)}
  th.l,td.l{text-align:left}
  td{padding:10px 16px;border-bottom:1px solid var(--rowLine);font-size:12px}
  tr:hover td{background:var(--rowHover)}
  .tag{display:inline-block;border:1px solid var(--border);padding:1px 6px;margin-right:6px;
       font-size:9px;text-transform:uppercase;letter-spacing:.15em;color:var(--tx2)}
  .muted{color:var(--tx3)} .w{color:var(--tx)} .empty{color:var(--tx3);padding:24px 16px;text-align:center}
  .about p{margin:0 0 16px;max-width:760px;font-size:12px;line-height:1.7;letter-spacing:.02em;
           text-transform:none;color:var(--tx2)}
  .brandbox{display:inline-flex;align-items:center;gap:22px;background:#0A0A0A;
            border:1px solid var(--border);border-radius:10px;padding:14px 22px}
  .brandbox svg{display:block}
  .brandbox .se{height:26px;width:auto}
  .brandbox .wm{height:17px;width:auto}
  .about .by{display:block;margin-top:12px;font-size:10px;text-transform:uppercase;
             letter-spacing:.25em;color:var(--tx3)}
  .about a.gh{display:inline-flex;align-items:center;gap:8px;margin-top:14px;
             border:1px solid var(--border);border-radius:7px;padding:8px 12px;
             font-size:11px;letter-spacing:.03em;color:var(--tx2);text-decoration:none;
             transition:background .12s,color .12s,border-color .12s}
  .about a.gh:hover{background:var(--segHover);color:var(--tx);border-color:var(--tx3)}
  .about a.gh svg{width:15px;height:15px;fill:currentColor}
  .foot{margin-top:32px;padding-top:24px;border-top:1px solid var(--rowLine);
        font-size:10px;text-transform:uppercase;letter-spacing:.25em;color:var(--tx3)}
  /* tokens_over_time chart */
  .chart-wrap{position:relative}
  #chart-svg{display:block;width:100%}
  #chart-svg text{font-family:var(--mono);font-size:10px;fill:var(--tx3)}
  #chart-svg .grid{stroke:var(--gridLine)}
  #chart-svg .hband{fill:transparent;cursor:crosshair}
  #chart-svg .hband:hover{fill:var(--segHover)}
  .chart-tip{position:absolute;pointer-events:none;display:none;z-index:6;min-width:170px;
             background:var(--surface2);border:1px solid var(--border);border-radius:7px;
             padding:9px 11px;font-size:11px;box-shadow:0 12px 32px -10px rgba(0,0,0,.55)}
  .chart-tip .td{font-size:10px;text-transform:uppercase;letter-spacing:.2em;color:var(--tx3);margin-bottom:7px}
  .chart-tip .tr{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:1.5px 0}
  .chart-tip .tr .n{display:flex;align-items:center;gap:7px;color:var(--tx2)}
  .chart-tip .tr .v{font-variant-numeric:tabular-nums;color:var(--tx)}
  .chart-tip .tr.tt{border-top:1px solid var(--rowLine);margin-top:5px;padding-top:5px}
  .sw{width:8px;height:8px;border-radius:2px;display:inline-block;flex:0 0 8px}
  .legend{display:flex;align-items:center;gap:14px;letter-spacing:.15em}
  .legend .li{display:flex;align-items:center;gap:6px}
</style>
</head>
<body>
<header>
  <div class="hd">
    <div class="brand">
      <span class="title">TOKENSCOPE</span>
      <span class="sub" data-i18n="brand_sub">tray · live local usage</span>
    </div>
    <div class="controls">
      <div class="meta"><span id="dot" class="dot"></span><span id="status">connecting…</span></div>
      <div class="seg" id="tool">
        <button data-t="" class="active">all</button>
        <button data-t="claude_api">claude</button>
        <button data-t="codex">codex</button>
        <button data-t="antigravity">antigravity</button>
      </div>
      <div class="seg" id="range">
        <button data-d="1">24h</button>
        <button data-d="7">7d</button>
        <button data-d="30" class="active">30d</button>
        <button data-d="90">90d</button>
        <button data-d="100000">life</button>
      </div>
      <div class="seg" id="lang">
        <button data-l="en">EN</button>
        <button data-l="fr">FR</button>
      </div>
      <div class="seg" id="theme">
        <button data-th="dark">dark</button>
        <button data-th="light">light</button>
      </div>
      <div class="seg" id="export" title="export current summary">
        <button data-x="csv">csv</button>
        <button data-x="json">json</button>
      </div>
      <a class="upd" id="upd" target="_blank" rel="noopener noreferrer"></a>
    </div>
  </div>
</header>

<div class="wrap">
  <section id="util-section">
    <div class="lbl" style="margin-bottom:10px">// subscription_utilization</div>
    <div class="grid g2" id="util-grid">
      <div class="card" id="cl-card" data-key="util-claude"><div class="head"><span class="lbl"><span data-i18n="claude_sub">claude · subscription</span></span><span class="lbl" id="cl-src">—</span></div><div class="body" id="cl-body"></div></div>
      <div class="card" id="cx-card" data-key="util-codex"><div class="head"><span class="lbl"><span data-i18n="codex_sub">codex · subscription</span></span><span class="lbl" id="cx-src">—</span></div><div class="body" id="cx-body"></div></div>
    </div>
  </section>

  <section class="grid g4" id="cards"></section>

  <section>
    <div class="card" data-key="chart">
      <div class="head"><span class="lbl">// tokens_over_time</span><span class="lbl legend" id="chart-legend"></span></div>
      <div class="body chart-wrap">
        <svg id="chart-svg" height="230" role="img" aria-label="Daily token usage"></svg>
        <div class="chart-tip" id="chart-tip"></div>
        <div class="empty" id="chart-empty" style="display:none"></div>
      </div>
    </div>
  </section>

  <section>
    <div class="card" data-key="budget">
      <div class="head"><span class="lbl">// budget · cost tracking</span><span class="lbl" id="bud-mode">—</span></div>
      <div class="body">
        <div id="bud-bars"></div>
        <div class="grid g2" style="gap:12px;margin-top:2px">
          <div><div class="lbl" style="margin-bottom:5px" data-i18n="daily_budget">daily budget ($)</div><input id="bud-daily" class="num" type="number" step="0.01" min="0"></div>
          <div><div class="lbl" style="margin-bottom:5px" data-i18n="monthly_budget">monthly budget ($)</div><input id="bud-monthly" class="num" type="number" step="0.01" min="0"></div>
        </div>
      </div>
    </div>
  </section>

  <section>
    <div class="card" data-key="project">
      <div class="head"><span class="lbl">// usage_by_project</span><span class="lbl" id="proj-n">0 projects</span></div>
      <div style="overflow-x:auto"><table id="proj-table">
        <thead><tr><th class="l" data-k="project">project</th><th class="l">tools</th><th data-k="in">in</th><th data-k="out">out</th><th data-k="total">total</th><th data-k="calls">calls</th><th data-k="cost">cost</th></tr></thead>
        <tbody id="proj-rows"></tbody>
      </table></div>
    </div>
  </section>

  <section>
    <div class="card" data-key="model">
      <div class="head"><span class="lbl">// breakdown_by_model</span><span class="lbl" id="mdl-n">0 models</span></div>
      <div style="overflow-x:auto"><table id="mdl-table">
        <thead><tr><th class="l" data-k="tool">tool</th><th class="l" data-k="model">model</th><th data-k="in">in</th><th data-k="out">out</th><th data-k="total">total</th><th data-k="calls">calls</th><th data-k="cost">cost</th></tr></thead>
        <tbody id="mdl-rows"></tbody>
      </table></div>
    </div>
  </section>

  <section>
    <div class="card about" data-key="about">
      <div class="head"><span class="lbl"><span data-i18n="about_title">// about</span></span></div>
      <div class="body">
        <p data-i18n="about_body">TokenScope was built to monitor token consumption.</p>
        <div class="brandbox">
          <svg class="se" xmlns="http://www.w3.org/2000/svg" viewBox="-0.5 -0.5 12 8" role="img" aria-label="StealthyLabs" shape-rendering="crispEdges">
            <defs><g id="se">
              <rect x="0" y="0" width="5" height="1"/><rect x="0" y="1" width="1" height="2"/><rect x="0" y="3" width="5" height="1"/><rect x="4" y="4" width="1" height="2"/><rect x="0" y="6" width="5" height="1"/>
              <rect x="6" y="0" width="1" height="7"/><rect x="7" y="0" width="4" height="1"/><rect x="7" y="3" width="3" height="1"/><rect x="7" y="6" width="4" height="1"/>
            </g></defs>
            <use href="#se" x="0.28" fill="#1fd8ff"/><use href="#se" x="-0.2" fill="#ff2e6e" opacity="0.4"/><use href="#se" fill="#ededed"/>
          </svg>
          <svg class="wm" xmlns="http://www.w3.org/2000/svg" viewBox="-0.5 -0.5 48.5 8" role="img" aria-label="Stealthy" shape-rendering="crispEdges">
            <defs><g id="wm">
              <rect x="0" y="0" width="5" height="1"/><rect x="0" y="1" width="1" height="2"/><rect x="0" y="3" width="5" height="1"/><rect x="4" y="4" width="1" height="2"/><rect x="0" y="6" width="5" height="1"/>
              <rect x="6" y="0" width="5" height="1"/><rect x="8" y="1" width="1" height="6"/>
              <rect x="12" y="0" width="1" height="7"/><rect x="13" y="0" width="4" height="1"/><rect x="13" y="3" width="3" height="1"/><rect x="13" y="6" width="4" height="1"/>
              <rect x="18" y="1" width="1" height="6"/><rect x="22" y="1" width="1" height="6"/><rect x="19" y="0" width="3" height="1"/><rect x="19" y="3" width="3" height="1"/>
              <rect x="24" y="0" width="1" height="7"/><rect x="25" y="6" width="4" height="1"/>
              <rect x="30" y="0" width="5" height="1"/><rect x="32" y="1" width="1" height="6"/>
              <rect x="36" y="0" width="1" height="7"/><rect x="40" y="0" width="1" height="7"/><rect x="37" y="3" width="3" height="1"/>
              <rect x="42" y="0" width="1" height="3"/><rect x="46" y="0" width="1" height="3"/><rect x="43" y="2" width="3" height="1"/><rect x="44" y="3" width="1" height="4"/>
            </g></defs>
            <use href="#wm" x="0.28" fill="#1fd8ff"/><use href="#wm" x="-0.22" fill="#ff2e6e" opacity="0.4"/><use href="#wm" fill="#ededed"/>
          </svg>
        </div>
        <span class="by" data-i18n="about_by">by StealthyLabs</span>
        <div>
          <a class="gh" href="https://github.com/imnotStealthy" target="_blank" rel="noopener noreferrer">
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
            github.com/imnotStealthy
          </a>
        </div>
      </div>
    </div>
  </section>

  <div class="foot" id="foot" data-i18n="footer">TokenScope · live from ~/.claude &amp; ~/.codex · local-first · no external telemetry</div>
</div>

<script>
const APP_VERSION="1.3.1", REPO="imnotStealthy/tokenscope";
const TOOL_LABEL={claude_api:"Claude",codex:"Codex",antigravity:"Antigravity"};
let DAYS=30, TOOL="", LAST_S=null, LAST_U=null, LOADING=false;
const SORT={proj:{k:null,dir:-1}, mdl:{k:null,dir:-1}};
const LS_D="tokenscope.budget.daily", LS_M="tokenscope.budget.monthly";
const rangeLabel=d=>d===1?"24h":d>=100000?"lifetime":d+"d";

// --- i18n (FR/EN) -- only readable prose is translated; technical labels stay EN ---
const I18N={
  en:{ brand_sub:"tray · live local usage", connecting:"connecting…", loading:"loading {r}…",
    live:"live", error:"error: {m}", claude_sub:"claude · subscription", codex_sub:"codex · subscription",
    subscription_word:"subscription", api_word:"api", na:"n/a",
    api_desc:"API mode ({plan}) · pay-as-you-go — cost = real spend",
    cl_waiting:"waiting for usage data · open claude usage page to refresh",
    cl_none:"not signed in (no subscription or API key)",
    cx_norate:"no rate-limit data", cx_none:"no codex rate-limit data in recent sessions",
    left:"{p}% left", calls_range:"{n} calls · range", prompt_fresh:"prompt (fresh)",
    completion:"completion", cache_est:"est. · cache {n} rd",
    projects:"{n} projects", no_project:"no project data · ensure ~/.claude or ~/.codex sessions exist",
    models:"{n} models", no_model:"no model data",
    tt_total:"total", tt_cost:"cost", no_chart:"no daily data yet in this range",
    bud_real:"real spend (api)", bud_est:"est. (subscription)", today:"today", month:"this month",
    over:" · over {x}", daily_budget:"daily budget ($)", monthly_budget:"monthly budget ($)",
    now:"now", in_prefix:"in", u_d:"d", u_h:"h", u_m:"m",
    about_title:"// about", about_by:"by StealthyLabs",
    about_body:"TokenScope was built to monitor token consumption and usage across Claude Code and Codex — to see, in one place and in real time, how many tokens I burn per project and per model, what it costs, and how much of my subscription quota is left. Local-first: it only reads my own session files, with no telemetry.",
    footer:"TokenScope · live from ~/.claude & ~/.codex · local-first · no external telemetry" },
  fr:{ brand_sub:"tray · usage local en direct", connecting:"connexion…", loading:"chargement {r}…",
    live:"en direct", error:"erreur : {m}", claude_sub:"claude · abonnement", codex_sub:"codex · abonnement",
    subscription_word:"abonnement", api_word:"api", na:"n/d",
    api_desc:"mode API ({plan}) · paiement à l'usage — coût = dépense réelle",
    cl_waiting:"en attente de données · ouvre la page d'usage claude pour rafraîchir",
    cl_none:"non connecté (aucun abonnement ni clé API)",
    cx_norate:"aucune donnée de limite", cx_none:"aucune donnée de limite codex dans les sessions récentes",
    left:"{p}% restant", calls_range:"{n} appels · plage", prompt_fresh:"prompt (frais)",
    completion:"complétion", cache_est:"est. · cache {n} lec",
    projects:"{n} projets", no_project:"aucune donnée projet · vérifie les sessions ~/.claude ou ~/.codex",
    models:"{n} modèles", no_model:"aucune donnée modèle",
    tt_total:"total", tt_cost:"coût", no_chart:"aucune donnée quotidienne sur cette plage",
    bud_real:"dépense réelle (api)", bud_est:"est. (abonnement)", today:"aujourd'hui", month:"ce mois",
    over:" · dépassé de {x}", daily_budget:"budget quotidien ($)", monthly_budget:"budget mensuel ($)",
    now:"maintenant", in_prefix:"dans", u_d:"j", u_h:"h", u_m:"m",
    about_title:"// à propos", about_by:"par StealthyLabs",
    about_body:"TokenScope a été créé pour monitorer la consommation et l'usage des tokens sur Claude Code et Codex — voir, au même endroit et en temps réel, combien de tokens je consomme par projet et par modèle, ce que ça coûte, et combien il reste de mon quota d'abonnement. Local-first : il lit uniquement mes propres fichiers de session, sans aucune télémétrie.",
    footer:"TokenScope · en direct depuis ~/.claude & ~/.codex · local-first · aucune télémétrie externe" }
};
let LANG=localStorage.getItem("tokenscope.lang")==="fr"?"fr":"en";
const t=(k,v={})=>(I18N[LANG][k]??I18N.en[k]??k).replace(/\{(\w+)\}/g,(_,n)=>v[n]??"");
function applyStatic(){document.querySelectorAll("[data-i18n]").forEach(el=>{el.textContent=t(el.dataset.i18n);});}
function setStatus(){document.getElementById("status").textContent=t("live")+" · "+new Date().toISOString().slice(11,19)+" UTC";}
let THEME=localStorage.getItem("tokenscope.theme")==="light"?"light":"dark";
function syncWindowTheme(){fetch("/api/theme?theme="+encodeURIComponent(THEME),{cache:"no-store"}).catch(()=>{});}
function applyTheme(){if(THEME==="light")document.documentElement.setAttribute("data-theme","light");else document.documentElement.removeAttribute("data-theme");syncWindowTheme();}

function fmtN(n){if(n==null)return"—";n=Number(n);if(isNaN(n))return"—";
  if(n>=1e9)return(n/1e9).toFixed(2)+"B";if(n>=1e6)return(n/1e6).toFixed(2)+"M";
  if(n>=1e3)return(n/1e3).toFixed(2)+"k";return n.toLocaleString("en-US");}
function fmtC(n){n=Number(n||0);return"$"+n.toFixed(n<1?4:2);}
function fmtReset(iso){if(!iso)return"";const tt=new Date(iso).getTime();if(isNaN(tt))return"";
  let d=tt-Date.now();if(d<=0)return t("now");let m=Math.floor(d/6e4),dd=Math.floor(m/1440),
  h=Math.floor((m%1440)/60),mm=m%60;const P=t("in_prefix");
  if(dd>0)return P+" "+dd+t("u_d")+" "+h+t("u_h");
  if(h>0)return P+" "+h+t("u_h")+" "+mm+t("u_m");return P+" "+mm+t("u_m");}
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
// Raw API model ids -> friendly display names. e.g. claude-opus-4-8 -> "Claude Opus 4.8",
// gpt-5.3-codex -> "GPT 5.3 Codex", claude-haiku-4-5-20251001 -> "Claude Haiku 4.5".
// Already-friendly names (Antigravity's "Gemini 3.5 Flash (Medium)") pass through.
const MDL_VENDOR={claude:"Claude",gpt:"GPT",gemini:"Gemini"};
const MDL_WORD={opus:"Opus",sonnet:"Sonnet",haiku:"Haiku",fable:"Fable",mythos:"Mythos",
  codex:"Codex",flash:"Flash",pro:"Pro",lite:"Lite",mini:"Mini",nano:"Nano",oss:"OSS",turbo:"Turbo"};
function prettyModel(id){
  if(!id) return id;
  if(/[A-Z\s()]/.test(id)) return id;                 // already a display name
  const parts=id.toLowerCase().split("-");
  if(parts.length>1 && /^\d{8}$/.test(parts[parts.length-1])) parts.pop();  // drop yyyymmdd snapshot
  const out=[];
  for(let i=0;i<parts.length;i++){
    let p=parts[i];
    if(/^[\d.]+$/.test(p)){                            // merge consecutive numeric tokens: 4 + 8 -> 4.8
      while(i+1<parts.length && /^[\d.]+$/.test(parts[i+1])) p+="."+parts[++i];
      out.push(p);
    } else if(i===0 && MDL_VENDOR[p]) out.push(MDL_VENDOR[p]);
    else out.push(MDL_WORD[p]||(p.charAt(0).toUpperCase()+p.slice(1)));
  }
  return out.join(" ");
}

function bar(label,pct,reset){pct=Math.max(0,Math.min(100,Number(pct)||0));
  const cls=pct>=90?"bad":pct>=75?"warn":"";
  return `<div class="b5"><div class="barhd"><span>${esc(label)}</span>
    <span><span class="r">${esc(fmtReset(reset))}</span> &nbsp; <span class="p">${pct.toFixed(0)}%</span></span></div>
    <div class="bar ${cls}"><i style="width:${pct}%"></i></div></div>`;}

// Codex shows REMAINING (100% full -> 0% = all used); red when low.
function barRemain(label,usedPct,reset){
  const used=Math.max(0,Math.min(100,Number(usedPct)||0)), rem=100-used;
  const cls=rem<=10?"bad":rem<=25?"warn":"";
  return `<div class="b5"><div class="barhd"><span>${esc(label)}</span>
    <span><span class="r">${esc(fmtReset(reset))}</span> &nbsp; <span class="p">${esc(t("left",{p:rem.toFixed(0)}))}</span></span></div>
    <div class="bar ${cls}"><i style="width:${rem}%"></i></div></div>`;
}

function renderUtil(u){
  const cl=u&&u.claude, cx=u&&u.codex;
  // Antigravity has no usable subscription/quota card; only Claude & Codex remain.
  const showCl=!TOOL||TOOL==="claude_api", showCx=!TOOL||TOOL==="codex";
  document.getElementById("cl-card").style.display=showCl?"":"none";
  document.getElementById("cx-card").style.display=showCx?"":"none";
  const _nUtil=[showCl,showCx].filter(Boolean).length;
  // Hide the whole section when no card applies (e.g. the Antigravity tab).
  document.getElementById("util-section").style.display=_nUtil?"":"none";
  document.getElementById("util-grid").style.gridTemplateColumns=_nUtil<=1?"1fr":"";
  const clMode=cl&&cl.mode;
  document.getElementById("cl-src").textContent =
    clMode==="subscription" ? t("subscription_word")+" · "+(cl.plan||"")
    : clMode==="api" ? t("api_word")+" · "+(cl.plan||"")
    : t("na");
  const clb=document.getElementById("cl-body");
  if(cl&&cl.available&&cl.limits&&cl.limits.length){
    clb.innerHTML=cl.limits.map(l=>bar(l.label,l.used_percent,l.reset)).join("");
  } else if(clMode==="api"){
    clb.innerHTML=`<div class="muted">${esc(t("api_desc",{plan:cl.plan||"Claude Platform"}))}</div>`;
  } else if(clMode==="subscription"){
    clb.innerHTML=`<div class="muted">${esc(t("cl_waiting"))}</div>`;
  } else {
    clb.innerHTML=`<div class="muted">${esc(t("cl_none"))}</div>`;
  }
  document.getElementById("cx-src").textContent=cx&&cx.plan_type?cx.plan_type:((cx&&cx.auth_mode)||t("na"));
  const cxb=document.getElementById("cx-body");
  // Always show the limit bars (like the official ChatGPT usage page). When a window has
  // no observed data yet, default to 100% left (0% used) instead of hiding the bar.
  const cxRow=(label,lim)=>lim?barRemain(label,lim.used_percent,lim.reset):barRemain(label,0,null);
  let h="";
  h+=cxRow("5h",cx&&cx.primary);
  h+=cxRow("weekly",cx&&cx.secondary);
  h+=`<div class="barhd" style="padding-top:4px;border-top:1px solid var(--rowLine)"><span>${esc((cx&&cx.spark_label)||"GPT-5.3-Codex-Spark")}</span></div>`;
  h+=cxRow("5h",cx&&cx.spark_primary);
  h+=cxRow("weekly",cx&&cx.spark_secondary);
  if(cx&&cx.credits!=null)h+=`<div class="barhd" style="padding-top:4px;border-top:1px solid var(--rowLine)"><span>credits</span><span class="w p">${esc(cx.credits)}</span></div>`;
  cxb.innerHTML=h;
}

function renderSummary(s){
  const tot=(s&&s.totals)||{input_tokens:0,output_tokens:0,total_tokens:0,cost_usd:0,entries:0};
  document.getElementById("cards").innerHTML=[
    ["total_tokens",fmtN(tot.total_tokens),t("calls_range",{n:(tot.entries||0)})],
    ["input_tokens",fmtN(tot.input_tokens),t("prompt_fresh")],
    ["output_tokens",fmtN(tot.output_tokens),t("completion")],
    ["total_cost_usd",fmtC(tot.cost_usd),t("cache_est",{n:fmtN(tot.cache_read_tokens)})],
  ].map(c=>`<div class="stat"><div class="lbl">${c[0]}</div><div class="v">${c[1]}</div><div class="s">${c[2]}</div></div>`).join("");

  const pr=sortRows((s&&s.by_project)||[], SORT.proj);
  document.getElementById("proj-n").textContent=t("projects",{n:pr.length});
  document.getElementById("proj-rows").innerHTML=pr.length?pr.map(r=>`<tr>
    <td class="l w" title="${esc(r.project)}">${esc(r.project_name||r.project)}</td>
    <td class="l">${Object.keys(r.tools||{}).map(k=>`<span class="tag">${esc(TOOL_LABEL[k]||k)}</span>`).join("")}</td>
    <td class="muted">${fmtN(r.input_tokens)}</td><td class="muted">${fmtN(r.output_tokens)}</td>
    <td class="w">${fmtN((r.input_tokens||0)+(r.output_tokens||0))}</td>
    <td class="muted">${r.entries}</td><td class="w">${fmtC(r.cost_usd)}</td></tr>`).join("")
    :`<tr><td colspan="7" class="empty">${esc(t("no_project"))}</td></tr>`;

  const md=sortRows((s&&s.by_model)||[], SORT.mdl);
  document.getElementById("mdl-n").textContent=t("models",{n:md.length});
  document.getElementById("mdl-rows").innerHTML=md.length?md.map(r=>`<tr>
    <td class="l muted">${esc(TOOL_LABEL[r.tool]||r.tool)}</td><td class="l w" title="${esc(r.model)}">${esc(prettyModel(r.model))}</td>
    <td class="muted">${fmtN(r.input_tokens)}</td><td class="muted">${fmtN(r.output_tokens)}</td>
    <td class="w">${fmtN((r.input_tokens||0)+(r.output_tokens||0))}</td>
    <td class="muted">${r.entries}</td><td class="w">${fmtC(r.cost_usd)}</td></tr>`).join("")
    :`<tr><td colspan="7" class="empty">${esc(t("no_model"))}</td></tr>`;
}

// --- tokens_over_time: dependency-free stacked-bar SVG, theme-aware via CSS vars ---
const CHART_TOOLS=[["claude_api","var(--cClaude)"],["codex","var(--cCodex)"],["antigravity","var(--cAg)"]];
// Hour label for the 24h view: FR "0h..23h", EN "12AM..11PM".
function hourLabel(h){
  if(LANG==="fr") return h+"h";
  return h===0?"12AM":h<12?h+"AM":h===12?"12PM":(h-12)+"PM";
}
// Backend day keys are LOCAL days; format Dates the same way (never toISOString = UTC).
function localDay(d){const p=v=>String(v).padStart(2,"0");return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}`;}
function chartDays(s){
  const byday=(s&&s.by_day)||[];
  if(DAYS===1){                                              // 24h: current LOCAL day, hour by hour
    const map={}; ((s&&s.by_hour)||[]).forEach(h=>{ if(h.hour) map[h.hour]=h; });
    const now=new Date(), p=v=>String(v).padStart(2,"0");
    const dk=localDay(now);
    const out=[];
    for(let h=0;h<24;h++){
      const d=map[`${dk}T${p(h)}`]||{claude_api:0,codex:0,antigravity:0,cost_usd:0};
      out.push({...d, day:`${dk} · ${hourLabel(h)}`, lbl:hourLabel(h)});
    }
    return out;
  }
  const map={}; byday.forEach(d=>{ if(d.day) map[d.day]=d; });
  const mk=d=>({...d, lbl:(d.day||"").slice(5)});
  if(DAYS>90){ return byday.filter(d=>d.day).map(mk); }      // lifetime: real days only
  const out=[], now=Date.now();
  for(let i=DAYS-1;i>=0;i--){
    const day=localDay(new Date(now-i*864e5));
    out.push(mk(map[day]||{day, claude_api:0, codex:0, antigravity:0, cost_usd:0}));
  }
  return out;
}
function niceMax(v){ if(v<=0)return 1; const p=Math.pow(10,Math.floor(Math.log10(v))); const u=v/p;
  return (u<=1?1:u<=2?2:u<=5?5:10)*p; }
function renderChart(s){
  const svg=document.getElementById("chart-svg"), tip=document.getElementById("chart-tip"),
        empty=document.getElementById("chart-empty"), legend=document.getElementById("chart-legend");
  const tools=TOOL?CHART_TOOLS.filter(x=>x[0]===TOOL):CHART_TOOLS;
  legend.innerHTML=tools.map(([k,c])=>`<span class="li"><span class="sw" style="background:${c}"></span>${esc(TOOL_LABEL[k]||k)}</span>`).join("")
    +`<span class="li"><span class="sw" style="background:#22c55e"></span>${esc(t("tt_cost"))} $</span>`;
  const days=chartDays(s);
  const hasData=days.some(d=>tools.some(([k])=>(d[k]||0)>0));
  svg.style.display=hasData?"":"none";
  empty.style.display=hasData?"none":"";
  if(!hasData){ empty.textContent=t("no_chart"); tip.style.display="none"; return; }
  const W=Math.max(320,svg.clientWidth||svg.parentElement.clientWidth||800), H=230,
        padL=44, padR=8, padT=10, padB=22, iw=W-padL-padR, ih=H-padT-padB;
  const max=niceMax(Math.max(...days.map(d=>tools.reduce((a,[k])=>a+(d[k]||0),0))));
  const n=days.length, slot=iw/n, bw=Math.max(1.5,Math.min(26,slot*0.62));
  svg.setAttribute("viewBox",`0 0 ${W} ${H}`); svg.setAttribute("width",W); svg.setAttribute("height",H);
  let g="";
  for(let i=0;i<=4;i++){                                     // y grid + labels
    const y=padT+ih-ih*i/4;
    g+=`<line class="grid" x1="${padL}" y1="${y}" x2="${W-padR}" y2="${y}"/>`;
    g+=`<text x="${padL-6}" y="${y+3}" text-anchor="end">${fmtN(max*i/4)}</text>`;
  }
  const step=DAYS===1?3:Math.max(1,Math.ceil(n/10));         // sparse x labels (every 3h on 24h view)
  days.forEach((d,i)=>{
    if(i%step===0) g+=`<text x="${padL+slot*i+slot/2}" y="${H-6}" text-anchor="middle">${esc(d.lbl??(d.day||"").slice(5))}</text>`;
  });
  days.forEach((d,i)=>{
    const x=padL+slot*i+(slot-bw)/2; let y=padT+ih;
    tools.forEach(([k,c])=>{
      const v=d[k]||0; if(!v)return;
      const h=Math.max(v>0?1:0, v/max*ih); y-=h;
      g+=`<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" style="fill:${c}"/>`;
    });
    g+=`<rect class="hband" data-i="${i}" x="${(padL+slot*i).toFixed(1)}" y="${padT}" width="${slot.toFixed(1)}" height="${ih}"/>`;
  });
  // Daily cost overlay: green line on its own scale (top of plot = costMax).
  const costMax=niceMax(Math.max(...days.map(d=>d.cost_usd||0)));
  if(costMax>0 && days.some(d=>(d.cost_usd||0)>0)){
    const pts=days.map((d,i)=>`${(padL+slot*i+slot/2).toFixed(1)},${(padT+ih-(d.cost_usd||0)/costMax*ih).toFixed(1)}`).join(" ");
    g+=n>1?`<polyline points="${pts}" fill="none" stroke="#22c55e" stroke-width="1.5" opacity=".9"/>`
          :`<circle cx="${padL+slot/2}" cy="${(padT+ih-(days[0].cost_usd||0)/costMax*ih).toFixed(1)}" r="3" fill="#22c55e"/>`;
    g+=`<text x="${W-padR}" y="${padT+9}" text-anchor="end" style="fill:#22c55e">${esc(fmtC(costMax))}</text>`;
  }
  svg.innerHTML=g;
  svg.onmouseleave=()=>{ tip.style.display="none"; };
  svg.onmousemove=e=>{
    const b=e.target.closest(".hband"); if(!b){ tip.style.display="none"; return; }
    const d=days[Number(b.dataset.i)]; if(!d) return;
    const rows=tools.map(([k,c])=>`<div class="tr"><span class="n"><span class="sw" style="background:${c}"></span>${esc(TOOL_LABEL[k]||k)}</span><span class="v">${fmtN(d[k]||0)}</span></div>`).join("");
    const tot=tools.reduce((a,[k])=>a+(d[k]||0),0);
    tip.innerHTML=`<div class="td">${esc(d.day)}</div>${rows}
      <div class="tr tt"><span class="n">${esc(t("tt_total"))}</span><span class="v">${fmtN(tot)}</span></div>
      <div class="tr"><span class="n">${esc(t("tt_cost"))}</span><span class="v">${fmtC(d.cost_usd)}</span></div>`;
    tip.style.display="block";
    const wrap=svg.parentElement.getBoundingClientRect(), tw=tip.offsetWidth;
    let lx=e.clientX-wrap.left+14; if(lx+tw>wrap.width-8) lx=e.clientX-wrap.left-tw-14;
    tip.style.left=Math.max(4,lx)+"px";
    tip.style.top=Math.max(4,e.clientY-wrap.top-10)+"px";
  };
}
let _rsz; window.addEventListener("resize",()=>{ clearTimeout(_rsz); _rsz=setTimeout(()=>{ if(LAST_S) renderChart(LAST_S); },150); });

// --- sortable tables ---
const SORT_VAL={project:r=>String(r.project_name||r.project||"").toLowerCase(),
  tool:r=>String(r.tool||""), model:r=>String(r.model||"").toLowerCase(),
  in:r=>r.input_tokens||0, out:r=>r.output_tokens||0,
  total:r=>(r.input_tokens||0)+(r.output_tokens||0), calls:r=>r.entries||0, cost:r=>r.cost_usd||0};
function sortRows(arr,s){
  if(!s.k||!SORT_VAL[s.k]) return arr;
  const v=SORT_VAL[s.k];
  return arr.slice().sort((a,b)=>{const x=v(a),y=v(b);
    return (typeof x==="string"?x.localeCompare(y):x-y)*s.dir;});
}
function markSort(){
  [["proj-table","proj"],["mdl-table","mdl"]].forEach(([id,key])=>{
    document.querySelectorAll(`#${id} th[data-k]`).forEach(th=>{
      th.classList.remove("s-asc","s-desc");
      const s=SORT[key];
      if(s.k===th.dataset.k) th.classList.add(s.dir===1?"s-asc":"s-desc");
    });
  });
}
[["proj-table","proj"],["mdl-table","mdl"]].forEach(([id,key])=>{
  document.querySelectorAll(`#${id} th[data-k]`).forEach(th=>{
    th.addEventListener("click",()=>{
      const s=SORT[key];
      if(s.k===th.dataset.k){ if(s.dir===1){s.k=null;s.dir=-1;} else s.dir=1; }  // desc -> asc -> default
      else { s.k=th.dataset.k; s.dir=-1; }
      markSort();
      if(LAST_S) renderSummary(LAST_S);
    });
  });
});

// --- CSV / JSON export of the currently loaded summary ---
function download(name,blob){
  const a=document.createElement("a");
  a.href=URL.createObjectURL(blob); a.download=name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(a.href),3000);
}
document.getElementById("export").addEventListener("click",e=>{
  const b=e.target.closest("button"); if(!b||!LAST_S)return;
  const stamp=new Date().toISOString().slice(0,10), range=rangeLabel(DAYS)+(TOOL?"_"+TOOL:"");
  if(b.dataset.x==="json"){
    download(`tokenscope_${range}_${stamp}.json`,
      new Blob([JSON.stringify(LAST_S,null,2)],{type:"application/json"}));
    return;
  }
  const esc0=v=>{v=String(v==null?"":v);return /[",\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v;};
  const lines=[["section","name","tool_or_tools","input_tokens","output_tokens","total_tokens","calls","cost_usd"].join(",")];
  (LAST_S.by_day||[]).forEach(d=>lines.push(["day",d.day,"",d.input_tokens||0,d.output_tokens||0,
    (d.claude_api||0)+(d.codex||0)+(d.antigravity||0),"",d.cost_usd||0].map(esc0).join(",")));
  (LAST_S.by_project||[]).forEach(r=>lines.push(["project",r.project_name||r.project,
    Object.keys(r.tools||{}).join("|"),r.input_tokens||0,r.output_tokens||0,
    (r.input_tokens||0)+(r.output_tokens||0),r.entries||0,r.cost_usd||0].map(esc0).join(",")));
  (LAST_S.by_model||[]).forEach(r=>lines.push(["model",r.model,r.tool,r.input_tokens||0,
    r.output_tokens||0,(r.input_tokens||0)+(r.output_tokens||0),r.entries||0,r.cost_usd||0].map(esc0).join(",")));
  download(`tokenscope_${range}_${stamp}.csv`, new Blob([lines.join("\n")],{type:"text/csv"}));
});

// --- update check: GitHub latest release, cached 6h, shown as a header pill ---
function newerVersion(a,b){
  const x=String(a).split(".").map(Number), y=String(b).split(".").map(Number);
  for(let i=0;i<3;i++){ if((x[i]||0)>(y[i]||0)) return true; if((x[i]||0)<(y[i]||0)) return false; }
  return false;
}
async function checkUpdate(){
  const CK="tokenscope.update.latest";
  let tag=null;
  try{
    const c=JSON.parse(localStorage.getItem(CK)||"null");
    if(c && Date.now()-c.t<216e5) tag=c.tag;
    if(!tag){
      const r=await fetch("https://api.github.com/repos/"+REPO+"/releases/latest",{cache:"no-store"});
      if(!r.ok) return;
      tag=(await r.json()).tag_name||"";
      localStorage.setItem(CK,JSON.stringify({t:Date.now(),tag}));
    }
  }catch(e){ return; }
  const v=String(tag).replace(/^v/,"");
  if(v && newerVersion(v,APP_VERSION)){
    const a=document.getElementById("upd");
    a.textContent="v"+v+" ↗";
    a.href="https://github.com/"+REPO+"/releases/latest";
    a.style.display="inline-flex";
  }
}
checkUpdate();

function getBud(k,def){const v=parseFloat(localStorage.getItem(k));return isFinite(v)&&v>0?v:def;}
function budBar(label,spend,cap){
  const pct=cap>0?Math.min(100,spend/cap*100):0;
  const cls=spend>cap?"bad":pct>=80?"warn":"";
  const over=spend>cap?t("over",{x:fmtC(spend-cap)}):"";
  return `<div class="b5"><div class="barhd"><span>${esc(label)}</span><span class="p">${fmtC(spend)} / ${fmtC(cap)}${esc(over)}</span></div><div class="bar ${cls}"><i style="width:${pct}%"></i></div></div>`;
}
// Budget bars use bs: a dedicated UNFILTERED 31-day summary — the main summary is
// range/tool-filtered and silently under-reported monthly spend (e.g. 7d range).
function renderBudget(bs,u){
  const byday=(bs&&bs.by_day)||[];
  const today=localDay(new Date()), month=today.slice(0,7);
  let td=0, mo=0;
  byday.forEach(d=>{ if(d.day===today) td+=d.cost_usd||0; if((d.day||"").startsWith(month)) mo+=d.cost_usd||0; });
  const dCap=getBud(LS_D,10), mCap=getBud(LS_M,200);
  document.getElementById("bud-bars").innerHTML=budBar(t("today"),td,dCap)+budBar(t("month"),mo,mCap);
  const api=(u&&u.claude&&u.claude.mode==="api")||(u&&u.codex&&u.codex.auth_mode==="apikey");
  document.getElementById("bud-mode").textContent=api?t("bud_real"):t("bud_est");
  const di=document.getElementById("bud-daily"), mi=document.getElementById("bud-monthly");
  if(document.activeElement!==di) di.value=dCap;
  if(document.activeElement!==mi) mi.value=mCap;
}

let LOAD_SEQ=0, LAST_B=null;
function okJson(r){ if(!r.ok) throw new Error("HTTP "+r.status); return r.json(); }
async function load(){
  const my=++LOAD_SEQ;  // drop stale responses: a slow "life" fetch must not overwrite a newer range
  LOADING=true;
  document.getElementById("dot").className="dot busy";
  document.getElementById("status").textContent=t("loading",{r:rangeLabel(DAYS)});
  try{
    const [sr,ur,br]=await Promise.all([
      fetch("/api/local/summary?days="+DAYS+(TOOL?"&tool="+TOOL:"")).then(okJson),
      fetch("/api/local/utilization").then(okJson).catch(()=>null),
      fetch("/api/local/summary?days=31").then(okJson).catch(()=>null),  // budget: unfiltered month
    ]);
    if(my!==LOAD_SEQ) return;
    if(sr&&sr.error) throw new Error(sr.error);
    LAST_S=sr; LAST_U=ur; LAST_B=br;
    renderSummary(sr); renderChart(sr); renderUtil(ur); renderBudget(br,ur);
    document.getElementById("dot").className="dot ok";
    setStatus();
  }catch(e){
    if(my!==LOAD_SEQ) return;
    document.getElementById("dot").className="dot";
    document.getElementById("status").textContent=t("error",{m:e.message});
  }finally{
    if(my===LOAD_SEQ) LOADING=false;
  }
}

document.getElementById("range").addEventListener("click",e=>{
  const b=e.target.closest("button"); if(!b)return;
  DAYS=Number(b.dataset.d);
  document.querySelectorAll("#range button").forEach(x=>x.classList.toggle("active",x===b));
  load();
});
["bud-daily","bud-monthly"].forEach((id,i)=>{
  document.getElementById(id).addEventListener("input",e=>{
    localStorage.setItem(i===0?LS_D:LS_M, e.target.value);
    renderBudget(LAST_B, LAST_U);
  });
});
document.getElementById("tool").addEventListener("click",e=>{
  const b=e.target.closest("button"); if(!b)return;
  TOOL=b.dataset.t;
  document.querySelectorAll("#tool button").forEach(x=>x.classList.toggle("active",x===b));
  load();
});
document.getElementById("lang").addEventListener("click",e=>{
  const b=e.target.closest("button"); if(!b)return;
  LANG=b.dataset.l; localStorage.setItem("tokenscope.lang",LANG);
  document.querySelectorAll("#lang button").forEach(x=>x.classList.toggle("active",x===b));
  applyStatic();
  if(LAST_S){renderSummary(LAST_S); renderChart(LAST_S); renderBudget(LAST_B,LAST_U);}
  if(LAST_U) renderUtil(LAST_U);
  if(!LOADING) setStatus();
});
document.getElementById("theme").addEventListener("click",e=>{
  const b=e.target.closest("button"); if(!b)return;
  THEME=b.dataset.th; localStorage.setItem("tokenscope.theme",THEME);
  document.querySelectorAll("#theme button").forEach(x=>x.classList.toggle("active",x===b));
  applyTheme();
});
function setupCollapse(){
  document.querySelectorAll(".card[data-key]").forEach(c=>{
    const head=c.querySelector(".head"); if(!head) return;
    let car=head.querySelector(".car");
    if(!car){ car=document.createElement("span"); car.className="car";
      const lbl=head.querySelector(".lbl"); if(lbl) lbl.insertBefore(car, lbl.firstChild); }
    const k="tokenscope.collapse."+c.dataset.key;
    const set=col=>{ c.classList.toggle("collapsed",col); if(car) car.textContent=col?"▸ ":"▾ "; };
    set(localStorage.getItem(k)==="1");
    head.addEventListener("click",()=>{ const col=!c.classList.contains("collapsed"); set(col); localStorage.setItem(k,col?"1":"0"); });
  });
}
document.querySelectorAll("#lang button").forEach(x=>x.classList.toggle("active",x.dataset.l===LANG));
document.querySelectorAll("#theme button").forEach(x=>x.classList.toggle("active",x.dataset.th===THEME));
applyTheme();
applyStatic();
document.getElementById("status").textContent=t("connecting");
setupCollapse();
load();
setInterval(load, 10000);                 // refresh data every 10s (near real-time)
setInterval(()=>{                          // tick clock + reset countdowns every second
  if(!LOADING) setStatus();
  if(LAST_U) renderUtil(LAST_U);
}, 1000);
</script>
</body>
</html>
"""


# ===== Tray popup (frameless pywebview window opened from the system-tray icon) =====
TRAY_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>TokenScope Menu</title>
<style>
  :root{
    --bg:#0A0A0A;--surface:#0A0A0A;--border:#27272A;--tx:#fff;--tx2:#A1A1AA;--tx3:#52525B;
    --red:#FF3B30;--yellow:#FFCC00;--green:#22c55e;--track:#1c1c1f;--fill:#fff;
    --hover:rgba(255,255,255,.06);--line:#1a1a1c;
    --mono:'JetBrains Mono','IBM Plex Mono',ui-monospace,Consolas,monospace;
  }
  html[data-theme="light"]{
    --bg:#fff;--surface:#fff;--border:#E4E4E7;--tx:#09090B;--tx2:#52525B;--tx3:#A1A1AA;
    --track:#E4E4E7;--fill:#09090B;--hover:rgba(0,0,0,.05);--line:#EDEDF0;
  }
  *{box-sizing:border-box;-webkit-user-select:none;user-select:none}
  html,body{margin:0;background:transparent;overflow:hidden}
  body{font-family:var(--mono);font-size:12px;color:var(--tx);-webkit-font-smoothing:antialiased}
  #menu{background:var(--surface);border:1px solid var(--border);border-radius:12px;
        padding:6px;width:300px;overflow:hidden;
        box-shadow:0 18px 50px -12px rgba(0,0,0,.7),0 0 0 .5px rgba(255,255,255,.03) inset}
  .item{display:flex;align-items:center;gap:10px;width:100%;border:0;background:transparent;
        color:var(--tx);font-family:var(--mono);font-size:12.5px;text-align:left;
        padding:9px 10px;border-radius:8px;cursor:pointer;transition:background .1s}
  .item:hover{background:var(--hover)}
  .item .ic{width:15px;height:15px;flex:0 0 15px;color:var(--tx2);stroke-width:1.6}
  .item.danger:hover{background:rgba(255,59,48,.12)}
  .item.danger:hover .ic,.item.danger:hover .lab{color:var(--red)}
  .item .lab{flex:1}
  .chk{width:15px;height:15px;color:var(--green);opacity:0;flex:0 0 15px}
  .chk.on{opacity:1}
  .sep{height:1px;background:var(--line);margin:6px 8px}
  .sect{font-size:9.5px;text-transform:uppercase;letter-spacing:.22em;color:var(--tx3);
        padding:8px 12px 5px;display:flex;align-items:center;justify-content:space-between;
        cursor:pointer;border-radius:6px;transition:background .1s}
  .sect:hover{background:var(--hover);color:var(--tx2)}
  .sect .car{font-size:9px;letter-spacing:0;transition:transform .15s}
  .grp.collapsed .car{transform:rotate(-90deg)}
  .grp.collapsed .gbody{display:none}
  .sub{font-size:9.5px;letter-spacing:.06em;color:var(--tx3);padding:6px 12px 4px 12px}
  .row{display:flex;align-items:center;gap:9px;padding:5px 12px}
  .row .ic{width:13px;height:13px;flex:0 0 13px;color:var(--tx3);stroke-width:1.5}
  .row .rl{width:86px;flex:0 0 86px;color:var(--tx2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .row .bar{flex:1;height:5px;background:var(--track);border-radius:3px;overflow:hidden}
  .row .bar > i{display:block;height:100%;background:var(--fill);border-radius:3px;transition:width .3s}
  .row .bar.warn > i{background:var(--yellow)} .row .bar.bad > i{background:var(--red)}
  .row .rv{width:62px;flex:0 0 62px;text-align:right;color:var(--tx);font-variant-numeric:tabular-nums}
</style>
</head>
<body>
<div id="menu">
  <button class="item" onclick="call('show_dashboard')">
    <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="4" width="18" height="13" rx="1.5"/><path d="M8 20h8M12 17v3"/></svg>
    <span class="lab">Show TokenScope</span>
  </button>
  <div class="sep"></div>
  <div class="grp" data-g="claude">
    <div class="sect" onclick="toggleGrp('claude')">Claude · usage limits<span class="car">▾</span></div>
    <div class="gbody" id="claude"></div>
  </div>
  <div class="sep"></div>
  <div class="grp" data-g="codex">
    <div class="sect" onclick="toggleGrp('codex')">Codex · usage limits<span class="car">▾</span></div>
    <div class="gbody">
      <div id="codex"></div>
      <div class="sub">GPT-5.3-Codex-Spark</div>
      <div id="spark"></div>
    </div>
  </div>
  <div class="sep"></div>
  <button class="item" onclick="toggleStartup()">
    <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 3v11m0 0l-4-4m4 4l4-4M5 21h14"/></svg>
    <span class="lab" id="startup-label">Start with Windows</span>
    <svg class="chk" id="chk" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M5 12l5 5L20 6"/></svg>
  </button>
  <button class="item danger" onclick="call('quit_app')">
    <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 4v8M7.5 7a7 7 0 1 0 9 0"/></svg>
    <span class="lab">Quit</span>
  </button>
</div>
<script>
const ICON_CLOCK='<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg>';
function call(name){ try{ window.pywebview.api[name](); }catch(e){} }
function esc(s){ return String(s).replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function _bar(label, pct, value, cls){
  const w = pct==null?0:Math.max(0,Math.min(100,pct));
  return `<div class="row">${ICON_CLOCK}<span class="rl">${esc(label)}</span>`+
         `<span class="bar ${cls}"><i style="width:${w}%"></i></span><span class="rv">${esc(value)}</span></div>`;
}
// Codex: bar = remaining, red when low (matches the dashboard's barRemain).
function row(label, leftPct){
  const cls = leftPct<=10?"bad":leftPct<=25?"warn":"";
  return _bar(label, leftPct, leftPct==null?"—":Math.round(leftPct)+"% left", cls);
}
// Claude: bar = used, fills 0->100 as consumed, red when high (matches the dashboard's bar).
function rowUsed(label, usedPct){
  const cls = usedPct>=90?"bad":usedPct>=75?"warn":"";
  return _bar(label, usedPct, usedPct==null?"—":Math.round(usedPct)+"% used", cls);
}
// Render whatever limit windows the API reports (labels change over time:
// Sonnet only -> Opus only -> Fable only, ...). "All" reads better as "Weekly (All)".
function claudeRows(u){
  const lims=((u.claude||{}).limits||[]).filter(l=>l.used_percent!=null);
  if(!lims.length) return rowUsed("5h",null)+rowUsed("Weekly (All)",null);
  return lims.map(l=>rowUsed(l.label==="All"?"Weekly (All)":l.label,l.used_percent)).join("");
}
function codexLeft(cx,key){
  const l = cx[key]; if(l && l.used_percent!=null) return 100-l.used_percent; return 100;
}
async function refreshTray(){
  let u={};
  try{ u = await (await fetch("/api/local/utilization",{cache:"no-store"})).json(); }catch(e){}
  const cx = u.codex||{};
  document.getElementById("claude").innerHTML = claudeRows(u);
  document.getElementById("codex").innerHTML =
    row("5h",codexLeft(cx,"primary"))+row("Weekly",codexLeft(cx,"secondary"));
  document.getElementById("spark").innerHTML =
    row("5h",codexLeft(cx,"spark_primary"))+row("Weekly",codexLeft(cx,"spark_secondary"));
  try{
    if(window.pywebview.api.startup_label){
      document.getElementById("startup-label").textContent = await window.pywebview.api.startup_label();
    }
    const on = await window.pywebview.api.startup_enabled();
    document.getElementById("chk").classList.toggle("on",!!on);
  }catch(e){}
  fitWindow();
}
function fitWindow(){
  const m=document.getElementById("menu").getBoundingClientRect();
  try{ window.pywebview.api.resize(Math.ceil(m.width)+2, Math.ceil(m.height)+2); }catch(e){}
}
// Collapsible sections keep the popup short; state persists across opens.
function setGrp(g,col){
  const el=document.querySelector(`.grp[data-g="${g}"]`); if(!el)return;
  el.classList.toggle("collapsed",col);
  localStorage.setItem("tokenscope.tray.collapse."+g,col?"1":"0");
}
function toggleGrp(g){
  const el=document.querySelector(`.grp[data-g="${g}"]`); if(!el)return;
  setGrp(g,!el.classList.contains("collapsed"));
  fitWindow();
}
["claude","codex"].forEach(g=>setGrp(g,localStorage.getItem("tokenscope.tray.collapse."+g)==="1"));
async function toggleStartup(){
  try{ const on=await window.pywebview.api.toggle_startup(); document.getElementById("chk").classList.toggle("on",!!on); }catch(e){}
}
async function applyTheme(){
  try{ const t=(await (await fetch("/api/theme",{cache:"no-store"})).json()).theme;
       document.documentElement.setAttribute("data-theme", t==="light"?"light":"dark"); }catch(e){}
}
window.addEventListener("pywebviewready", ()=>{ applyTheme(); refreshTray(); });
window.addEventListener("focus", ()=>{ applyTheme(); refreshTray(); });
window.addEventListener("blur", ()=>{ call("dismiss"); });
document.addEventListener("keydown", e=>{ if(e.key==="Escape") call("dismiss"); });
document.addEventListener("contextmenu", e=>e.preventDefault());  // no native WebView2 menu
// In case pywebviewready already fired before listeners attached:
if(window.pywebview && window.pywebview.api){ applyTheme(); refreshTray(); }
</script>
</body>
</html>
"""
