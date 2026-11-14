"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Bell, LogOut, Menu, Search, Settings, User } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { PENDING_QUERY_KEY } from "@/lib/navigation";
import { notificationService } from "@/services/bis";

export function Topbar({ onMenu }: { onMenu: () => void }) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [unread, setUnread] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    const load = () =>
      notificationService
        .list(true)
        .then((items) => active && setUnread(items.length))
        .catch(() => undefined);
    void load();
    const timer = window.setInterval(load, 30000);
    window.addEventListener("notifications:changed", load);
    return () => {
      active = false;
      window.clearInterval(timer);
      window.removeEventListener("notifications:changed", load);
    };
  }, []);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    window.sessionStorage.setItem(PENDING_QUERY_KEY, q);
    setQuery("");
    router.push("/assistant");
    window.dispatchEvent(new Event("assistant:pending-query"));
  };

  const initials = (user?.full_name || "?")
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-6">
      <button className="rounded-md p-2 text-slate-600 hover:bg-slate-100 lg:hidden" onClick={onMenu} aria-label="Open menu">
        <Menu className="h-5 w-5" />
      </button>
      <form onSubmit={submit} className="relative hidden max-w-xl flex-1 sm:block">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask BIS SAATHI about standards, certification, hallmarking…"
          className="h-10 w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm focus:border-navy-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-navy-100"
          aria-label="Ask BIS SAATHI"
        />
      </form>
      <div className="ml-auto flex items-center gap-1">
        <Link href="/notifications" className="relative rounded-lg p-2 text-slate-600 hover:bg-slate-100" aria-label="Notifications">
          <Bell className="h-5 w-5" />
          {unread > 0 && (
            <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-semibold text-white">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </Link>
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="flex items-center gap-2 rounded-lg p-1.5 hover:bg-slate-100"
            aria-label="User menu"
            aria-expanded={menuOpen}
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-navy-900 text-xs font-semibold text-white">{initials}</span>
            <span className="hidden text-left md:block">
              <span className="block text-sm font-medium leading-tight text-slate-800">{user?.full_name}</span>
              <span className="block text-[11px] leading-tight text-slate-500">{user?.is_admin ? "Administrator" : "Member"}</span>
            </span>
          </button>
          {menuOpen && (
            <div className="absolute right-0 mt-2 w-52 overflow-hidden rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
              <Link href="/profile" onClick={() => setMenuOpen(false)} className="flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">
                <User className="h-4 w-4" /> Profile
              </Link>
              <Link href="/settings" onClick={() => setMenuOpen(false)} className="flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">
                <Settings className="h-4 w-4" /> Settings
              </Link>
              <button
                onClick={() => {
                  logout();
                  router.replace("/login");
                }}
                className="flex w-full items-center gap-2 border-t border-slate-100 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
              >
                <LogOut className="h-4 w-4" /> Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
