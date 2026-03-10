"use client";

import { useEffect, useState } from "react";
import { subDays, format } from "date-fns";
import type { TweetWithNews } from "@/lib/api";
import { fetchTweetsWithNews } from "@/lib/api";
import TweetDayColumn from "./TweetDayColumn";

const DAYS_TO_SHOW = 7;

function getLast7Days(): string[] {
    return Array.from({ length: DAYS_TO_SHOW }, (_, i) =>
        format(subDays(new Date(), i), "yyyy-MM-dd")
    );
}

type DayMap = Record<string, TweetWithNews[]>;

export default function TweetBoard() {
    const dates = getLast7Days();
    const [tweetMap, setTweetMap] = useState<DayMap>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setLoading(true);
        Promise.allSettled(dates.map((d) => fetchTweetsWithNews(d))).then((results) => {
            const map: DayMap = {};
            results.forEach((res, i) => {
                map[dates[i]] = res.status === "fulfilled" ? res.value : [];
            });
            setTweetMap(map);
            setLoading(false);
        }).catch(() => {
            setError("Error cargando los tweets.");
            setLoading(false);
        });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    if (loading) {
        return (
            <div className="flex gap-4 overflow-x-auto pb-4 px-4">
                {dates.map((d) => (
                    <div
                        key={d}
                        className="flex-shrink-0 w-80 h-64 bg-slate-800/40 rounded-2xl border border-slate-700 animate-pulse"
                    />
                ))}
            </div>
        );
    }

    if (error) {
        return (
            <div className="px-4 py-12 text-center text-red-400 text-sm">{error}</div>
        );
    }

    return (
        <div className="flex gap-4 overflow-x-auto pb-4 px-4">
            {dates.map((date) => (
                <TweetDayColumn
                    key={date}
                    date={date}
                    tweets={tweetMap[date] ?? []}
                />
            ))}
        </div>
    );
}
