"use client";

import { ProtectedPage } from "@/components/layout/ProtectedPage";
import Link from "next/link";
import { Activity, Database, Languages, RefreshCw, Settings, Trash2 } from "lucide-react";
import { useState } from "react";
import { Alert, Badge, Button, Card, CardHeader, PageHeader, SkeletonList } from "@/components/ui";
import { useAsync } from "@/hooks/useAsync";
import { systemService } from "@/services/bis";
import { LANGUAGES } from "@/utils/format";

function healthTone(value: string) {
  if (/^(connected|ready|ok)/.test(value)) return "green" as const;
  if (/not configured|not pulled|loads on first use/.test(value)) return "amber" as const;
  return "red" as const;
}

export default function SettingsPage() {
  return (
    <ProtectedPage>
      <SettingsPageContent />
    </ProtectedPage>
  );
}

function SettingsPageContent() {
  const health = useAsync(() => systemService.health());
  const [cleared, setCleared] = useState(false);

  const clearLocal = () => {
    window.localStorage.removeItem("bis_saathi_recent_standards");
    window.sessionStorage.clear();
    setCleared(true);
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader title="Settings" description="System status, language preferences and local data." icon={<Settings className="h-5 w-5" />} />
      <Card>
        <CardHeader
          title="System status"
          description="Availability of the services BIS SAATHI depends on."
          icon={<Activity className="h-4 w-4" />}
          action={<Button size="sm" variant="secondary" onClick={health.reload} loading={health.loading}><RefreshCw className="h-4 w-4" /> Refresh</Button>}
        />
        <div className="p-5">
          {health.error && <Alert tone="error">{health.error}</Alert>}
          {health.loading && !health.data ? (
            <SkeletonList rows={4} />
          ) : (
            health.data && (
              <dl className="divide-y divide-slate-100 text-sm">
                {[
                  ["MySQL database", health.data.database],
                  ["Pinecone vector database", health.data.pinecone],
                  ["Language model", health.data.llm],
                  ["Embedding model", health.data.embedding_model],
                ].map(([label, value]) => (
                  <div key={label} className="flex flex-col gap-1 py-2.5 sm:flex-row sm:items-center sm:justify-between">
                    <dt className="text-slate-600">{label}</dt>
                    <dd><Badge tone={healthTone(value)}>{value}</Badge></dd>
                  </div>
                ))}
              </dl>
            )
          )}
        </div>
      </Card>
      <Card>
        <CardHeader title="Languages" icon={<Languages className="h-4 w-4" />} description="Answers can be translated into these languages. Standard numbers and clause references are never translated." />
        <div className="flex flex-wrap items-center gap-2 p-5">
          {LANGUAGES.map((l) => <Badge key={l.value} tone="navy">{l.label} · {l.native}</Badge>)}
          <Link href="/profile" className="ml-auto text-sm font-medium text-navy-700 hover:underline">Change preferred language</Link>
        </div>
      </Card>
      <Card>
        <CardHeader title="Local data" icon={<Database className="h-4 w-4" />} description="Recently viewed standards are stored only in this browser." />
        <div className="flex items-center justify-between gap-3 p-5">
          {cleared ? <Alert tone="success">Local browsing data cleared.</Alert> : <p className="text-sm text-slate-600">Clear recently viewed standards and pending searches.</p>}
          <Button variant="secondary" onClick={clearLocal}><Trash2 className="h-4 w-4" /> Clear</Button>
        </div>
      </Card>
    </div>
  );
}
