"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import type { FeedbackItem } from "@/lib/types";

interface SentimentTesterProps {
  token: string | null;
  onAnalysisComplete?: () => void;
}

const SAMPLE_REVIEWS = [
  {
    label: "🇧🇩 Strong Positive",
    text: "পণ্যটির কোয়ালিটি অনেক ভালো এবং কাস্টমার সার্ভিস অসাধারণ!",
  },
  {
    label: "🇧🇩 Strong Negative",
    text: "একদম বাজে অভিজ্ঞতা, প্যাকেজিং ছেঁড়া ছিল এবং পণ্য কাজ করছে না।",
  },
  {
    label: "🇧🇩 Neutral / Mixed",
    text: "প্রোডাক্ট মোটামুটি ভালো, তবে ডেলিভারি একটু লেইট হয়েছে।",
  },
  {
    label: "🇬🇧 English Positive",
    text: "Outstanding build quality and blazingly fast delivery!",
  },
  {
    label: "🇬🇧 English Negative",
    text: "Disappointing customer service, broke within two days.",
  },
];

const LABEL_DESCRIPTIONS: Record<string, { title: string; color: string; desc: string }> = {
  SP: {
    title: "Strongly Positive",
    color: "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800",
    desc: "গাঢ় ইতিবাচক (High praise/satisfaction)",
  },
  WP: {
    title: "Weakly Positive",
    color: "bg-teal-100 text-teal-800 border-teal-300 dark:bg-teal-950 dark:text-teal-300 dark:border-teal-800",
    desc: "হালকা ইতিবাচক (Slightly positive)",
  },
  NU: {
    title: "Neutral",
    color: "bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
    desc: "নিরপেক্ষ (Factual or neutral)",
  },
  WN: {
    title: "Weakly Negative",
    color: "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800",
    desc: "হালকা নেতিবাচক (Minor complaint/defect)",
  },
  SN: {
    title: "Strongly Negative",
    color: "bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950 dark:text-rose-300 dark:border-rose-800",
    desc: "গাঢ় নেতিবাচক (Severe dissatisfaction)",
  },
  POSITIVE: {
    title: "Positive",
    color: "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800",
    desc: "English Positive",
  },
  NEGATIVE: {
    title: "Negative",
    color: "bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950 dark:text-rose-300 dark:border-rose-800",
    desc: "English Negative",
  },
};

