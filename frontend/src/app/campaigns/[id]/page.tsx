"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getCampaign,
  updateCampaignStatus,
  uploadPdf,
  uploadAsset,
  deleteAsset,
  addComment,
  getMe,
} from "@/lib/api";
import type { Campaign, CampaignStatus, User } from "@/types";
import StatusBadge from "@/components/StatusBadge";
import { formatDateTime, toDatetimeLocalBerlin, berlinToISO } from "@/lib/dates";

type AllowedTransition = {
  label: string;
  status: CampaignStatus;
  needsSendAt?: boolean;
  needsReason?: boolean;
};

const MARKETING_TRANSITIONS: Record<CampaignStatus, AllowedTransition[]> = {
  submitted: [
    { label: "In Prüfung nehmen", status: "in_review" },
    { label: "Änderungen anfragen", status: "changes_needed" },
    { label: "Planen", status: "scheduled", needsSendAt: true },
    { label: "Genehmigen", status: "approved", needsSendAt: true },
    { label: "Ablehnen", status: "rejected" },
  ],
  in_review: [
    { label: "Änderungen anfragen", status: "changes_needed" },
    { label: "Planen", status: "scheduled", needsSendAt: true },
    { label: "Genehmigen", status: "approved", needsSendAt: true },
    { label: "Ablehnen", status: "rejected" },
  ],
  changes_needed: [
    { label: "In Prüfung nehmen", status: "in_review" },
    { label: "Ablehnen", status: "rejected" },
  ],
  scheduled: [
    { label: "Genehmigen", status: "approved" },
    { label: "Ablehnen", status: "rejected" },
    { label: "Als versendet markieren", status: "sent" },
  ],
  approved: [
    { label: "Zurück auf geplant", status: "scheduled", needsReason: true },
    { label: "Ablehnen", status: "rejected" },
    { label: "Als versendet markieren", status: "sent" },
  ],
  rejected: [],
  sent: [],
};

const REQUESTER_TRANSITIONS: Record<CampaignStatus, AllowedTransition[]> = {
  submitted: [],
  in_review: [],
  changes_needed: [{ label: "Erneut einreichen", status: "submitted" }],
  scheduled: [],
  approved: [],
  rejected: [],
  sent: [],
};

function AuthedImage({ src, alt, className }: { src: string; alt: string; className?: string }) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  useEffect(() => {
    const user = typeof window !== "undefined"
      ? (localStorage.getItem("x-user") || "requester@bvmw.example")
      : "";
    let url: string | null = null;
    fetch(src, { headers: { "X-User": user } })
      .then((r) => r.blob())
      .then((blob) => { url = URL.createObjectURL(blob); setBlobUrl(url); })
      .catch(() => {});
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [src]);

  if (!blobUrl) return <div className={className} />;
  return <img src={blobUrl} alt={alt} className={className} />;
}


