"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { apiFetch } from "@/lib/api";

const TOKEN_STORAGE_KEY = "sentiment_admin_token";

interface AuthContextValue {
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    try {
      // One-time hydration from localStorage after mount (unavailable during SSR) -
      // not a reactive sync, so the cascading-render concern this rule targets doesn't apply.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setToken(localStorage.getItem(TOKEN_STORAGE_KEY));
    } catch {
      // localStorage unavailable (private mode, disabled storage, etc.) - stay logged out
    }
    setIsLoading(false);
  }, []);

  async function login(email: string, password: string) {
    const data = await apiFetch<{ access_token: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    try {
      localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
    } catch {
      // ignore storage failures - the in-memory token still works for this session
    }
  }

  function logout() {
    setToken(null);
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    } catch {
      // ignore storage failures
    }
  }

  return (
    <AuthContext.Provider value={{ token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
