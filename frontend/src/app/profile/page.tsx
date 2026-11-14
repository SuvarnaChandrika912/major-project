"use client";

import { useState } from "react";
import { User } from "lucide-react";
import { Alert, Badge, Button, Card, CardHeader, Field, Input, PageHeader, Select } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { ProtectedPage } from "@/components/layout/ProtectedPage";
import { authService } from "@/services/auth";
import type { Language } from "@/types";
import { errorMessage, formatDate, LANGUAGES } from "@/utils/format";

export default function ProfilePage() {
  return (
    <ProtectedPage>
      <ProfilePageContent />
    </ProtectedPage>
  );
}

function ProfilePageContent() {
  const { user, setUser } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [organization, setOrganization] = useState(user?.organization ?? "");
  const [language, setLanguage] = useState<Language>(user?.preferred_language ?? "en");
  const [saving, setSaving] = useState(false);
  const [profileMsg, setProfileMsg] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const [pwSaving, setPwSaving] = useState(false);
  const [pwMsg, setPwMsg] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  const saveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setProfileMsg(null);
    try {
      const updated = await authService.updateProfile({ full_name: fullName.trim(), organization: organization.trim() || null, preferred_language: language });
      setUser(updated);
      setProfileMsg({ tone: "success", text: "Profile updated." });
    } catch (err) {
      setProfileMsg({ tone: "error", text: errorMessage(err) });
    } finally {
      setSaving(false);
    }
  };

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwMsg(null);
    if (pw.next.length < 8) return setPwMsg({ tone: "error", text: "New password must be at least 8 characters." });
    if (pw.next !== pw.confirm) return setPwMsg({ tone: "error", text: "New passwords do not match." });
    setPwSaving(true);
    try {
      await authService.changePassword(pw.current, pw.next);
      setPw({ current: "", next: "", confirm: "" });
      setPwMsg({ tone: "success", text: "Password changed." });
    } catch (err) {
      setPwMsg({ tone: "error", text: errorMessage(err) });
    } finally {
      setPwSaving(false);
    }
  };

  if (!user) return null;
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader title="Profile" description="Manage your account details and preferences." icon={<User className="h-5 w-5" />} />
      <Card className="flex items-center gap-4 p-5">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-navy-900 text-lg font-semibold text-white">
          {user.full_name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase()}
        </div>
        <div>
          <p className="font-semibold text-slate-900">{user.full_name}</p>
          <p className="text-sm text-slate-500">{user.email}</p>
          <div className="mt-1 flex gap-1.5">
            <Badge tone={user.is_admin ? "navy" : "neutral"}>{user.is_admin ? "Administrator" : "Member"}</Badge>
            <Badge>Joined {formatDate(user.created_at)}</Badge>
          </div>
        </div>
      </Card>
      <Card>
        <CardHeader title="Personal details" />
        <form onSubmit={saveProfile} className="space-y-4 p-5">
          {profileMsg && <Alert tone={profileMsg.tone}>{profileMsg.text}</Alert>}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Full name" htmlFor="fn"><Input id="fn" value={fullName} onChange={(e) => setFullName(e.target.value)} required minLength={2} /></Field>
            <Field label="Organization" htmlFor="org"><Input id="org" value={organization} onChange={(e) => setOrganization(e.target.value)} /></Field>
            <Field label="Email" htmlFor="em"><Input id="em" value={user.email} disabled /></Field>
            <Field label="Preferred answer language" htmlFor="lang">
              <Select id="lang" value={language} onChange={(e) => setLanguage(e.target.value as Language)}>
                {LANGUAGES.map((l) => <option key={l.value} value={l.value}>{l.label} ({l.native})</option>)}
              </Select>
            </Field>
          </div>
          <div className="flex justify-end"><Button type="submit" loading={saving}>Save changes</Button></div>
        </form>
      </Card>
      <Card>
        <CardHeader title="Change password" />
        <form onSubmit={changePassword} className="space-y-4 p-5">
          {pwMsg && <Alert tone={pwMsg.tone}>{pwMsg.text}</Alert>}
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Current password" htmlFor="pc"><Input id="pc" type="password" autoComplete="current-password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} required /></Field>
            <Field label="New password" htmlFor="pn"><Input id="pn" type="password" autoComplete="new-password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} required /></Field>
            <Field label="Confirm new password" htmlFor="pcf"><Input id="pcf" type="password" autoComplete="new-password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} required /></Field>
          </div>
          <div className="flex justify-end"><Button type="submit" loading={pwSaving}>Update password</Button></div>
        </form>
      </Card>
    </div>
  );
}
