"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useFeedbackList } from "@/lib/useFeedbackList";
import { useSentimentTrend } from "@/lib/useSentimentTrend";
import { useSentimentDistribution } from "@/lib/useSentimentDistribution";
import { FeedbackTable } from "@/components/FeedbackTable";
import { Pagination } from "@/components/Pagination";
import { SentimentTrendChart } from "@/components/SentimentTrendChart";
import { LabelDistributionChart } from "@/components/LabelDistributionChart";
import { Filters, type FiltersValue } from "@/components/Filters";
import { SentimentTester } from "@/components/SentimentTester";

const PAGE_SIZE = 20;
const EMPTY_FILTERS: FiltersValue = { sentiment: "", startDate: "", endDate: "" };

export default function DashboardPage() {
  const { token, isLoading: isAuthLoading, logout } = useAuth();
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<FiltersValue>(EMPTY_FILTERS);

  useEffect(() => {
    if (!isAuthLoading && !token) {
      router.replace("/login");
    }
  }, [isAuthLoading, token, router]);

  const {
    data,
    error,
    isLoading: isFeedbackLoading,
    refetch: refetchFeedback,
  } = useFeedbackList({
    token,
    page,
    pageSize: PAGE_SIZE,
    sentiment: filters.sentiment || undefined,
    startDate: filters.startDate || undefined,
    endDate: filters.endDate || undefined,
  });

  const {
    data: trend,
    error: trendError,
    refetch: refetchTrend,
  } = useSentimentTrend({
    token,
    startDate: filters.startDate || undefined,
    endDate: filters.endDate || undefined,
  });

  const {
    data: distribution,
    error: distError,
    refetch: refetchDistribution,
  } = useSentimentDistribution({
    token,
    startDate: filters.startDate || undefined,
    endDate: filters.endDate || undefined,
  });

  function handleFiltersChange(next: FiltersValue) {
    setFilters(next);
    setPage(1);
  }

  function handleRefreshAll() {
    refetchFeedback();
    refetchTrend();
    refetchDistribution();
  }

  if (isAuthLoading || !token) {
    return (
      <main className="flex min-h-screen flex-1 items-center justify-center p-6 text-sm text-slate-500">
        <div className="flex items-center gap-3">
          <svg className="h-5 w-5 animate-spin text-emerald-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
          <span>Loading Sentiment Intelligence Dashboard...</span>
        </div>
      </main>
    );
  }

  // Calculate quick KPI metrics from distribution
  const totalCount = distribution?.total ?? data?.total ?? 0;
  const posCount = (distribution?.polarities?.positive ?? 0);
  const negCount = (distribution?.polarities?.negative ?? 0);
  const neuCount = (distribution?.polarities?.neutral ?? 0);
  const posPct = totalCount > 0 ? ((posCount / totalCount) * 100).toFixed(1) : "0.0";
  const negPct = totalCount > 0 ? ((negCount / totalCount) * 100).toFixed(1) : "0.0";
  const neuPct = totalCount > 0 ? ((neuCount / totalCount) * 100).toFixed(1) : "0.0";

  return (
    <main className="flex min-h-screen flex-1 flex-col bg-slate-50/60 dark:bg-slate-950/70">
      {/* Modern Sticky Navigation Bar */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200/80 bg-white/80 px-6 py-3.5 backdrop-blur-md dark:border-slate-800/80 dark:bg-slate-900/80">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white shadow-sm shadow-emerald-500/30">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-slate-900 dark:text-white">
                Sentiment Intelligence
              </h1>
              <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 border border-emerald-200/60 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800">
                v2.0 Active
              </span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Bengali (BanglaBERT 5-Class) &amp; English (DistilBERT SST-2)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleRefreshAll}
            title="Refresh All Data"
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 active:scale-95 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Refresh</span>
          </button>

          <button
            onClick={logout}
            className="rounded-xl border border-rose-200/70 bg-rose-50/50 px-3 py-1.5 text-xs font-semibold text-rose-700 transition hover:bg-rose-100/70 active:scale-95 dark:border-rose-900/40 dark:bg-rose-950/30 dark:text-rose-300 dark:hover:bg-rose-900/50"
          >
            Sign out
          </button>
        </div>
      </header>

      <div className="flex-1 space-y-6 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Error notification banner */}
        {(error || trendError || distError) && (
          <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-3.5 text-xs font-medium text-red-700 dark:border-red-900/50 dark:bg-red-950/50 dark:text-red-300">
            <svg className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>{error ?? trendError ?? distError}</span>
          </div>
        )}

        {/* KPI Metric Summary Cards */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
          {/* Card 1: Total */}
          <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Feedback</p>
            <p className="mt-2 text-2xl font-extrabold text-slate-900 dark:text-white">{totalCount}</p>
            <p className="mt-1 text-[11px] text-slate-400">Processed through RQ</p>
          </div>

          {/* Card 2: Positive */}
          <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">Positive Sentiment</p>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-extrabold text-emerald-600 dark:text-emerald-400">{posCount}</span>
              <span className="text-xs font-semibold text-slate-400">({posPct}%)</span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400">SP / WP / POSITIVE</p>
          </div>

          {/* Card 3: Neutral */}
          <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Neutral Sentiment</p>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-extrabold text-slate-700 dark:text-slate-200">{neuCount}</span>
              <span className="text-xs font-semibold text-slate-400">({neuPct}%)</span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400">NU (Bengali neutral)</p>
          </div>

          {/* Card 4: Negative */}
          <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs font-semibold text-rose-600 dark:text-rose-400 uppercase tracking-wider">Negative Sentiment</p>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-extrabold text-rose-600 dark:text-rose-400">{negCount}</span>
              <span className="text-xs font-semibold text-slate-400">({negPct}%)</span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400">SN / WN / NEGATIVE</p>
          </div>
        </div>

        {/* 1. Interactive Live Sentiment Tester Widget */}
        <SentimentTester token={token} onAnalysisComplete={handleRefreshAll} />

        {/* 2. Visual Analytics Section (2-Column Grid) */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Polarity Trend Chart */}
          <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="border-b border-slate-100 bg-slate-50/60 px-5 py-3.5 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    📈 Sentiment Polarity Trend Over Time
                  </h3>
                  <p className="text-[11px] text-slate-500">Daily breakdown: Positive vs Neutral vs Negative</p>
                </div>
              </div>
            </div>
            <div className="p-4">
              <SentimentTrendChart data={trend ?? []} />
            </div>
          </div>

          {/* 5-Class Label Distribution Chart */}
          <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="border-b border-slate-100 bg-slate-50/60 px-5 py-3.5 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    📊 Fine-Grained Label Distribution
                  </h3>
                  <p className="text-[11px] text-slate-500">BanglaBERT 5-class breakdown (SN, WN, NU, WP, SP)</p>
                </div>
              </div>
            </div>
            <div className="p-4">
              <LabelDistributionChart distribution={distribution} />
            </div>
          </div>
        </div>

        {/* 3. Feedback Stream Section */}
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                Customer Feedback Records
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Live stream of intake submissions processed by background workers.
              </p>
            </div>
          </div>

          <Filters value={filters} onChange={handleFiltersChange} />

          {isFeedbackLoading && !data ? (
            <div className="flex h-48 items-center justify-center rounded-2xl border border-slate-200/80 bg-white p-6 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center gap-2">
                <svg className="h-4 w-4 animate-spin text-emerald-600" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                </svg>
                <span>Loading feedback items...</span>
              </div>
            </div>
          ) : data ? (
            <div className="space-y-4">
              <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
                <FeedbackTable items={data.items} />
              </div>
              <Pagination
                page={data.page}
                pageSize={data.page_size}
                total={data.total}
                onPageChange={setPage}
              />
            </div>
          ) : null}
        </div>
      </div>
    </main>
  );
}

