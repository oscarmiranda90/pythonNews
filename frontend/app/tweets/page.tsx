import TweetBoard from "@/components/TweetBoard";

export default function TweetsPage() {
    return (
        <main className="min-h-screen bg-slate-900">
            {/* Top bar */}
            <header className="sticky top-0 z-40 bg-slate-900/90 backdrop-blur border-b border-slate-800 px-6 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <a
                        href="/"
                        className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                    >
                        ← Kanban
                    </a>
                    <span className="text-slate-700">|</span>
                    <span className="text-xl font-bold text-white tracking-tight">
                        {process.env.NEXT_PUBLIC_SITE_NAME || "News Pipeline"}
                    </span>
                    <span className="text-slate-500 text-sm font-medium">Tweet Preview</span>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-500">
                        Últ. 7 días · Vista previa de threads generados
                    </span>
                </div>
            </header>

            {/* Board */}
            <section className="pt-4">
                <TweetBoard />
            </section>
        </main>
    );
}
