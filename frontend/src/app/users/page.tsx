"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getUsers,
  createUser,
  updateUser,
  deleteUser,
  getStoredUser,
  isAuthenticated,
} from "@/lib/api";
import type { User } from "@/types";

export default function UsersPage() {
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New-user form
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [formLoading, setFormLoading] = useState(false);

  // Edit form
  const [editUser, setEditUser] = useState<User | null>(null);
  const [editName, setEditName] = useState("");
  const [editPassword, setEditPassword] = useState("");

  useEffect(() => {
    const stored = getStoredUser();
    if (!isAuthenticated() || !stored?.is_admin) {
      router.replace("/login");
      return;
    }
    loadUsers();
  }, [router]);

  async function loadUsers() {
    try {
      const data = await getUsers();
      setUsers(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Fehler beim Laden.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);

    if (!newName.trim() || !newEmail.trim() || !newPassword) {
      setFormError("Alle Felder sind Pflichtfelder.");
      return;
    }
    if (newPassword.length < 8) {
      setFormError("Passwort muss mindestens 8 Zeichen lang sein.");
      return;
    }

    setFormLoading(true);
    try {
      await createUser({
        name: newName.trim(),
        email: newEmail.trim(),
        password: newPassword,
      });
      setNewName("");
      setNewEmail("");
      setNewPassword("");
      setShowForm(false);
      await loadUsers();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Fehler beim Anlegen.");
    } finally {
      setFormLoading(false);
    }
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault();
    if (!editUser) return;
    setFormError(null);

    const data: { name?: string; password?: string } = {};
    if (editName.trim() && editName.trim() !== editUser.name) {
      data.name = editName.trim();
    }
    if (editPassword) {
      if (editPassword.length < 8) {
        setFormError("Passwort muss mindestens 8 Zeichen lang sein.");
        return;
      }
      data.password = editPassword;
    }

    if (Object.keys(data).length === 0) {
      setEditUser(null);
      return;
    }

    setFormLoading(true);
    try {
      await updateUser(editUser.id, data);
      setEditUser(null);
      setEditPassword("");
      await loadUsers();
    } catch (err: unknown) {
      setFormError(
        err instanceof Error ? err.message : "Fehler beim Aktualisieren."
      );
    } finally {
      setFormLoading(false);
    }
  }

  async function handleToggleActive(user: User) {
    try {
      if (user.is_active) {
        await deleteUser(user.id);
      } else {
        await updateUser(user.id, { is_active: true });
      }
      await loadUsers();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Fehler.");
    }
  }

  function startEdit(user: User) {
    setEditUser(user);
    setEditName(user.name);
    setEditPassword("");
    setFormError(null);
  }

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto">
        <p className="text-gray-500">Lade Benutzer...</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Benutzerverwaltung</h1>
        <button
          onClick={() => {
            setShowForm(!showForm);
            setFormError(null);
          }}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
        >
          {showForm ? "Abbrechen" : "Neuer Moderator"}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* New user form */}
      {showForm && (
        <div className="mb-6 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-sm font-semibold mb-4">Neuen Moderator anlegen</h2>
          {formError && (
            <div className="mb-3 p-2 bg-red-50 border border-red-200 text-red-700 rounded text-sm">
              {formError}
            </div>
          )}
          <form onSubmit={handleCreate} className="space-y-3">
            <input
              type="text"
              placeholder="Name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="email"
              placeholder="E-Mail"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="password"
              placeholder="Passwort (min. 8 Zeichen)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={formLoading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
            >
              {formLoading ? "Wird angelegt..." : "Anlegen"}
            </button>
          </form>
        </div>
      )}

      {/* Edit form */}
      {editUser && (
        <div className="mb-6 bg-white rounded-xl shadow-sm border border-blue-100 p-6">
          <h2 className="text-sm font-semibold mb-4">
            Bearbeiten: {editUser.email}
          </h2>
          {formError && (
            <div className="mb-3 p-2 bg-red-50 border border-red-200 text-red-700 rounded text-sm">
              {formError}
            </div>
          )}
          <form onSubmit={handleUpdate} className="space-y-3">
            <input
              type="text"
              placeholder="Name"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="password"
              placeholder="Neues Passwort (leer lassen = keine Änderung)"
              value={editPassword}
              onChange={(e) => setEditPassword(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={formLoading}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
              >
                {formLoading ? "Speichern..." : "Speichern"}
              </button>
              <button
                type="button"
                onClick={() => setEditUser(null)}
                className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
              >
                Abbrechen
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Users table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-medium">Name</th>
              <th className="text-left px-4 py-3 font-medium">E-Mail</th>
              <th className="text-left px-4 py-3 font-medium">Rolle</th>
              <th className="text-left px-4 py-3 font-medium">Status</th>
              <th className="text-right px-4 py-3 font-medium">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-4 py-3">{u.name}</td>
                <td className="px-4 py-3 text-gray-500">{u.email}</td>
                <td className="px-4 py-3">
                  {u.is_admin ? (
                    <span className="inline-block px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs font-medium">
                      Admin
                    </span>
                  ) : (
                    <span className="inline-block px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                      Moderator
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {u.is_active ? (
                    <span className="inline-block px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                      Aktiv
                    </span>
                  ) : (
                    <span className="inline-block px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">
                      Deaktiviert
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-right space-x-2">
                  <button
                    onClick={() => startEdit(u)}
                    className="text-blue-600 hover:text-blue-800 text-xs"
                  >
                    Bearbeiten
                  </button>
                  {!u.is_admin && (
                    <button
                      onClick={() => handleToggleActive(u)}
                      className={`text-xs ${
                        u.is_active
                          ? "text-red-600 hover:text-red-800"
                          : "text-green-600 hover:text-green-800"
                      }`}
                    >
                      {u.is_active ? "Deaktivieren" : "Aktivieren"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                  Keine Moderatoren vorhanden.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
