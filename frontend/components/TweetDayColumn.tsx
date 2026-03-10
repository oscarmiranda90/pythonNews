"use client";

import { format, parseISO, isToday } from "date-fns";
import { es } from "date-fns/locale";
import type { TweetWithNews } from "@/lib/api";
import TweetCard from "./TweetCard";

interface Props {
    date: string;
    tweets: TweetWithNews[];
}

export default function TweetDayColumn({ date, tweets }: Props) {
    const parsedDate = parseISO(date);
    const isCurrentDay = isToday(parsedDate);
    const dayLabel = isCurrentDay
        ? "Hoy"
        : format(parsedDate, "EEE d MMM", { locale: es });

    const posted = tweets.filter((t) => t.status === "posted");
    const scheduled = tweets.filter((t) => t.status === "scheduled");
    const failed = tweets.filter((t) => t.status === "failed");
    const draft = tweets.filter((t) => t.status === "draft");

    // Display order: scheduled → draft → posted → failed
    const ordered = [...scheduled, ...draft, ...posted, ...failed];

    return (
        <div
            className={`flex-shrink-0 w-80 flex flex-col rounded-2xl border ${isCurrentDay
                    ? "border-sky-500/60 bg-slate-800/80"
                    : "border-slate-700 bg-slate-800/40"
                }`}
        >
            {/* Column header */}
            <div className="px-4 pt-4 pb-3 border-b border-slate-700">
                <div className="flex items-center justify-between">
                    <h2 className={`font-bold text-sm capitalize ${isCurrentDay ? "text-sky-400" : "text-slate-300"}`}>
                        {dayLabel}
                    </h2>
                    <span className="text-xs text-slate-500">{tweets.length} threads</span>
                </div>

                {/* Status summary pills */}
                <div className="flex gap-2 mt-2 flex-wrap">
                    {scheduled.length > 0 && (
                        <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 text-[10px] font-semibold">
                            ⏰ {scheduled.length} programados
                        </span>
                    )}
                    {posted.length > 0 && (
                        <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-semibold">
                            ✓ {posted.length} publicados
                        </span>
                    )}
                    {failed.length > 0 && (
                        <span className="px-2 py-0.5 rounded-full bg-red-500/20 text-red-300 text-[10px] font-semibold">
                            ✗ {failed.length} error
                        </span>
                    )}
                    {draft.length > 0 && (
                        <span className="px-2 py-0.5 rounded-full bg-slate-600/60 text-slate-400 text-[10px]">
                            {draft.length} borrador
                        </span>
                    )}
                    {tweets.length === 0 && (
                        <span className="text-slate-600 text-[10px]">Sin tweets para este día</span>
                    )}
                </div>
            </div>

            {/* Cards */}
            <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3 max-h-[calc(100vh-210px)]">
                {ordered.length === 0 ? (
                    <p className="text-slate-500 text-xs text-center py-8">
                        No hay tweets generados aún.<br />
                        <span className="text-slate-600">Aprueba noticias y presiona Generar tweets.</span>
                    </p>
                ) : (
                    ordered.map((tweet) => (
                        <TweetCard key={tweet.id} tweet={tweet} />
                    ))
                )}
            </div>
        </div>
    );
}
