import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Xperi RevGuard",
  icons: {
    icon: "/revguard-logo.png",
    shortcut: "/revguard-.svg",
    apple: "/revguard-logo.png",
  },
  description:
    "Xperi RevGuard — campaign revenue protection: detect, diagnose, quantify, recommend, act, measure.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} tabular-nums`}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
