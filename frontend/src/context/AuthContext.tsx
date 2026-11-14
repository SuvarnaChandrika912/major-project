"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { setUnauthorizedHandler, tokenStore } from "@/services/api";
import { authService, type RegisterInput } from "@/services/auth";
import type { User } from "@/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  ready: Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => void;
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const refreshVersion = useRef(0);
  const [authReady] = useState(() => {
    let resolve!: () => void;
    const promise = new Promise<void>((done) => {
      resolve = done;
    });
    return { promise, resolve };
  });

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const version = ++refreshVersion.current;
    const token = tokenStore.get();
    setUser(null);
    setLoading(true);
    if (!token) {
      if (version === refreshVersion.current) setLoading(false);
      return;
    }
    try {
      const currentUser = await authService.me();
      if (version === refreshVersion.current && tokenStore.get() === token) setUser(currentUser);
    } catch {
      if (version === refreshVersion.current && tokenStore.get() === token) tokenStore.clear();
    } finally {
      if (version === refreshVersion.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    void Promise.resolve().then(refreshUser).finally(() => authReady.resolve());
    const unsubscribe = tokenStore.subscribe(() => void refreshUser());
    return () => {
      unsubscribe();
      setUnauthorizedHandler(null);
    };
  }, [authReady, logout, refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await authService.login(email, password);
    tokenStore.set(res.access_token);
    setUser(res.user);
  }, []);

  const register = useCallback(async (input: RegisterInput) => {
    const res = await authService.register(input);
    tokenStore.set(res.access_token);
    setUser(res.user);
  }, []);

  const value = useMemo(
    () => ({ user, loading, ready: authReady.promise, login, register, logout, setUser }),
    [user, loading, authReady, login, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
