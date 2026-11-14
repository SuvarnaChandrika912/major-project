"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { Alert, Button, Field, Input } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { errorMessage } from "@/utils/format";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      router.replace("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout title="Welcome back" subtitle="Log in to continue to BIS SAATHI.">
      <form onSubmit={submit} className="space-y-4">
        {error && <Alert tone="error">{error}</Alert>}
        <Field label="Email" htmlFor="email" required>
          <Input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </Field>
        <Field label="Password" htmlFor="password" required>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Field>
        <Button type="submit" size="lg" className="w-full" loading={submitting}>
          Log in
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">
        New to BIS SAATHI?{" "}
        <Link href="/register" className="font-medium text-navy-700 hover:underline">
          Create an account
        </Link>
      </p>
    </AuthLayout>
  );
}
