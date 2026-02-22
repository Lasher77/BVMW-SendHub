"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getCampaigns } from "@/lib/api";
import type { CampaignListItem } from "@/types";
import StatusBadge from "@/components/StatusBadge";

function formatDate(s: string | null) {
  if (!s) return "–";
  return new Date(s).toLocaleDateString("de-DE", {
    day: "2-digit", month: "2-digit", year: "numeric",
  });
}

export default function RequestsPage() {
  const [campaigns, setCampaigns] = useState<CampaignListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCampaigns()
      .then(setCampaigns)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold">Meine Anfragen</h1>
        <Link
          href="/requests/new"
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          + Neue Anfrage
        </Link>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">{error}</div>
      )}

      {loading ? (
        <p className="text-gray-400 text-sm">Lade…</p>
      ) : campaigns.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="mb-4">Noch keine Anfragen vorhanden.</p>
          <Link href="/requests/new" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">
            Erste Anfrage erstellen
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-500">Titel</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">Abteilung</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">Termin</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">Status</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">Erstellt</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((c) => (
                <tr key={c.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link href={`/campaigns/${c.id}`} className="font-medium text-blue-600 hover:underline">
                      {c.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{c.department.name}</td>
                  <td className="px-4 py-3 text-gray-600">{formatDate(c.send_at)}</td>
                  <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                  <td className="px-4 py-3 text-gray-400">{formatDate(c.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
