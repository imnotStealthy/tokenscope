import { useRef, useState } from "react";
import { Upload, FileJson, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { uploadFile, seedDemo } from "@/lib/tokenApi";
import { useLang } from "@/lib/i18n";

export default function UploadDropzone({ onImported }) {
  const { t } = useLang();
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [seedBusy, setSeedBusy] = useState(false);

  const handleFiles = async (files) => {
    if (!files || files.length === 0) return;
    setBusy(true);
    try {
      for (const f of files) {
        const res = await uploadFile(f);
        toast.success(
          t("upload.imported", { filename: f.name }),
          { description: t("upload.imported_desc", { inserted: res.inserted, skipped: res.skipped }) }
        );
      }
      onImported?.();
    } catch (e) {
      toast.error(t("upload.import_failed"), {
        description: e?.response?.data?.detail || e.message,
      });
    } finally {
      setBusy(false);
    }
  };

  const handleSeed = async () => {
    setSeedBusy(true);
    try {
      const res = await seedDemo();
      toast.success(t("upload.demo_loaded"), {
        description: t("upload.demo_loaded_desc", { n: res.inserted }),
      });
      onImported?.();
    } catch (e) {
      toast.error(t("upload.seed_failed"), { description: e.message });
    } finally {
      setSeedBusy(false);
    }
  };

  return (
    <div
      data-testid="upload-section"
      className="border border-zinc-800 bg-[#0A0A0A]"
    >
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between flex-wrap gap-2">
        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
          // import_data
        </div>
        <div className="flex items-center gap-2">
          <button
            data-testid="seed-demo-btn"
            onClick={handleSeed}
            disabled={seedBusy}
            className="font-mono text-[10px] uppercase tracking-[0.2em] px-3 py-1.5 border border-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-900 disabled:opacity-50"
          >
            {seedBusy ? t("upload.loading") : t("upload.load_demo")}
          </button>
        </div>
      </div>

      <div
        data-testid="upload-dropzone"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={`cursor-pointer p-8 border-2 border-dashed m-3 transition-colors duration-100 ${
          drag ? "border-white bg-zinc-900" : "border-zinc-800 hover:border-zinc-600"
        }`}
      >
        <input
          ref={inputRef}
          data-testid="upload-input"
          type="file"
          accept=".csv,.json,application/json,text/csv"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div className="flex items-center justify-between gap-6 flex-wrap">
          <div className="flex items-center gap-4">
            {busy ? (
              <Loader2 className="h-6 w-6 animate-spin" strokeWidth={1.5} />
            ) : (
              <Upload className="h-6 w-6" strokeWidth={1.5} />
            )}
            <div>
              <div className="font-mono text-sm tracking-tight">
                {busy ? t("upload.parsing") : t("upload.drop_here")}
              </div>
              <div className="font-mono text-[11px] text-zinc-500 mt-1">
                {t("upload.expected_fields")} tool, model, input_tokens, output_tokens, timestamp [, underlying_model, cost_usd]
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
            <div className="flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5" strokeWidth={1.5} /> .csv
            </div>
            <div className="flex items-center gap-1.5">
              <FileJson className="h-3.5 w-3.5" strokeWidth={1.5} /> .json
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
