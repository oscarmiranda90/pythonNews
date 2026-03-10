"use client";

import { useState } from "react";
import { format, parseISO, isToday } from "date-fns";
import { es } from "date-fns/locale";
import type { NewsItem, NewsStatus } from "@/lib/api";
import NewsCard from "./NewsCard";

interface Props {
    date: string; // YYYY-MM-DD
    items: NewsItem[];
    onStatusChange: (id: string, status: NewsStatus) => void;
    onGenerateTweets: (date: string, approvedItems: NewsItem[]) => void;
    generatingTweets: boolean;
}

export default function DayColumn({
    date,
    items,
    onStatusChange,
    onGenerateTweets,
    generatingTweets,
}: Props) {
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

    return (
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
                    <div className="flex gap-2 text-[11px]">
                        <span className="text-slate-500">{items.length} noticias</span>
                    </div>
                </div>
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
                        {/* Approved first, then pending, then rejected */}
                        {[...approved, ...pending, ...tweeted, ...rejected].map((item) => (
                            <NewsCard key={item.id} item={item} onStatusChange={onStatusChange} />
                        ))}
                    </>
                )}
            </div>
        </div>
    );
}
