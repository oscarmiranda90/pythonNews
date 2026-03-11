"use client";

import { useState } from "react";
import { format, parseISO, isToday } from "date-fns";
import { es } from "date-fns/locale";
import type { NewsItem, NewsStatus, ScrapeStatus } from "@/lib/api";
import NewsCard from "./NewsCard";

interface Props {
    date: string;
    items: NewsItem[];
    onStatusChange: (id: string, status: NewsStatus) => void;
    onGenerateTweets: (date: string, approvedItems: NewsItem[]) => void;
    generatingTweets: boolean;
    scrapeStatus: ScrapeStatus | null;
}

export default function DayColumn({
    date,
    items,
    onStatusChange,
    onGenerateTweets,
    generatingTweets,
    scrapeStatus,
}: Props) {
    const [showErrors, setShowErrors] = useState(false);
    const parsedDate = parseISO(date);
    const isCurrentDay = isToday(parsedDate);
    const dayLabel = isCurrentDay
        ? "Hoy"
        : format(parsedDate, "EEE d MMM", { locale: es });

    const approved = items.filter((i) => i.status === "approved");
    const tweeted = items.filter((i) => i.status === "tweeted");
    const pending = items.filter((i) => i.status === "pending");
    const rejected = items.filter((i) => i.status === "rejected");

    const canGenerate = approved.length > 0;

    const scrapeTime = scrapeStatus
        ? format(parseISO(scrapeStatus.scraped_at), "HH:mm", { locale: es })
        : null;
    const hasErrors = (scrapeStatus?.errors?.length ?? 0) > 0;

    return (
        <>
            <div
                className={`flex-shrink-0 w-72 flex flex-col rounded-2xl border ${isCurrentDay ? "border-sky-500/60 bg-slate-800/80" : "border-slate-700 bg-slate-800/40"
                    }`}
            >
                {/* Column header */}
                <div className="px-4 pt-4 pb-3 border-b border-slate-700">
                    <div className="flex items-center justify-between">
                        <h2 className={`font-bold text-sm capitalize ${isCurrentDay ? "text-sky-400" : "text-slate-300"}`}>
                            {dayLabel}
                        </h2>
                        <div className="flex items-center gap-2 text-[11px]">
                            <span className="text-slate-500">{items.length} noticias</span>
                        </div>
                    </div>

                    {/* Scrape metadata row */}
                    {scrapeStatus ? (
                        <div className="flex items-center gap-2 mt-1.5">
                            <span className="text-[10px] text-slate-500">
                                ⚡ {scrapeTime} · {scrapeStatus.duration_s}s · {scrapeStatus.count} items
                            </span>
                            {hasErrors && (
                                <button
                                    onClick={() => setShowErrors(true)}
                                    className="text-[10px] text-red-400 hover:text-red-300 font-semibold transition-colors"
                                >
                                    ⚠ {scrapeStatus.errors.length} error{scrapeStatus.errors.length > 1 ? "es" : ""}
                                </button>
                            )}
                        </div>
                    ) : (
                        <div className="mt-1.5 text-[10px] text-slate-600">Sin scraping registrado</div>
                    )}

                    {/* Status summary pills */}
                    <div className="flex gap-2 mt-2 flex-wrap">
                        {approved.length > 0 && (
                            <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-semibold">
                                ✓ {approved.length} aprobadas
                            </span>
                        )}
                        {tweeted.length > 0 && (
                            <span className="px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-300 text-[10px] font-semibold">
                                🐦 {tweeted.length} tuiteadas
                            </span>
                        )}
                        {pending.length > 0 && (
                            <span className="px-2 py-0.5 rounded-full bg-slate-600/60 text-slate-400 text-[10px]">
                                {pending.length} pendientes
                            </span>
                        )}
                    </div>

                    {/* Generate Tweets button */}
                    <button
                        onClick={() => onGenerateTweets(date, approved)}
                        disabled={!canGenerate || generatingTweets}
                        className={`mt-3 w-full py-1.5 rounded-lg text-xs font-bold transition-all ${canGenerate
                            ? "bg-sky-600 hover:bg-sky-500 text-white"
                            : "bg-slate-700 text-slate-500 cursor-not-allowed"
                            } disabled:opacity-50`}
                    >
                        {generatingTweets ? "Generando…" : `🐦 Generar tweets (${approved.length})`}
                    </button>
                </div>

                {/* Cards */}
                <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3 max-h-[calc(100vh-220px)]">
                    {items.length === 0 ? (
                        <p className="text-slate-500 text-xs text-center py-8">Sin noticias para este día</p>
                    ) : (
                        <>
                            {[...approved, ...pending, ...tweeted, ...rejected].map((item) => (
                                <NewsCard key={item.id} item={item} onStatusChange={onStatusChange} />
                            ))}
                        </>
                    )}
                </div>
            </div>

            {/* Error modal */}
            {showErrors && scrapeStatus && (
                <div
                    className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
                    onClick={() => setShowErrors(false)}
                >
                    <div
                        className="bg-slate-800 border border-slate-600 rounded-2xl w-full max-w-lg max-h-[80vh] flex flex-col shadow-2xl"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
                            <h3 className="text-sm font-bold text-white">
                                Errores de scraping · {dayLabel}
                            </h3>
                            <button
                                onClick={() => setShowErrors(false)}
                                className="text-slate-400 hover:text-white text-lg leading-none"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="overflow-y-auto p-4 flex flex-col gap-3">
                            {scrapeStatus.errors.map((err, i) => (
                                <div key={i} className="bg-red-950/40 border border-red-500/20 rounded-xl p-3">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-xs font-semibold text-red-300">{err.source}</span>
                                        {err.url && (
                                            <a
                                                href={err.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-[10px] text-sky-400 hover:text-sky-300 truncate max-w-[200px]"
                                            >
                                                {err.url} ↗
                                            </a>
                                        )}
                                    </div>
                                    <p className="text-[11px] text-red-200 font-mono break-all">{err.error}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
