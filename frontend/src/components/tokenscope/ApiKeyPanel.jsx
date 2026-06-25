import { useEffect, useState } from "react";
import { Key, Check, AlertTriangle, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { fetchAuthStatus, getApiKey, setApiKey } from "@/lib/tokenApi";

/**
 * Compact API key panel.
 * - If backend has TOKENSCOPE_API_KEY set, writes require X-API-Key.
 * - User stores key in localStorage; interceptor injects it on every request.
 */
export default function ApiKeyPanel() {
  const [status, setStatus] = useState({ required: false, valid: true });
  const [keyInput, setKeyInput] = useState(getApiKey());
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    try {
      const r = await fetchAuthStatus();
      setStatus(r);
    } catch (e) {
      // ignore
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const save = async () => {
    setBusy(true);
    setApiKey(keyInput.trim());
    await refresh();
    setBusy(false);
    toast.success("API KEY SAVED");
  };

  const clear = async () => {
    setApiKey("");
    setKeyInput("");
    await refresh();
    toast.success("API KEY CLEARED");
  };

  // When backend doesn't require a key, render a tiny "OPEN" tag.
  if (!status.required) {
    return (
      <div
        data-testid="api-key-panel-open"
        className="border border-zinc-800 bg-[#0A0A0A] px-3 py-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500"
      >
        <Key className="h-3 w-3" strokeWidth={1.5} />
        api: open · no key required
      </div>
    );
  }

  const ok = status.valid;
  return (
    <div
      data-testid="api-key-panel"
      className={`border bg-[#0A0A0A] ${ok ? "border-zinc-800" : "border-[#FFCC00]"}`}
    >
      <div className="px-3 py-2 border-b border-zinc-800 flex items-center justify-between">
        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500 flex items-center gap-2">
          <Key className="h-3 w-3" strokeWidth={1.5} />
          api_key
        </div>
        {ok ? (
          <div
            data-testid="api-key-status-ok"
            className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-400 flex items-center gap-1"
          >
            <Check className="h-3 w-3" strokeWidth={2} /> authenticated
          </div>
        ) : (
          <div
            data-testid="api-key-status-missing"
            className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#FFCC00] flex items-center gap-1"
          >
            <AlertTriangle className="h-3 w-3" strokeWidth={2} /> key required
          </div>
        )}
      </div>
      <div className="p-3 flex items-center gap-2">
        <div className="relative flex-1">
          <input
            data-testid="api-key-input"
            type={show ? "text" : "password"}
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder="paste X-API-Key…"
            className="w-full bg-black border border-zinc-800 px-2.5 py-2 pr-8 font-mono text-xs text-white focus:outline-none focus:border-white"
          />
          <button
            type="button"
            data-testid="api-key-toggle-visibility"
            onClick={() => setShow((s) => !s)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white"
            aria-label="toggle visibility"
          >
            {show ? <EyeOff className="h-3.5 w-3.5" strokeWidth={1.5} /> : <Eye className="h-3.5 w-3.5" strokeWidth={1.5} />}
          </button>
        </div>
        <button
          data-testid="api-key-save-btn"
          onClick={save}
          disabled={busy || !keyInput.trim()}
          className="font-mono text-[10px] uppercase tracking-[0.2em] px-3 py-2 bg-white text-black hover:bg-zinc-200 disabled:opacity-40"
        >
          save
        </button>
        <button
          data-testid="api-key-clear-btn"
          onClick={clear}
          className="font-mono text-[10px] uppercase tracking-[0.2em] px-3 py-2 border border-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-900"
        >
          clear
        </button>
      </div>
    </div>
  );
}
