"use client";

import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { INTENT_LABELS } from "@/utils/format";

export function ActivityChart({ data }: { data: { date: string; queries: number }[] }) {
  const formatted = data.map((d) => ({
    ...d,
    label: new Date(`${d.date}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short" }),
  }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={formatted} margin={{ top: 10, right: 8, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="queriesFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#23458a" stopOpacity={0.25} />
            <stop offset="100%" stopColor="#23458a" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
        <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} />
        <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }} />
        <Area type="monotone" dataKey="queries" name="Answers" stroke="#0b2559" strokeWidth={2} fill="url(#queriesFill)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function IntentChart({ data }: { data: { intent: string; count: number }[] }) {
  const formatted = data.slice(0, 6).map((d) => ({ name: INTENT_LABELS[d.intent] ?? d.intent, count: d.count }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={formatted} layout="vertical" margin={{ top: 4, right: 12, left: 8, bottom: 0 }}>
        <XAxis type="number" allowDecimals={false} hide />
        <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 12, fill: "#475569" }} tickLine={false} axisLine={false} />
        <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }} cursor={{ fill: "#f1f5f9" }} />
        <Bar dataKey="count" name="Queries" fill="#23458a" radius={[0, 4, 4, 0]} barSize={16} />
      </BarChart>
    </ResponsiveContainer>
  );
}