function fmt(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [me, setMe] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Transition modal state
  const [pendingTransition, setPendingTransition] = useState<AllowedTransition | null>(null);
  const [sendAt, setSendAt] = useState("");
  const [reason, setReason] = useState("");
  const [transitioning, setTransitioning] = useState(false);

  // Inline send_at editor
  const [editSendAt, setEditSendAt] = useState("");
  const [savingSendAt, setSavingSendAt] = useState(false);

  // Comment
  const [commentText, setCommentText] = useState("");
  const [commenting, setCommenting] = useState(false);

  // File uploads
  const pdfRef = useRef<HTMLInputElement>(null);
  const assetRef = useRef<HTMLInputElement>(null);

  async function load() {
    try {
      const [c, u] = await Promise.all([getCampaign(parseInt(id)), getMe()]);
      setCampaign(c);
      setMe(u);
      if (c.send_at) {
        const berlin = toDatetimeLocalBerlin(c.send_at);
        setSendAt(berlin);
        setEditSendAt(berlin);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [id]);

  async function applyTransition() {
    if (!pendingTransition || !campaign) return;
    setTransitioning(true);
    try {
      await updateCampaignStatus(campaign.id, {
        status: pendingTransition.status,
        send_at: pendingTransition.needsSendAt && sendAt ? berlinToISO(sendAt) : undefined,
        reason: pendingTransition.needsReason && reason ? reason : undefined,
      });
      setPendingTransition(null);
      setReason("");
      setError(null);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler");
    } finally {
      setTransitioning(false);
    }
  }

  async function handleSaveSendAt() {
    if (!campaign || !editSendAt) return;
    setSavingSendAt(true);
    try {
      await updateCampaignStatus(campaign.id, { send_at: berlinToISO(editSendAt) });
      setError(null);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler beim Speichern des Termins");
    } finally {
      setSavingSendAt(false);
    }
  }

  async function handleComment() {
    if (!commentText.trim() || !campaign) return;
    setCommenting(true);
    try {
      await addComment(campaign.id, commentText.trim());
      setCommentText("");
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler");
    } finally {
      setCommenting(false);
    }
  }

  async function handlePdfUpload(file: File) {
    if (!campaign) return;
    try {
      await uploadPdf(campaign.id, file);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler beim PDF-Upload");
    }
  }

  async function handleAssetUpload(file: File) {
    if (!campaign) return;
    try {
      await uploadAsset(campaign.id, file);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler beim Asset-Upload");
    }
  }

  async function handleDeleteAsset(assetId: number) {
    if (!campaign) return;
    if (!confirm("Asset wirklich löschen?")) return;
    try {
      await deleteAsset(campaign.id, assetId);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler beim Löschen");
    }
  }

  if (loading) return <p className="text-gray-400 text-sm">Lade…</p>;
  if (!campaign || !me) return <p className="text-red-500">Kampagne nicht gefunden.</p>;

  const isMarketing = me.role === "marketing";
  const isOwner = me.id === campaign.creator.id;
  const transitions = isMarketing
    ? MARKETING_TRANSITIONS[campaign.status]
    : REQUESTER_TRANSITIONS[campaign.status];

  const marketingEditable: CampaignStatus[] = ["submitted", "in_review", "changes_needed", "scheduled", "approved"];
  const requesterEditable: CampaignStatus[] = ["submitted", "in_review", "changes_needed", "scheduled"];
  const canEdit = isMarketing
    ? marketingEditable.includes(campaign.status)
    : requesterEditable.includes(campaign.status);
  const canUploadPdf = canEdit && (isMarketing || isOwner);
  const canUploadAsset = canEdit && (isMarketing || isOwner);
  const canDeleteAsset = canEdit && (isMarketing || isOwner);

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <button onClick={() => router.back()} className="text-sm text-gray-400 hover:text-gray-600 mb-2">
            ← Zurück
          </button>
          <h1 className="text-xl font-semibold">{campaign.title}</h1>
          <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
            <span>{campaign.department.name}</span>
            <span>·</span>
            <span>Termin: {formatDateTime(campaign.send_at)}</span>
            <span>·</span>
            <StatusBadge status={campaign.status} />
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex justify-between">
          {error}
          <button onClick={() => setError(null)} className="font-bold ml-2">×</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Status actions */}
          {transitions.length > 0 && (
            <section className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
              <h2 className="font-medium mb-3 text-sm text-gray-700">Statuswechsel</h2>
              <div className="flex flex-wrap gap-2">
                {transitions.map((t) => (
                  <button
                    key={t.status}
                    onClick={() => setPendingTransition(t)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium border ${
                      t.status === "rejected"
                        ? "border-red-200 text-red-700 hover:bg-red-50"
                        : t.status === "sent"
                        ? "border-emerald-200 text-emerald-700 hover:bg-emerald-50"
                        : "border-blue-200 text-blue-700 hover:bg-blue-50"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </section>
          )}

          {/* PDF Versions */}
          <section className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-medium text-sm text-gray-700">PDF-Versionen</h2>
              {canUploadPdf && (
                <button
                  onClick={() => pdfRef.current?.click()}
                  className="text-xs px-3 py-1.5 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100"
                >
                  + Neue Version
                </button>
              )}
            </div>
            <input
              ref={pdfRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handlePdfUpload(f);
                e.target.value = "";
              }}
            />
            {campaign.files.length === 0 ? (
              <p className="text-sm text-gray-400">Keine PDFs vorhanden.</p>
            ) : (
              <ul className="space-y-2">
                {[...campaign.files].reverse().map((f) => (
                  <li key={f.id} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-gray-400 text-xs bg-gray-100 px-2 py-0.5 rounded">v{f.version}</span>
                      <span className="text-gray-700">{f.original_filename}</span>
                      <span className="text-gray-400 text-xs">{fmt(f.file_size)}</span>
                    </div>
                    <div className="flex items-center gap-2 text-gray-400 text-xs">
                      <span>{formatDateTime(f.uploaded_at)}</span>
                      <a
                        href={`/api/campaigns/${campaign.id}/files/${f.id}/download`}
                        className="text-blue-500 hover:underline"
                        target="_blank"
                      >
                        Download
                      </a>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Assets */}
          <section className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-medium text-sm text-gray-700">Assets / Bilder</h2>
              {canUploadAsset && (
                <button
                  onClick={() => assetRef.current?.click()}
                  className="text-xs px-3 py-1.5 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100"
                >
                  + Bild hinzufügen
                </button>
              )}
            </div>
            <input
              ref={assetRef}
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleAssetUpload(f);
                e.target.value = "";
              }}
            />
            {campaign.assets.filter((a) => !a.is_deleted).length === 0 ? (
              <p className="text-sm text-gray-400">Keine Assets vorhanden.</p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {campaign.assets
                  .filter((a) => !a.is_deleted)
                  .map((a) => (
                    <div key={a.id} className="border rounded-lg overflow-hidden group relative">
                      <div className="aspect-video bg-gray-100 flex items-center justify-center">
                        <AuthedImage
                          src={`/api/campaigns/assets/${a.id}/download`}
                          alt={a.original_filename}
                          className="object-cover w-full h-full"
                        />
                      </div>
                      <div className="p-2">
                        <p className="text-xs text-gray-600 truncate">{a.original_filename}</p>
                        <p className="text-xs text-gray-400">{fmt(a.file_size)}</p>
                      </div>
                      {canDeleteAsset && (
                        <button
                          onClick={() => handleDeleteAsset(a.id)}
                          className="absolute top-1 right-1 w-5 h-5 bg-red-500 text-white rounded-full text-xs hidden group-hover:flex items-center justify-center"
                        >
                          ×
                        </button>
                      )}
                    </div>
                  ))}
              </div>
            )}
          </section>

          {/* Comments */}
          <section className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <h2 className="font-medium text-sm text-gray-700 mb-3">Kommentare</h2>
            <div className="space-y-3 mb-4 max-h-64 overflow-y-auto">
              {campaign.comments.length === 0 ? (
                <p className="text-sm text-gray-400">Noch keine Kommentare.</p>
              ) : (
                campaign.comments.map((c) => (
                  <div key={c.id} className="flex gap-3">
                    <div className="w-7 h-7 rounded-full bg-blue-100 flex-shrink-0 flex items-center justify-center text-xs font-medium text-blue-700">
                      {c.author.name[0]}
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 mb-0.5">
                        <span className="font-medium text-gray-700">{c.author.name}</span>
                        {" · "}
                        {formatDateTime(c.created_at)}
                      </div>
                      <p className="text-sm text-gray-800 whitespace-pre-wrap">{c.text}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
            <div className="flex gap-2">
              <textarea
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                placeholder="Kommentar schreiben…"
                rows={2}
                className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
              <button
                onClick={handleComment}
                disabled={commenting || !commentText.trim()}
                className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm disabled:opacity-50"
              >
                Senden
              </button>
            </div>
          </section>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* Info card */}
          <section className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <h2 className="font-medium text-sm text-gray-700 mb-3">Details</h2>
            <dl className="space-y-2 text-sm">
              <div><dt className="text-gray-400 text-xs">Erstellt von</dt><dd>{campaign.creator.name}</dd></div>
              <div><dt className="text-gray-400 text-xs">Abteilung</dt><dd>{campaign.department.name}</dd></div>
              <div><dt className="text-gray-400 text-xs">Erstellt am</dt><dd>{formatDateTime(campaign.created_at)}</dd></div>
              <div><dt className="text-gray-400 text-xs">Zuletzt geändert</dt><dd>{formatDateTime(campaign.updated_at)}</dd></div>
              <div>
                <dt className="text-gray-400 text-xs">Versandtermin</dt>
                {canEdit ? (
                  <dd className="mt-1 space-y-1">
                    <input
                      type="datetime-local"
                      value={editSendAt}
                      onChange={(e) => setEditSendAt(e.target.value)}
                      className="w-full border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={handleSaveSendAt}
                      disabled={savingSendAt || editSendAt === sendAt}
                      className="w-full px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-40"
                    >
                      {savingSendAt ? "Speichert…" : "Termin speichern"}
                    </button>
                  </dd>
                ) : (
                  <dd className="font-medium">{formatDateTime(campaign.send_at)}</dd>
                )}
              </div>
              <div><dt className="text-gray-400 text-xs">Kanal</dt><dd>{campaign.channel}</dd></div>
            </dl>
          </section>

          {/* Move log */}
          {campaign.move_logs.length > 0 && (
            <section className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
              <h2 className="font-medium text-sm text-gray-700 mb-3">Änderungsprotokoll</h2>
              <ul className="space-y-2">
                {campaign.move_logs.map((l) => (
                  <li key={l.id} className="text-xs text-gray-600">
                    <div className="font-medium">{l.moved_by.name}</div>
                    <div>
                      {l.old_send_at ? formatDateTime(l.old_send_at) : "–"} → {l.new_send_at ? formatDateTime(l.new_send_at) : "–"}
                    </div>
                    {l.reason && <div className="text-gray-400 italic">{l.reason}</div>}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </div>

      {/* Transition modal */}
      {pendingTransition && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h3 className="font-semibold mb-4">{pendingTransition.label}</h3>

            {pendingTransition.needsSendAt && (
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Versandtermin *</label>
                <input
                  type="datetime-local"
                  value={sendAt}
                  onChange={(e) => setSendAt(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
            )}

            {pendingTransition.needsReason && (
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Begründung *</label>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  rows={3}
                  placeholder="Warum wird der Status geändert?"
                  className="w-full border rounded-lg px-3 py-2 text-sm resize-none"
                />
              </div>
            )}

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => { setPendingTransition(null); setReason(""); }}
                className="px-4 py-2 text-sm bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                Abbrechen
              </button>
              <button
                onClick={applyTransition}
                disabled={
                  transitioning ||
                  (pendingTransition.needsReason && !reason.trim()) ||
                  (pendingTransition.needsSendAt && !sendAt)
                }
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {transitioning ? "Wird gespeichert…" : "Bestätigen"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
