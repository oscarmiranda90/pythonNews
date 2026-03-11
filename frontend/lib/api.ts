// lib/api.ts — typed fetch wrappers for the FastAPI backend

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type NewsStatus = "pending" | "approved" | "rejected" | "tweeted";
export type TweetStatus = "draft" | "scheduled" | "posted" | "failed";
export type Category = "ai" | "github" | "latam" | "saas" | "general";

export interface NewsItem {
    id: string;
    date: string;
    title: string;
    url: string;
    source: string;
    category: Category;
    summary: string | null;
    image_url: string | null;
    status: NewsStatus;
    created_at: string;
    approved_at: string | null;
}

export interface Tweet {
    id: string;
    news_id: string;
    content: string[];
    scheduled_at: string | null;
    posted_at: string | null;
    x_tweet_id: string | null;
    x_thread_ids: string[] | null;
    status: TweetStatus;
    error_msg: string | null;
    created_at: string;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
        ...init,
        headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`API ${path} → ${res.status}: ${text}`);
    }
    return res.json() as Promise<T>;
}

// ── News ──────────────────────────────────────────────────────────────────────

export function fetchNewsByDate(date: string): Promise<NewsItem[]> {
    return apiFetch<NewsItem[]>(`/api/news?date=${date}`);
}

export function fetchApprovedNews(date: string): Promise<NewsItem[]> {
    return apiFetch<NewsItem[]>(`/api/news/approved?date=${date}`);
}

export function updateNewsStatus(id: string, status: NewsStatus): Promise<NewsItem> {
    return apiFetch<NewsItem>(`/api/news/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
    });
}

// ── Tweets ────────────────────────────────────────────────────────────────────

export function fetchTweetsByDate(date: string): Promise<Tweet[]> {
    return apiFetch<Tweet[]>(`/api/tweets?date=${date}`);
}

// ── Scrape status ─────────────────────────────────────────────────────────────

export interface ScrapeError {
    source: string;
    url: string;
    error: string;
}

export interface ScrapeStatus {
    scraped_at: string;
    duration_s: number;
    count: number;
    errors: ScrapeError[];
}

export async function fetchScrapeStatus(date: string): Promise<ScrapeStatus | null> {
    try {
        const res = await fetch(`${BASE}/api/scrape-status?date=${date}`);
        if (!res.ok || res.status === 404) return null;
        const data = await res.json();
        return data ?? null;
    } catch {
        return null;
    }
}

/** Tweet enriched with its parent news item (joined client-side). */
export interface TweetWithNews extends Tweet {
    news?: NewsItem;
}

export async function fetchTweetsWithNews(date: string): Promise<TweetWithNews[]> {
    const [tweets, news] = await Promise.all([
        fetchTweetsByDate(date),
        fetchNewsByDate(date),
    ]);
    const newsMap = Object.fromEntries(news.map((n) => [n.id, n]));
    return tweets.map((t) => ({ ...t, news: newsMap[t.news_id] }));
}
