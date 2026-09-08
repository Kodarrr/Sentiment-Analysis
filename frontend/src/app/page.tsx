"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useFeedbackList } from "@/lib/useFeedbackList";
import { FeedbackTable } from "@/components/FeedbackTable";
import { Pagination } from "@/components/Pagination";

const PAGE_SIZE = 20;

export default function DashboardPage() {
  const { token, isLoading: isAuthLoading, logout } = useAuth();
  const router = useRouter();
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!isAuthLoading && !token) {
      router.replace("/login");
    }
  }, [isAuthLoading, token, router]);

  const {
    data,
    error,
    isLoading: isFeedbackLoading,
  } = useFeedbackList({ token, page, pageSize: PAGE_SIZE });

  if (isAuthLoading || !token) {
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

      <div className="flex-1 space-y-4 p-6">
        {error && (
          <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
            {error}
          </p>
        )}

        {isFeedbackLoading && !data ? (
          <p className="text-sm text-black/60 dark:text-white/60">Loading feedback...</p>
        ) : data ? (
          <>
            <div className="overflow-hidden rounded-lg border border-black/10 dark:border-white/10">
              <FeedbackTable items={data.items} />
            </div>
            <Pagination
              page={data.page}
              pageSize={data.page_size}
              total={data.total}
              onPageChange={setPage}
            />
          </>
        ) : null}
      </div>
    </main>
  );
}
