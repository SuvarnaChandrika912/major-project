"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { X } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { NAV_ITEMS } from "@/lib/navigation";
import { cn } from "@/utils/format";

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();
  const { user } = useAuth();
  const items = NAV_ITEMS.filter((item) => !item.adminOnly || user?.is_admin);

  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-slate-900/30 lg:hidden" onClick={onClose} />}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-16 items-center justify-between border-b border-slate-100 px-5">
          <Link href="/" className="flex items-center gap-2.5" onClick={onClose}>
            <Image src="/logo.svg" alt="" width={32} height={32} />
            <div className="leading-tight">
              <p className="text-[15px] font-bold tracking-wide text-navy-900">BIS SAATHI</p>
              <p className="text-[11px] text-slate-500">Standards & Certification AI</p>
            </div>
          </Link>
          <button className="rounded-md p-1 text-slate-500 hover:bg-slate-100 lg:hidden" onClick={onClose} aria-label="Close menu">
            <X className="h-5 w-5" />
          </button>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4" aria-label="Main">
          {items.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  active ? "bg-navy-900 text-white" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
                  item.adminOnly && !active && "mt-3 border-t border-slate-100 pt-3",
                )}
              >
                <Icon className="h-[18px] w-[18px] shrink-0" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-100 p-4 text-[11px] leading-relaxed text-slate-500">
          Preliminary AI guidance. Official decisions rest with the Bureau of Indian Standards.
        </div>
      </aside>
    </>
  );
}
