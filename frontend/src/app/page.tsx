"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  ArrowRight,
  Bell,
  Bot,
  ClipboardCheck,
  Database,
  FileBarChart,
  FlaskConical,
  Gem,
  MessageSquare,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import { ActivityChart, IntentChart } from "@/components/dashboard/ActivityChart";
import { Alert, Badge, Card, CardHeader, EmptyState, Skeleton, SkeletonList } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { ProtectedPage } from "@/components/layout/ProtectedPage";
import { useAsync } from "@/hooks/useAsync";
import { useRecentStandards } from "@/hooks/useRecentStandards";
import { PENDING_QUERY_KEY, POPULAR_QUERIES } from "@/lib/navigation";
import { notificationService } from "@/services/bis";
import { chatService } from "@/services/chat";
import { reportService } from "@/services/reports";
import { REPORT_TYPE_LABELS, timeAgo } from "@/utils/format";

const SERVICES = [
  { href: "/standards", label: "Find Indian Standards", desc: "Search by number, product or keyword", icon: Search },
  { href: "/certification", label: "Certification Guide", desc: "Step-by-step certification roadmap", icon: ShieldCheck },
  { href: "/laboratories", label: "Laboratory Finder", desc: "Testing labs by capability and location", icon: FlaskConical },
  { href: "/hallmarking", label: "Hallmarking", desc: "HUID and jewellery hallmark guidance", icon: Gem },
  { href: "/consumer-help", label: "Consumer Help", desc: "ISI mark verification and complaints", icon: Users },
  { href: "/compliance", label: "Compliance Workspace", desc: "Preliminary product gap analysis", icon: ClipboardCheck },
];

export default function DashboardPage() {
  return (
    <ProtectedPage>
      <DashboardPageContent />
    </ProtectedPage>
  );
}

