"use client";
import { useEffect, useState } from "react";
import {
  getSettings,
  updateSettings,
  getDepartments,
  createDepartment,
  updateDepartment,
} from "@/lib/api";
import type { AppSettings, Department } from "@/types";

type Tab = "rules" | "departments";

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>("rules");

  // Rules tab
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [minGap, setMinGap] = useState(2);
  const [settingsSaved, setSettingsSaved] = useState(false);
  const [settingsError, setSettingsError] = useState<string | null>(null);

  // Departments tab
  const [departments, setDepartments] = useState<Department[]>([]);
  const [newDeptName, setNewDeptName] = useState("");
  const [deptError, setDeptError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");

  useEffect(() => {
    getSettings().then((s) => { setSettings(s); setMinGap(s.min_gap_days); }).catch(() => {});
    getDepartments().then(setDepartments).catch(() => {});
  }, []);

  async function saveSettings() {
    setSettingsError(null);
    try {
      const s = await updateSettings({ min_gap_days: minGap });
      setSettings(s);
      setSettingsSaved(true);
      setTimeout(() => setSettingsSaved(false), 2000);
    } catch (e: unknown) {
      setSettingsError(e instanceof Error ? e.message : "Fehler");
    }
  }

  async function createDept() {
    if (!newDeptName.trim()) return;
    setDeptError(null);
    try {
      const d = await createDepartment({ name: newDeptName.trim(), is_active: true });
      setDepartments((prev) => [...prev, d]);
      setNewDeptName("");
    } catch (e: unknown) {
      setDeptError(e instanceof Error ? e.message : "Fehler");
    }
  }

  async function toggleDept(dept: Department) {
    setDeptError(null);
    try {
      const updated = await updateDepartment(dept.id, { is_active: !dept.is_active });
      setDepartments((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
    } catch (e: unknown) {
      setDeptError(e instanceof Error ? e.message : "Fehler");
    }
  }

  async function saveDeptName(id: number) {
    if (!editingName.trim()) return;
    setDeptError(null);
    try {
      const updated = await updateDepartment(id, { name: editingName.trim() });
      setDepartments((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
      setEditingId(null);
    } catch (e: unknown) {
      setDeptError(e instanceof Error ? e.message : "Fehler");
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-xl font-semibold mb-6">Einstellungen</h1>

      {/* Tabs */}
      <div className="flex border-b mb-6">
        {(["rules", "departments"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              tab === t
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "rules" ? "Regeln" : "Abteilungen"}
          </button>
        ))}
      </div>

      {/* Rules tab */}
      {tab === "rules" && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">
              Mindestabstand zwischen Email-Aussendungen (Tage)
            </label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min={1}
                max={365}
                value={minGap}
                onChange={(e) => setMinGap(parseInt(e.target.value) || 1)}
                className="w-24 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={saveSettings}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
              >
                Speichern
              </button>
              {settingsSaved && <span className="text-green-600 text-sm">Gespeichert ✓</span>}
            </div>
            {settingsError && (
              <p className="mt-2 text-sm text-red-600">{settingsError}</p>
            )}
          </div>
          <div className="bg-blue-50 rounded-lg p-3 text-sm text-blue-700">
            <strong>Regelung:</strong> Zwischen zwei Email-Aussendungen müssen mindestens{" "}
            <strong>{minGap} {minGap === 1 ? "Tag" : "Tage"}</strong> liegen (Kalendertage).
            <br />
            Bei Mindestabstand {minGap}: Montag → {minGap === 1 ? "Dienstag" : minGap === 2 ? "Mittwoch" : `+${minGap} Tage`} OK.
          </div>
        </div>
      )}

      {/* Departments tab */}
      {tab === "departments" && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
            <h2 className="text-sm font-medium mb-3">Neue Abteilung</h2>
            <div className="flex gap-2">
              <input
                type="text"
                value={newDeptName}
                onChange={(e) => setNewDeptName(e.target.value)}
                placeholder="Abteilungsname"
                onKeyDown={(e) => e.key === "Enter" && createDept()}
                className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={createDept}
                disabled={!newDeptName.trim()}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                Hinzufügen
              </button>
            </div>
            {deptError && <p className="mt-2 text-sm text-red-600">{deptError}</p>}
          </div>

          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Name</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Status</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">Aktionen</th>
                </tr>
              </thead>
              <tbody>
                {departments.map((d) => (
                  <tr key={d.id} className="border-b last:border-0">
                    <td className="px-4 py-3">
                      {editingId === d.id ? (
                        <input
                          type="text"
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") saveDeptName(d.id);
                            if (e.key === "Escape") setEditingId(null);
                          }}
                          className="border rounded px-2 py-1 text-sm w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
                          autoFocus
                        />
                      ) : (
                        <span className={d.is_active ? "" : "text-gray-400 line-through"}>
                          {d.name}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          d.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                        }`}
                      >
                        {d.is_active ? "Aktiv" : "Inaktiv"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      {editingId === d.id ? (
                        <>
                          <button
                            onClick={() => saveDeptName(d.id)}
                            className="text-xs text-blue-600 hover:underline"
                          >
                            Speichern
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="text-xs text-gray-400 hover:underline"
                          >
                            Abbrechen
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={() => { setEditingId(d.id); setEditingName(d.name); }}
                            className="text-xs text-blue-600 hover:underline"
                          >
                            Umbenennen
                          </button>
                          <button
                            onClick={() => toggleDept(d)}
                            className={`text-xs hover:underline ${
                              d.is_active ? "text-amber-600" : "text-green-600"
                            }`}
                          >
                            {d.is_active ? "Deaktivieren" : "Aktivieren"}
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
