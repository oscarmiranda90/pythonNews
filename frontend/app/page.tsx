import KanbanBoard from "@/components/KanbanBoard";

export const dynamic = "force-dynamic";

export default function Home() {
    return (
        <main className="min-h-screen bg-slate-900">
            {/* Top bar */}
            <header className="sticky top-0 z-40 bg-slate-900/90 backdrop-blur border-b border-slate-800 px-6 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <span className="text-xl font-bold text-white tracking-tight">
                        {process.env.NEXT_PUBLIC_SITE_NAME || "News Pipeline"}
                    </span>
                    <span className="text-slate-500 text-sm font-medium">Dashboard</span>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-500">
                        Últ. 7 días · Aprueba las noticias que quieres tuitear
                    </span>
                    <a
                        href="/tweets"
                        className="text-xs text-sky-400 hover:text-sky-300 transition-colors font-medium"
                    >
                        🐦 Ver tweets →
                    </a>
                    {process.env.NEXT_PUBLIC_DASHBOARD_URL && (
                        <a
                            href={process.env.NEXT_PUBLIC_DASHBOARD_URL}
                            className="text-xs text-sky-400 hover:text-sky-300 transition-colors"
                        >
                            {process.env.NEXT_PUBLIC_DASHBOARD_URL.replace(/^https?:\/\//, "")} ↗
                        </a>
                    )}
                </div>
            </header>

            {/* Board */}
            <section className="pt-4">
                <KanbanBoard />
            </section>
        </main>
    );
}
