"use client";

import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import type { TweetWithNews, TweetStatus } from "@/lib/api";

const STATUS_STYLES: Record<TweetStatus, { pill: string; label: string; dot: string }> = {
    draft: { pill: "bg-slate-600/50 text-slate-300", label: "Borrador", dot: "bg-slate-400" },
    scheduled: { pill: "bg-amber-500/20 text-amber-300", label: "Programado", dot: "bg-amber-400" },
    posted: { pill: "bg-emerald-500/20 text-emerald-300", label: "Publicado", dot: "bg-emerald-400" },
    failed: { pill: "bg-red-500/20 text-red-300", label: "Error", dot: "bg-red-400" },
};

interface Props {
    tweet: TweetWithNews;
}

export default function TweetCard({ tweet }: Props) {
    const style = STATUS_STYLES[tweet.status];
    const scheduledAt = tweet.scheduled_at
        ? format(parseISO(tweet.scheduled_at), "HH:mm", { locale: es })
        : null;
    const postedAt = tweet.posted_at
        ? format(parseISO(tweet.posted_at), "HH:mm", { locale: es })
        : null;

    return (
        <div
            className={`rounded-xl border p-4 flex flex-col gap-3 transition-all ${tweet.status === "posted"
                    ? "border-emerald-500/30 bg-emerald-950/20"
                    : tweet.status === "failed"
                        ? "border-red-500/30 bg-red-950/20"
                        : tweet.status === "scheduled"
                            ? "border-amber-500/20 bg-slate-800/60"
                            : "border-slate-700 bg-slate-800/40"
                }`}
        >
            {/* Header: news title + status */}
            <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                    {tweet.news && (
                        <a
                            href={tweet.news.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-slate-400 hover:text-sky-400 transition-colors font-medium line-clamp-1"
                        >
                            {tweet.news.title}
                        </a>
                    )}
                </div>
                <span className={`flex-shrink-0 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold ${style.pill}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
                    {style.label}
                    {scheduledAt && tweet.status === "scheduled" && (
                        <span className="text-amber-400/70">· {scheduledAt}</span>
                    )}
                    {postedAt && tweet.status === "posted" && (
                        <span className="text-emerald-400/70">· {postedAt}</span>
                    )}
                </span>
            </div>

            {/* Tweet thread preview */}
            <div className="flex flex-col gap-2">
                {tweet.content.map((text, i) => (
                    <div key={i} className="flex gap-2">
                        {/* Thread line indicator */}
                        <div className="flex flex-col items-center flex-shrink-0">
                            <div className="w-6 h-6 rounded-full bg-sky-500/20 border border-sky-500/40 flex items-center justify-center">
                                <span className="text-[9px] text-sky-400 font-bold">{i + 1}</span>
                            </div>
                            {i < tweet.content.length - 1 && (
                                <div className="w-px flex-1 bg-slate-700 mt-1 mb-0 min-h-[8px]" />
                            )}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap break-words">
                                {text}
                            </p>
                            <p className="text-[10px] text-slate-500 mt-0.5 text-right">
                                {text.length}/280
                                {text.length > 280 && (
                                    <span className="text-red-400 font-semibold"> ⚠ muy largo</span>
                                )}
                            </p>
                        </div>
                    </div>
                ))}
            </div>

            {/* Error message */}
            {tweet.status === "failed" && tweet.error_msg && (
                <p className="text-[10px] text-red-400 bg-red-950/40 rounded-lg px-3 py-2 font-mono break-all">
                    {tweet.error_msg}
                </p>
            )}

            {/* Posted link */}
            {tweet.status === "posted" && tweet.x_tweet_id && (
                <a
                    href={`https://x.com/i/web/status/${tweet.x_tweet_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] text-sky-400 hover:text-sky-300 transition-colors self-end"
                >
                    Ver en X ↗
                </a>
            )}
        </div>
    );
}