export function SentimentTester({ token, onAnalysisComplete }: SentimentTesterProps) {
  const [text, setText] = useState("");
  const [selectedEngine, setSelectedEngine] = useState<"auto" | "bangla" | "distilbert">("auto");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<FeedbackItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze(submitText?: string, engineOverride?: "auto" | "bangla" | "distilbert") {
    const textToAnalyze = (submitText ?? text).trim();
    if (!textToAnalyze) return;

    const engineToUse = engineOverride ?? selectedEngine;

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      // 1. Submit review to intake API
      const submitted = await apiFetch<FeedbackItem>("/api/v1/feedback", {
        method: "POST",
        body: JSON.stringify({
          user_id: "dashboard-tester",
          text: textToAnalyze,
          model_override: engineToUse === "auto" ? null : engineToUse,
        }),
      });

      // 2. Poll briefly (worker processes in < 250ms)
      let processedItem = submitted;
      for (let attempt = 0; attempt < 8; attempt++) {
        if (processedItem.status === "processed" || processedItem.status === "failed") {
          break;
        }
        await new Promise((r) => setTimeout(r, 300));
        if (token) {
          try {
            processedItem = await apiFetch<FeedbackItem>(
              `/api/v1/feedback/${submitted.id}`,
              {},
              token
            );
          } catch {
            // ignore interim polling error
          }
        }
      }

      setResult(processedItem);
      if (onAnalysisComplete) {
        onAnalysisComplete();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze sentiment.");
    } finally {
      setIsLoading(false);
    }
  }

  const isBangla = result?.model_id?.includes("bangla") || false;

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm transition dark:border-slate-800 dark:bg-slate-900">
      {/* Header */}
      <div className="border-b border-slate-100 bg-gradient-to-r from-emerald-500/5 via-teal-500/5 to-indigo-500/5 px-6 py-4 dark:border-slate-800">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              🧪 Live Sentiment Tester &amp; Review Sandbox
            </h2>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Type or paste Bengali or English text to test real-time model classification &amp; probability distribution.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="model-select" className="text-xs font-semibold text-slate-600 dark:text-slate-300">
              Judge Model:
            </label>
            <select
              id="model-select"
              value={selectedEngine}
              onChange={(e) => setSelectedEngine(e.target.value as "auto" | "bangla" | "distilbert")}
              className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 shadow-sm transition hover:border-emerald-500 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="auto">⚡ Auto (Script Detect: BN → BanglaBERT, EN → DistilBERT)</option>
              <option value="bangla">🇧🇩 BanglaBERT (5-Class SentiGOLD)</option>
              <option value="distilbert">🇬🇧 DistilBERT (2-Class English SST-2)</option>
            </select>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-4">
        {/* Sample chips */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Quick Examples (Click to test):
          </label>
          <div className="flex flex-wrap gap-2">
            {SAMPLE_REVIEWS.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setText(sample.text);
                  handleAnalyze(sample.text);
                }}
                className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700 transition hover:border-emerald-400 hover:bg-emerald-50/50 hover:text-emerald-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-emerald-500 dark:hover:bg-emerald-950/50"
              >
                {sample.label}
              </button>
            ))}
          </div>
        </div>

        {/* Input box */}
        <div className="space-y-2">
          <div className="relative">
            <textarea
              rows={3}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="পণ্যটি সম্পর্কে আপনার রিভিউ লিখুন... (Type a customer review in Bengali or English)"
              className="w-full rounded-xl border border-slate-200 bg-slate-50/50 p-3.5 text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-emerald-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-800 dark:bg-slate-950 dark:text-white dark:focus:border-emerald-400"
            />
            {text && (
              <button
                type="button"
                onClick={() => setText("")}
                className="absolute right-3 top-3 rounded-md text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                Clear
              </button>
            )}
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">
              {text.length} characters
            </span>
            <button
              type="button"
              disabled={isLoading || !text.trim()}
              onClick={() => handleAnalyze()}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-5 py-2 text-sm font-semibold text-white shadow-md shadow-emerald-600/20 transition hover:from-emerald-500 hover:to-teal-500 active:scale-[0.99] disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <svg className="h-4 w-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                  </svg>
                  <span>Processing with ML Worker...</span>
                </>
              ) : (
                <>
                  <span>✨ Analyze Sentiment</span>
                </>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-900/50 dark:bg-red-950/50 dark:text-red-300">
            {error}
          </div>
        )}

        {/* Real-time Analysis Result Card */}
        {result && (
          <div className="mt-4 rounded-xl border border-slate-200/80 bg-slate-50/70 p-4 transition-all dark:border-slate-800 dark:bg-slate-950/70">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/60 pb-3 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Prediction Result
                </span>
                <span className="rounded-md bg-slate-200/80 px-2 py-0.5 text-[10px] font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                  {isBangla ? "🇧🇩 BanglaBERT (SentiGOLD)" : "🇬🇧 DistilBERT (SST-2)"}
                </span>
                {result.model_revision && (
                  <span className="text-[10px] text-slate-400">
                    rev: {result.model_revision.slice(0, 7)}
                  </span>
                )}
              </div>

              {/* Status Indicator */}
              <span className={`inline-flex items-center gap-1 text-[11px] font-semibold ${
                result.status === "processed" ? "text-emerald-600 dark:text-emerald-400" : "text-amber-500"
              }`}>
                ● {result.status.toUpperCase()}
              </span>
            </div>

            {/* Badges Grid */}
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
              {/* Fine Label */}
              <div className="rounded-lg bg-white p-3 shadow-sm border border-slate-200/70 dark:bg-slate-900 dark:border-slate-800">
                <p className="text-[11px] font-medium text-slate-400">Class Label</p>
                <div className="mt-1 flex items-center gap-2">
                  <span
                    className={`inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-bold ${
                      LABEL_DESCRIPTIONS[result.sentiment_label ?? ""]?.color ??
                      "bg-slate-100 text-slate-700 border-slate-300"
                    }`}
                  >
                    {result.sentiment_label ?? "N/A"}
                  </span>
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                    {LABEL_DESCRIPTIONS[result.sentiment_label ?? ""]?.title}
                  </span>
                </div>
                <p className="mt-1 text-[10px] text-slate-500">
                  {LABEL_DESCRIPTIONS[result.sentiment_label ?? ""]?.desc}
                </p>
              </div>

              {/* Coarse Polarity */}
              <div className="rounded-lg bg-white p-3 shadow-sm border border-slate-200/70 dark:bg-slate-900 dark:border-slate-800">
                <p className="text-[11px] font-medium text-slate-400">Coarse Polarity</p>
                <p className="mt-1 text-sm font-bold capitalize text-slate-800 dark:text-slate-100">
                  {result.sentiment_polarity ?? (result.sentiment_label?.toLowerCase() ?? "N/A")}
                </p>
                <p className="mt-1 text-[10px] text-slate-500">
                  Derivation: {result.sentiment_polarity === "negative" ? "Alert eligible" : "Normal stream"}
                </p>
              </div>

              {/* Confidence */}
              <div className="rounded-lg bg-white p-3 shadow-sm border border-slate-200/70 dark:bg-slate-900 dark:border-slate-800">
                <p className="text-[11px] font-medium text-slate-400">Model Confidence</p>
                <p className="mt-1 text-sm font-bold text-emerald-600 dark:text-emerald-400">
                  {result.confidence != null
                    ? `${(result.confidence * 100).toFixed(1)}%`
                    : result.sentiment_score != null
                      ? `${(result.sentiment_score * 100).toFixed(1)}%`
                      : "N/A"}
                </p>
                <p className="mt-1 text-[10px] text-slate-500">Softmax maximum probability</p>
              </div>
            </div>

            {/* Probability Breakdown Distribution */}
            {result.probabilities && Object.keys(result.probabilities).length > 0 && (
              <div className="mt-4 rounded-lg bg-white p-3.5 shadow-sm border border-slate-200/70 dark:bg-slate-900 dark:border-slate-800">
                <p className="mb-2.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Softmax Probability Distribution Across All Classes:
                </p>
                <div className="space-y-2">
                  {Object.entries(result.probabilities).map(([cls, prob]) => {
                    const numVal = typeof prob === "number" ? prob : Number(prob);
                    const pct = (numVal * 100).toFixed(1);
                    const isTop = cls === result.sentiment_label;
                    return (
                      <div key={cls} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className={`font-semibold ${isTop ? "text-emerald-600 dark:text-emerald-400" : "text-slate-600 dark:text-slate-300"}`}>
                            {cls} ({LABEL_DESCRIPTIONS[cls]?.title ?? cls})
                          </span>
                          <span className="font-mono text-slate-500">{pct}%</span>
                        </div>
                        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${
                              isTop
                                ? "bg-gradient-to-r from-emerald-500 to-teal-500"
                                : "bg-slate-300 dark:bg-slate-700"
                            }`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
