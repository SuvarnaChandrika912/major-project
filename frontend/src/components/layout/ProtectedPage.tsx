"use client";

import type { ReactNode } from "react";
import { Suspense, use, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Spinner } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";

export function ProtectedPage({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<AuthLoading />}>
      <AuthenticatedPage>{children}</AuthenticatedPage>
    </Suspense>
  );
}

function AuthenticatedPage({ children }: { children: ReactNode }) {
  const { user, loading, ready } = useAuth();
  const router = useRouter();
  use(ready);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, router, user]);

  if (loading || !user) return <AuthLoading />;

  return children;
}

function AuthLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Spinner className="h-7 w-7" />
    </div>
  );
}
