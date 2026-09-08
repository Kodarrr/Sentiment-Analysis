"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function DashboardPage() {
  const { token, isLoading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !token) {
      router.replace("/login");
    }
  }, [isLoading, token, router]);

  if (isLoading || !token) {
    return (
      <main className="flex flex-1 items-center justify-center p-6 text-sm text-black/60 dark:text-white/60">
        Loading...
      </main>
    );
  }

  return (
    <main className="flex flex-1 flex-col">
      <header className="flex items-center justify-between border-b border-black/10 px-6 py-4 dark:border-white/10">
        <h1 className="text-lg font-semibold">Feedback Dashboard</h1>
        <button
          onClick={logout}
          className="rounded border border-black/15 px-3 py-1.5 text-sm dark:border-white/15"
        >
          Sign out
        </button>
      </header>
      <div className="flex-1 p-6 text-sm text-black/60 dark:text-white/60">
        Feedback list, sentiment trend chart, and filters coming soon.
      </div>
    </main>
  );
}
