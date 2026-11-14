"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { Alert, Button, Field, Input, Select } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import type { Language } from "@/types";
import { errorMessage, LANGUAGES } from "@/utils/format";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    confirm: "",
    organization: "",
    preferred_language: "en" as Language,
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const update = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (form.password.length < 8) return setError("Password must be at least 8 characters.");
    if (form.password !== form.confirm) return setError("Passwords do not match.");
    setSubmitting(true);
    try {
      await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
        preferred_language: form.preferred_language,
        organization: form.organization.trim() || undefined,
      });
      router.replace("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout title="Create your account" subtitle="Access standards research, certification guidance and compliance tools.">
      <form onSubmit={submit} className="space-y-4">
        {error && <Alert tone="error">{error}</Alert>}
        <Field label="Full name" htmlFor="full_name" required>
          <Input id="full_name" value={form.full_name} onChange={update("full_name")} required minLength={2} />
        </Field>
        <Field label="Email" htmlFor="email" required>
          <Input id="email" type="email" autoComplete="email" value={form.email} onChange={update("email")} required />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Organization" htmlFor="organization">
            <Input id="organization" value={form.organization} onChange={update("organization")} placeholder="Optional" />
          </Field>
          <Field label="Preferred language" htmlFor="language">
            <Select id="language" value={form.preferred_language} onChange={update("preferred_language")}>
              {LANGUAGES.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label} ({l.native})
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Password" htmlFor="password" required hint="At least 8 characters">
            <Input id="password" type="password" autoComplete="new-password" value={form.password} onChange={update("password")} required />
          </Field>
          <Field label="Confirm password" htmlFor="confirm" required>
            <Input id="confirm" type="password" autoComplete="new-password" value={form.confirm} onChange={update("confirm")} required />
          </Field>
        </div>
        <Button type="submit" size="lg" className="w-full" loading={submitting}>
          Create account
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-navy-700 hover:underline">
          Log in
        </Link>
      </p>
    </AuthLayout>
  );
}
