"use client";

import { ProtectedPage } from "@/components/layout/ProtectedPage";
import { Bell, CheckCheck, CheckCircle2, CircleAlert, Info, Trash2, TriangleAlert } from "lucide-react";
import { Alert, Button, Card, EmptyState, PageHeader, SkeletonList } from "@/components/ui";
import { useAsync } from "@/hooks/useAsync";
import { notificationService } from "@/services/bis";
import type { AppNotification } from "@/types";
import { cn, formatDate } from "@/utils/format";

const ICONS: Record<AppNotification["notification_type"], React.ReactNode> = {
  info: <Info className="h-4 w-4 text-sky-600" />,
  success: <CheckCircle2 className="h-4 w-4 text-emerald-600" />,
  warning: <TriangleAlert className="h-4 w-4 text-amber-600" />,
  error: <CircleAlert className="h-4 w-4 text-red-600" />,
  ingestion_success: <CheckCircle2 className="h-4 w-4 text-emerald-600" />,
  ingestion_error: <CircleAlert className="h-4 w-4 text-red-600" />,
};

export default function NotificationsPage() {
  return (
    <ProtectedPage>
      <NotificationsPageContent />
    </ProtectedPage>
  );
}

function NotificationsPageContent() {
  const { data, loading, error, setData, reload } = useAsync(() => notificationService.list());
  const changed = () => window.dispatchEvent(new Event("notifications:changed"));

  const markRead = async (n: AppNotification) => {
    if (n.read_status) return;
    await notificationService.markRead(n.id);
    setData((data ?? []).map((x) => (x.id === n.id ? { ...x, read_status: true } : x)));
    changed();
  };

  const markAll = async () => {
    await notificationService.markAllRead();
    await reload();
    changed();
  };

  const remove = async (id: number) => {
    await notificationService.remove(id);
    setData((data ?? []).filter((x) => x.id !== id));
    changed();
  };

  const unread = (data ?? []).filter((n) => !n.read_status).length;

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="Notifications"
        description={unread ? `${unread} unread` : "You're all caught up."}
        icon={<Bell className="h-5 w-5" />}
        action={<Button variant="secondary" onClick={markAll} disabled={!unread}><CheckCheck className="h-4 w-4" /> Mark all read</Button>}
      />
      {error && <Alert tone="error" className="mb-4">{error}</Alert>}
      <Card>
        {loading ? (
          <div className="p-5"><SkeletonList rows={5} /></div>
        ) : !data?.length ? (
          <EmptyState icon={<Bell className="h-5 w-5" />} title="No notifications" description="Document ingestion updates will appear here." />
        ) : (
          <ul className="divide-y divide-slate-100">
            {data.map((n) => (
              <li key={n.id} className={cn("group flex items-start gap-3 px-5 py-4", !n.read_status && "bg-navy-50/40")}>
                <div className="mt-0.5">{ICONS[n.notification_type] ?? ICONS.info}</div>
                <button onClick={() => markRead(n)} className="min-w-0 flex-1 text-left">
                  <p className={cn("text-sm", n.read_status ? "text-slate-700" : "font-semibold text-slate-900")}>{n.title}</p>
                  <p className="mt-0.5 text-sm text-slate-500">{n.description}</p>
                  <p className="mt-1 text-xs text-slate-400">{formatDate(n.created_at, true)}</p>
                </button>
                <button onClick={() => remove(n.id)} className="rounded p-1 text-slate-400 opacity-0 hover:text-red-600 group-hover:opacity-100 focus:opacity-100" aria-label="Delete notification">
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
