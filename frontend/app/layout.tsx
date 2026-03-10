import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "UltraMare News",
    description: "AI & Tech news dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="es" className={inter.className}>
            <body className="bg-slate-900 text-slate-100 min-h-screen">{children}</body>
        </html>
    );
}
