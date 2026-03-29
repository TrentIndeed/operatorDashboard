import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Operator Dashboard",
  description: "AI-powered solo founder command center",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased dark`}
      suppressHydrationWarning
    >
      <head>
        <meta name="darkreader-lock" />
        <meta name="color-scheme" content="dark" />
      </head>
      <body className="min-h-full bg-background text-foreground flex" suppressHydrationWarning>
        <Sidebar />
        <main className="flex-1 ml-60 min-h-screen overflow-y-auto">
          {children}
        </main>
      </body>
    </html>
  );
}
