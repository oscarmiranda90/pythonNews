import type { Category } from "@/lib/api";

const CONFIG: Record<Category, { label: string; classes: string }> = {
    ai: { label: "AI", classes: "bg-violet-500/20 text-violet-300 border border-violet-500/40" },
    github: { label: "GitHub", classes: "bg-slate-500/20 text-slate-300 border border-slate-500/40" },
    latam: { label: "LATAM", classes: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40" },
    saas: { label: "SaaS", classes: "bg-amber-500/20 text-amber-300 border border-amber-500/40" },
    general: { label: "Tech", classes: "bg-sky-500/20 text-sky-300 border border-sky-500/40" },
};

export default function CategoryBadge({ category }: { category: Category }) {
    const { label, classes } = CONFIG[category] ?? CONFIG.general;
    return (
        <span className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide ${classes}`}>
            {label}
        </span>
    );
}
