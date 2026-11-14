import { CheckCircle2, CircleHelp, XCircle } from "lucide-react";
import { Badge, statusTone } from "@/components/ui";
import type { ChecklistItem } from "@/types";

const STATUS_LABEL: Record<ChecklistItem["status"], string> = {
  meets: "Meets",
  does_not_meet: "Does not meet",
  missing_information: "Missing information",
};

const STATUS_ICON = {
  meets: <CheckCircle2 className="h-3.5 w-3.5" />,
  does_not_meet: <XCircle className="h-3.5 w-3.5" />,
  missing_information: <CircleHelp className="h-3.5 w-3.5" />,
};

export function ChecklistTable({ items }: { items: ChecklistItem[] }) {
  if (!items.length) return <p className="text-sm text-slate-500">No checklist items could be derived from the indexed requirements.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
            <th className="py-2 pr-3 font-medium">Requirement</th>
            <th className="py-2 pr-3 font-medium">Clause</th>
            <th className="py-2 pr-3 font-medium">Status</th>
            <th className="py-2 font-medium">Notes</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {items.map((item, i) => (
            <tr key={`${item.requirement}-${i}`} className="align-top">
              <td className="py-2.5 pr-3 text-slate-800">
                {item.requirement}
                {item.citation && <span className="ml-1 text-xs text-navy-600">{item.citation}</span>}
              </td>
              <td className="whitespace-nowrap py-2.5 pr-3 text-slate-600">{item.clause_number ?? "—"}</td>
              <td className="py-2.5 pr-3">
                <Badge tone={statusTone(item.status)} className="whitespace-nowrap">
                  {STATUS_ICON[item.status]} {STATUS_LABEL[item.status]}
                </Badge>
              </td>
              <td className="py-2.5 text-slate-500">{item.notes || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
