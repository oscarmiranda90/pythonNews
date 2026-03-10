"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { subDays, format } from "date-fns";
import type { NewsItem, NewsStatus } from "@/lib/api";
import { fetchNewsByDate } from "@/lib/api";
import DayColumn from "./DayColumn";

const DAYS_TO_SHOW = 7;

function getLast7Days(): string[] {
    return Array.from({ length: DAYS_TO_SHOW }, (_, i) =>
        format(subDays(new Date(), i), "yyyy-MM-dd")
    );
}

type DayMap = Record<string, NewsItem[]>;

export default function KanbanBoard() {
    const dates = getLast7Days();
    const [newsMap, setNewsMap] = useState<DayMap>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [generatingDate, setGeneratingDate] = useState<string | null>(null);
    const [toast, setToast] = useState<{ msg: string; type: "ok" | "err" } | null>(null);
    const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    function showToast(msg: string, type: "ok" | "err" = "ok") {
        if (toastTimer.current) clearTimeout(toastTimer.current);
        setToast({ msg, type });
        toastTimer.current = setTimeout(() => setToast(null), 4000);
    }

    // Fetch all 7 days in parallel
    useEffect(() => {
        setLoading(true);
        Promise.allSettled(dates.map((d) => fetchNewsByDate(d))).then((results) => {
            const map: DayMap = {};
            results.forEach((res, i) => {
                map[dates[i]] = res.status === "fulfilled" ? res.value : [];
            });
            setNewsMap(map);
            setLoading(false);
        });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleStatusChange = useCallback((id: string, status: NewsStatus) => {
        setNewsMap((prev) => {
            const next = { ...prev };
            for (const date of Object.keys(next)) {
                next[date] = next[date].map((item) =>
                    item.id === id ? { ...item, status } : item
                );
            }
            return next;
        });
    }, []);

    async function handleGenerateTweets(date: string, approvedItems: NewsItem[]) {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        setGeneratingDate(date);
        try {
            const res = await fetch(`${apiUrl}/api/generate-tweets`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    date,
                    news: approvedItems.map((i) => ({
                        id: i.id,
                        title: i.title,
                        url: i.url,
                        summary: i.summary ?? null,
                        category: i.category ?? null,
                    })),
                }),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail ?? `HTTP ${res.status}`);
            }
            showToast(`✓ OpenClaw generando tweets para ${approvedItems.length} noticias`);
        } catch (e) {
            showToast(`Error: ${e}`, "err");
        } finally {
            setGeneratingDate(null);
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64 text-slate-400 text-sm animate-pulse">
                Cargando noticias…
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-64 text-red-400 text-sm">
                {error}
            </div>
        );
    }

    return (
        <div className="relative">
            {/* Toast */}
            {toast && (
                <div
                    className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-xl text-sm font-semibold transition-all ${toast.type === "ok"
                        ? "bg-emerald-600 text-white"
                        : "bg-red-600 text-white"
                        }`}
                >
                    {toast.msg}
                </div>
            )}

            {/* Horizontal scroll container */}
            <div className="flex gap-4 overflow-x-auto pb-4 px-4">
                {dates.map((date) => (
                    <DayColumn
                        key={date}
                        date={date}
                        items={newsMap[date] ?? []}
                        onStatusChange={handleStatusChange}
                        onGenerateTweets={handleGenerateTweets}
                        generatingTweets={generatingDate === date}
                    />
                ))}
            </div>
        </div>
    );
}
