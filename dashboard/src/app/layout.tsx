import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { JarvisBackground } from "@/components/jarvis-background";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MALU // Multi-Bot Trading System",
  description: "J.A.R.V.I.S.-class multi-bot trading dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full bg-background text-foreground jarvis-grid hex-pattern" suppressHydrationWarning>
        <JarvisBackground />
        <div className="relative" style={{ zIndex: 1 }}>
          {children}
        </div>
      </body>
    </html>
  );
}