function DashboardPageContent() {
  const { user } = useAuth();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const summary = useAsync(() => reportService.dashboard());
  const sessions = useAsync(() => chatService.sessions());
  const reports = useAsync(() => reportService.list());
  const notifications = useAsync(() => notificationService.list());
  const recent = useRecentStandards();

  const ask = (q: string) => {
    if (!q.trim()) return;
    window.sessionStorage.setItem(PENDING_QUERY_KEY, q.trim());
    router.push("/assistant");
  };

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const stats = summary.data;

  return (
    <div className="space-y-6">
      <section className="rounded-2xl bg-navy-900 px-6 py-7 text-white sm:px-8">
        <p className="text-sm text-navy-200">{greeting},</p>
        <h1 className="mt-0.5 text-2xl font-semibold">{user?.full_name}</h1>
        <p className="mt-2 max-w-2xl text-sm text-navy-100">
          Ask about Indian Standards, certification, testing or hallmarking. Every answer is grounded in indexed BIS documents and verified before it reaches you.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(query);
          }}
          className="mt-5 flex max-w-2xl gap-2"
        >
          <div className="relative flex-1">
            <Sparkles className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-navy-300" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Which standard applies to LED bulbs?"
              className="h-12 w-full rounded-xl border-0 bg-white pl-10 pr-3 text-[15px] text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-navy-300"
              aria-label="Ask BIS SAATHI"
            />
          </div>
          <button type="submit" className="flex h-12 items-center gap-2 rounded-xl bg-white/10 px-5 text-sm font-medium ring-1 ring-white/30 hover:bg-white/20">
            Ask <ArrowRight className="h-4 w-4" />
          </button>
        </form>
      </section>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { label: "Conversations", value: stats?.total_sessions, icon: MessageSquare },
          { label: "Questions asked", value: stats?.total_messages, icon: Bot },
          { label: "Saved reports", value: stats?.total_reports, icon: FileBarChart },
          { label: "Indexed documents", value: stats?.indexed_documents, icon: Database },
        ].map(({ label, value, icon: Icon }) => (
          <Card key={label} className="flex items-center gap-3 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy-50 text-navy-700">
              <Icon className="h-5 w-5" />
            </div>
            <div>
              {summary.loading ? <Skeleton className="h-6 w-10" /> : <p className="text-xl font-semibold text-slate-900">{value ?? 0}</p>}
              <p className="text-xs text-slate-500">{label}</p>
            </div>
          </Card>
        ))}
      </section>
      {summary.error && <Alert tone="error">{summary.error}</Alert>}
      {stats && stats.indexed_documents === 0 && (
        <Alert tone="warning" title="The knowledge base is empty">
          No BIS documents have been indexed yet, so answers cannot cite sources.
          {user?.is_admin ? (
            <>
              {" "}
              <Link href="/admin/documents" className="font-medium underline">
                Upload authorised documents
              </Link>{" "}
              to get started.
            </>
          ) : (
            " Ask your administrator to upload authorised BIS documents."
          )}
        </Alert>
      )}

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">BIS services</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {SERVICES.map(({ href, label, desc, icon: Icon }) => (
            <Link key={href} href={href} className="group flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-navy-200">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-navy-50 text-navy-700 group-hover:bg-navy-900 group-hover:text-white">
                <Icon className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="font-medium text-slate-800">{label}</p>
                <p className="truncate text-sm text-slate-500">{desc}</p>
              </div>
              <ArrowRight className="h-4 w-4 text-slate-300 group-hover:text-navy-700" />
            </Link>
          ))}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Assistant activity" description="Answers generated over the last 14 days" />
          <div className="p-4">{summary.loading ? <Skeleton className="h-52 w-full" /> : <ActivityChart data={stats?.activity ?? []} />}</div>
        </Card>
        <Card>
          <CardHeader title="Topics you asked about" />
          <div className="p-4">
            {summary.loading ? (
              <Skeleton className="h-52 w-full" />
            ) : stats?.intent_distribution.length ? (
              <IntentChart data={stats.intent_distribution} />
            ) : (
              <p className="py-16 text-center text-sm text-slate-500">No questions yet.</p>
            )}
          </div>
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader title="Recent conversations" action={<Link href="/assistant" className="text-sm font-medium text-navy-700 hover:underline">Open</Link>} />
          <div className="p-2">
            {sessions.loading ? (
              <div className="p-3"><SkeletonList /></div>
            ) : sessions.data?.length ? (
              sessions.data.slice(0, 5).map((s) => (
                <Link key={s.id} href={`/assistant#session-${s.id}`} className="block rounded-lg px-3 py-2 hover:bg-slate-50">
                  <p className="truncate text-sm font-medium text-slate-700">{s.title}</p>
                  <p className="text-xs text-slate-400">{timeAgo(s.updated_at)}</p>
                </Link>
              ))
            ) : (
              <EmptyState icon={<MessageSquare className="h-5 w-5" />} title="No conversations yet" />
            )}
          </div>
        </Card>
        <Card>
          <CardHeader title="Recently viewed standards" action={<Link href="/standards" className="text-sm font-medium text-navy-700 hover:underline">Search</Link>} />
          <div className="p-2">
            {recent.items.length ? (
              recent.items.slice(0, 5).map((s) => (
                <Link key={s.id} href={`/standards#standard-${s.id}`} className="block rounded-lg px-3 py-2 hover:bg-slate-50">
                  <p className="text-sm font-medium text-navy-800">{s.standard_number}</p>
                  <p className="truncate text-xs text-slate-500">{s.title}</p>
                </Link>
              ))
            ) : (
              <EmptyState icon={<Search className="h-5 w-5" />} title="No standards viewed yet" />
            )}
          </div>
        </Card>
        <Card>
          <CardHeader title="Saved reports" action={<Link href="/reports" className="text-sm font-medium text-navy-700 hover:underline">All reports</Link>} />
          <div className="p-2">
            {reports.loading ? (
              <div className="p-3"><SkeletonList /></div>
            ) : reports.data?.length ? (
              reports.data.slice(0, 5).map((r) => (
                <Link key={r.id} href={`/reports#report-${r.id}`} className="block rounded-lg px-3 py-2 hover:bg-slate-50">
                  <p className="truncate text-sm font-medium text-slate-700">{r.report_title}</p>
                  <p className="text-xs text-slate-400">{REPORT_TYPE_LABELS[r.report_type]} · {timeAgo(r.created_at)}</p>
                </Link>
              ))
            ) : (
              <EmptyState icon={<FileBarChart className="h-5 w-5" />} title="No reports yet" />
            )}
          </div>
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Popular questions" icon={<Sparkles className="h-4 w-4" />} />
          <div className="flex flex-wrap gap-2 p-4">
            {POPULAR_QUERIES.map((q) => (
              <button key={q} onClick={() => ask(q)} className="rounded-full border border-slate-200 px-3 py-1.5 text-left text-sm text-slate-700 hover:border-navy-200 hover:bg-navy-50/50">
                {q}
              </button>
            ))}
          </div>
        </Card>
        <Card>
          <CardHeader title="Notifications" icon={<Bell className="h-4 w-4" />} action={<Link href="/notifications" className="text-sm font-medium text-navy-700 hover:underline">View all</Link>} />
          <div className="p-2">
            {notifications.loading ? (
              <div className="p-3"><SkeletonList /></div>
            ) : notifications.data?.length ? (
              notifications.data.slice(0, 4).map((n) => (
                <div key={n.id} className="flex items-start gap-2 rounded-lg px-3 py-2">
                  {!n.read_status && <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-navy-600" />}
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-700">{n.title}</p>
                    <p className="line-clamp-1 text-xs text-slate-500">{n.description}</p>
                  </div>
                  <Badge className="ml-auto shrink-0">{timeAgo(n.created_at)}</Badge>
                </div>
              ))
            ) : (
              <EmptyState icon={<Bell className="h-5 w-5" />} title="You're all caught up" />
            )}
          </div>
        </Card>
      </section>
    </div>
  );
}
