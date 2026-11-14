import { BadgeCheck, ExternalLink, MapPin, Phone } from "lucide-react";
import { Badge, Card } from "@/components/ui";
import type { Laboratory } from "@/types";
import { formatDate } from "@/utils/format";

export function LabCard({ lab }: { lab: Laboratory }) {
  const capabilities = (lab.testing_capabilities || "").split(/[;,\n]/).map((c) => c.trim()).filter(Boolean);
  return (
    <Card className="flex flex-col p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="font-semibold text-slate-900">{lab.laboratory_name}</p>
        {lab.recognition_status && (
          <Badge tone="green" className="shrink-0">
            <BadgeCheck className="h-3.5 w-3.5" /> {lab.recognition_status}
          </Badge>
        )}
      </div>
      {(lab.city || lab.state) && (
        <p className="mt-1 flex items-center gap-1 text-sm text-slate-500">
          <MapPin className="h-3.5 w-3.5" /> {[lab.city, lab.state].filter(Boolean).join(", ")}
        </p>
      )}
      {lab.address && <p className="mt-1 text-xs text-slate-500">{lab.address}</p>}
      {capabilities.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {capabilities.slice(0, 6).map((c) => <Badge key={c}>{c}</Badge>)}
          {capabilities.length > 6 && <Badge>+{capabilities.length - 6} more</Badge>}
        </div>
      )}
      <div className="mt-auto flex flex-wrap items-center gap-x-4 gap-y-1 pt-3 text-xs text-slate-500">
        {lab.contact_information && (
          <span className="flex items-center gap-1"><Phone className="h-3.5 w-3.5" /> {lab.contact_information}</span>
        )}
        {lab.official_source_url && (
          <a href={lab.official_source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-navy-700 hover:underline">
            Official record <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
        {lab.last_verified_at && <span>Verified {formatDate(lab.last_verified_at)}</span>}
      </div>
    </Card>
  );
}
