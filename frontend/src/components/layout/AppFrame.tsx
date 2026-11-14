"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

const PUBLIC_ROUTES = ["/login", "/register"];

/** Chooses between the public auth layout and the protected application shell. */
export function AppFrame({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const isPublic = PUBLIC_ROUTES.includes(pathname);

  useEffect(() => {
    if (user && isPublic) router.replace("/");
  }, [user, isPublic, router]);

  if (isPublic || loading || !user) return <>{children}</>;

  return (
    <div className="min-h-screen">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <div className="lg:pl-64">
        <Topbar onMenu={() => setMenuOpen(true)} />
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
