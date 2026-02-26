"use client";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { isAuthenticated, getSetupStatus } from "@/lib/api";

/** Pages that do NOT require authentication. */
const PUBLIC_PATHS = ["/login", "/setup", "/requests/new"];

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Skip check for public pages
    if (PUBLIC_PATHS.includes(path)) {
      setReady(true);
      return;
    }

    // Check if setup is needed
    getSetupStatus()
      .then((status) => {
        if (status.needs_setup) {
          router.replace("/setup");
          return;
        }
        if (!isAuthenticated()) {
          router.replace("/login");
          return;
        }
        setReady(true);
      })
      .catch(() => {
        // If setup-status check fails, still allow navigation
        if (!isAuthenticated()) {
          router.replace("/login");
        } else {
          setReady(true);
        }
      });
  }, [path, router]);

  if (!ready && !PUBLIC_PATHS.includes(path)) {
    return null; // Show nothing while checking auth
  }

  return <>{children}</>;
}
