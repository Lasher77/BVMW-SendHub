"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { isAuthenticated, getStoredUser, logout } from "@/lib/api";
import type { User } from "@/types";

export default function Nav() {
  const path = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setLoggedIn(isAuthenticated());
    setUser(getStoredUser());
  }, []);

  // Dev-mode user switcher (only shown in dev with X-User header)
  const [devUser, setDevUser] = useState("");
  useEffect(() => {
    const stored = localStorage.getItem("x-user");
    if (stored) setDevUser(stored);
  }, []);

  function handleLogout() {
    logout();
    setLoggedIn(false);
    setUser(null);
    router.push("/login");
  }

  // On login/setup pages, don't show nav
  if (path === "/login" || path === "/setup") return null;

  // Public pages (request form) — show minimal nav
  if (!loggedIn) {
    return (
      <nav className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <span className="font-bold text-blue-700 text-lg">SendHub</span>
          <Link
            href="/requests/new"
            className={`text-sm font-medium ${
              path === "/requests/new"
                ? "text-blue-600 border-b-2 border-blue-600 pb-0.5"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            Neue Anfrage
          </Link>
        </div>
        <Link
          href="/login"
          className="text-xs bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-full text-gray-600"
        >
          Anmelden
        </Link>
      </nav>
    );
  }

  // Authenticated nav
  const isModerator = user?.role === "moderator" || user?.role === "marketing";
  const isAdmin = isModerator && user?.is_admin;

  const links = [
    { href: "/calendar", label: "Kalender", show: isModerator },
    { href: "/requests/new", label: "Neue Anfrage", show: true },
    { href: "/requests", label: "Anfragen", show: isModerator },
    { href: "/settings", label: "Einstellungen", show: isModerator },
    { href: "/users", label: "Benutzer", show: isAdmin },
  ];

  return (
    <nav className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <span className="font-bold text-blue-700 text-lg">SendHub</span>
        {links
          .filter((l) => l.show)
          .map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`text-sm font-medium ${
                path.startsWith(l.href)
                  ? "text-blue-600 border-b-2 border-blue-600 pb-0.5"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {l.label}
            </Link>
          ))}
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-500">
          {user?.name}
          {isAdmin && (
            <span className="ml-1 px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded text-[10px] font-medium">
              Admin
            </span>
          )}
        </span>
        <button
          onClick={handleLogout}
          className="text-xs bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-full text-gray-600"
        >
          Abmelden
        </button>
      </div>
    </nav>
  );
}
