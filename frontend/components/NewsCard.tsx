"use client";

import { useState } from "react";
import type { NewsItem, NewsStatus } from "@/lib/api";
import { updateNewsStatus } from "@/lib/api";
import CategoryBadge from "./CategoryBadge";

const STATUS_RING: Record<NewsStatus, string> = {
    pending: "border-slate-600",
    approved: "border-emerald-500",
    rejected: "border-red-600 opacity-50",
    tweeted: "border-sky-500",
};

interface Props {
    item: NewsItem;
    onStatusChange: (id: string, status: NewsStatus) => void;
}

export default function NewsCard({ item, onStatusChange }: Props) {
    const [loading, setLoading] = useState(false);

    async function changeStatus(status: NewsStatus) {
        setLoading(true);
        try {
            await updateNewsStatus(item.id, status);
            onStatusChange(item.id, status);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }

    const isRejected = item.status === "rejected";
    const isApproved = item.status === "approved";
    const isTweeted = item.status === "tweeted";

    return (
        <div
            className={`relative rounded-xl border-2 bg-slate-800 p-3 flex flex-col gap-2 transition-all duration-200 ${STATUS_RING[item.status]} ${isRejected ? "opacity-40" : ""}`}
        >
            {/* Header: source + category */}
            <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] text-slate-400 truncate">{item.source}</span>
                <CategoryBadge category={item.category} />
            </div>

            {/* Title */}
            <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-semibold text-slate-100 leading-snug hover:text-sky-400 transition-colors line-clamp-3"
            >
                {item.title}
            </a>

            {/* Summary */}
            {item.summary && (
                <p className="text-[12px] text-slate-400 leading-relaxed line-clamp-2">
                    {item.summary}
                </p>
            )}

            {/* Status badge for tweeted */}
            {isTweeted && (
                <span className="text-[11px] text-sky-400 font-semibold">✓ Tuiteado</span>
            )}

            {/* Action buttons */}
            {!isTweeted && (
                <div className="flex gap-2 mt-1">
                    {!isApproved ? (
                        <button
                            onClick={() => changeStatus("approved")}
                            disabled={loading}
                            className="flex-1 text-xs font-semibold py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 transition-colors"
                        >
                            ✓ Aprobar
                        </button>
                    ) : (
                        <button
                            onClick={() => changeStatus("pending")}
                            disabled={loading}
                            className="flex-1 text-xs font-semibold py-1 rounded-lg bg-slate-600 hover:bg-slate-500 disabled:opacity-40 transition-colors"
                        >
                            ↩ Deshacer
                        </button>
                    )}
                    {!isRejected ? (
                        <button
                            onClick={() => changeStatus("rejected")}
                            disabled={loading}
                            className="flex-1 text-xs font-semibold py-1 rounded-lg bg-red-700 hover:bg-red-600 disabled:opacity-40 transition-colors"
                        >
                            ✕ Rechazar
                        </button>
                    ) : (
                        <button
                            onClick={() => changeStatus("pending")}
                            disabled={loading}
                            className="flex-1 text-xs font-semibold py-1 rounded-lg bg-slate-600 hover:bg-slate-500 disabled:opacity-40 transition-colors"
                        >
                            ↩ Restaurar
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}
