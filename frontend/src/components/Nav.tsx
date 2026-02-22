"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";

const links = [
  { href: "/calendar", label: "Kalender" },
  { href: "/requests/new", label: "Neue Anfrage" },
  { href: "/requests", label: "Meine Anfragen" },
  { href: "/settings", label: "Einstellungen" },
];

export default function Nav() {
  const path = usePathname();
  const [user, setUser] = useState("requester@bvmw.example");

  useEffect(() => {
    const stored = localStorage.getItem("x-user");
    if (stored) setUser(stored);
  }, []);

  function switchUser() {
    const options = ["requester@bvmw.example", "marketing@bvmw.example"];
    const next = options[(options.indexOf(user) + 1) % options.length];
    localStorage.setItem("x-user", next);
    setUser(next);
    window.location.reload();
  }

  return (
    <nav className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <span className="font-bold text-blue-700 text-lg">SendHub</span>
        {links.map((l) => (
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
      <button
        onClick={switchUser}
        className="text-xs bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-full text-gray-600"
        title="Dev: Benutzer wechseln"
      >
        {user.split("@")[0]}
      </button>
    </nav>
  );
}
