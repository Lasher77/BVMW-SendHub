"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getDepartments, getNextAvailable, createCampaign } from "@/lib/api";
import type { Department } from "@/types";
import { toDatetimeLocalBerlin, berlinToISO } from "@/lib/dates";

export default function NewRequestPage() {
  const router = useRouter();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [requesterName, setRequesterName] = useState("");
  const [requesterEmail, setRequesterEmail] = useState("");
  const [title, setTitle] = useState("");
  const [deptId, setDeptId] = useState<number | "">("");
  const [sendAt, setSendAt] = useState("");
  const [pdf, setPdf] = useState<File | null>(null);
  const [assets, setAssets] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const pdfRef = useRef<HTMLInputElement>(null);
  const assetRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getDepartments()
      .then((d) => setDepartments(d.filter((x) => x.is_active)))
      .catch(() => {});
    fetchNextAvailable();
  }, []);

  async function fetchNextAvailable() {
    try {
      const res = await getNextAvailable("email");
      setSendAt(toDatetimeLocalBerlin(res.next_available));
    } catch {}
  }

  function addAssets(files: FileList | null) {
    if (!files) return;
    const allowed = ["image/png", "image/jpeg", "image/webp", "image/gif"];
    const valid: File[] = [];
    for (const f of Array.from(files)) {
      if (!allowed.includes(f.type)) {
        setError(`Nicht erlaubter Dateityp: ${f.type}. Erlaubt: PNG, JPEG, WebP, GIF`);
        return;
      }
      if (f.size > 10 * 1024 * 1024) {
        setError(`Datei '${f.name}' ist größer als 10 MB.`);
        return;
      }
      valid.push(f);
    }
    setAssets((prev) => [...prev, ...valid]);
  }

  function removeAsset(i: number) {
    setAssets((prev) => prev.filter((_, idx) => idx !== i));
  }

  function validateBvmwEmail(email: string): boolean {
    return /^[^@\s]+@bvmw\.de$/i.test(email);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!requesterName.trim()) { setError("Bitte Ihren Namen angeben."); return; }
    if (!requesterEmail.trim()) { setError("Bitte Ihre E-Mail angeben."); return; }
    if (!validateBvmwEmail(requesterEmail.trim())) {
      setError("Nur @bvmw.de E-Mail-Adressen sind erlaubt.");
      return;
    }
    if (!title.trim()) { setError("Bitte Titel angeben."); return; }
    if (!deptId) { setError("Bitte Abteilung auswählen."); return; }
    if (!pdf) { setError("Bitte PDF hochladen (Pflichtfeld)."); return; }
    if (pdf.size > 20 * 1024 * 1024) { setError("PDF darf maximal 20 MB groß sein."); return; }
    if (pdf.type !== "application/pdf" && !pdf.name.toLowerCase().endsWith(".pdf")) {
      setError("Nur PDF-Dateien erlaubt.");
      return;
    }

    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("requester_name", requesterName.trim());
      fd.append("requester_email", requesterEmail.trim());
      fd.append("title", title.trim());
      fd.append("department_id", String(deptId));
      if (sendAt) fd.append("send_at", berlinToISO(sendAt));
      fd.append("pdf", pdf);
      for (const a of assets) fd.append("assets", a);

      await createCampaign(fd);
      setSubmitted(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler beim Erstellen");
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-xl shadow-sm border border-green-100 p-8 text-center">
          <div className="text-green-600 text-4xl mb-4">&#10003;</div>
          <h1 className="text-xl font-semibold mb-2">Anfrage eingereicht!</h1>
          <p className="text-sm text-gray-600 mb-6">
            Ihre Email-Anfrage wurde erfolgreich eingereicht und wird vom
            Marketing-Team bearbeitet. Sie erhalten eine Benachrichtigung an{" "}
            <strong>{requesterEmail}</strong>.
          </p>
          <button
            onClick={() => {
              setSubmitted(false);
              setTitle("");
              setPdf(null);
              setAssets([]);
              setDeptId("");
              fetchNextAvailable();
            }}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
          >
            Weitere Anfrage einreichen
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-xl font-semibold mb-6">Neue Email-Anfrage</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        {/* Requester info */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Ihr Name *</label>
            <input
              type="text"
              value={requesterName}
              onChange={(e) => setRequesterName(e.target.value)}
              placeholder="Max Mustermann"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Ihre E-Mail (@bvmw.de) *</label>
            <input
              type="email"
              value={requesterEmail}
              onChange={(e) => setRequesterEmail(e.target.value)}
              placeholder="name@bvmw.de"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Title */}
        <div>
          <label className="block text-sm font-medium mb-1">Titel *</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="z.B. Newsletter April 2025"
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Department */}
        <div>
          <label className="block text-sm font-medium mb-1">Abteilung *</label>
          <select
            value={deptId}
            onChange={(e) => setDeptId(e.target.value ? parseInt(e.target.value) : "")}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Bitte wählen...</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>

        {/* Send date */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Geplanter Versandtermin
          </label>
          <div className="flex gap-2">
            <input
              type="datetime-local"
              value={sendAt}
              onChange={(e) => setSendAt(e.target.value)}
              className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="button"
              onClick={fetchNextAvailable}
              className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg border text-gray-600"
              title="Nächstmöglicher Termin"
            >
              Nächster frei
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-1">Standard: nächstmöglicher regelkonformer Termin</p>
        </div>

        {/* PDF */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Email-Text als PDF *
          </label>
          <div
            className="border-2 border-dashed rounded-lg p-4 text-center cursor-pointer hover:bg-gray-50"
            onClick={() => pdfRef.current?.click()}
          >
            {pdf ? (
              <div className="flex items-center justify-center gap-2 text-sm">
                <span className="text-blue-600">{pdf.name}</span>
                <span className="text-gray-400">({(pdf.size / 1024).toFixed(0)} KB)</span>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setPdf(null); }}
                  className="text-red-400 hover:text-red-600 font-bold"
                >
                  x
                </button>
              </div>
            ) : (
              <p className="text-sm text-gray-500">PDF hierher ziehen oder klicken (max. 20 MB)</p>
            )}
          </div>
          <input
            ref={pdfRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) setPdf(f);
              e.target.value = "";
            }}
          />
        </div>

        {/* Assets */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Bilder / Assets (optional, einzeln)
          </label>
          <div
            className="border-2 border-dashed rounded-lg p-4 text-center cursor-pointer hover:bg-gray-50"
            onClick={() => assetRef.current?.click()}
          >
            <p className="text-sm text-gray-500">Bild hinzufügen (PNG, JPEG, WebP, GIF - max. 10 MB)</p>
          </div>
          <input
            ref={assetRef}
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            multiple
            className="hidden"
            onChange={(e) => { addAssets(e.target.files); e.target.value = ""; }}
          />
          {assets.length > 0 && (
            <ul className="mt-2 space-y-1">
              {assets.map((a, i) => (
                <li key={i} className="flex items-center gap-2 text-sm text-gray-700">
                  <span>{a.name}</span>
                  <span className="text-gray-400">({(a.size / 1024).toFixed(0)} KB)</span>
                  <button
                    type="button"
                    onClick={() => removeAsset(i)}
                    className="text-red-400 hover:text-red-600 font-bold"
                  >
                    x
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
          >
            {loading ? "Wird eingereicht..." : "Anfrage einreichen"}
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
          >
            Abbrechen
          </button>
        </div>
      </form>
    </div>
  );
}
