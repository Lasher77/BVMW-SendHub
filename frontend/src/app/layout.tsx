import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import AuthGuard from "@/components/AuthGuard";

export const metadata: Metadata = {
  title: "BVMW SendHub",
  description: "Planung & Freigabe von Email-Aussendungen",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="de">
      <body className="min-h-screen bg-gray-50 text-gray-900">
        <Nav />
        <AuthGuard>
          <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
        </AuthGuard>
      </body>
    </html>
  );
}
