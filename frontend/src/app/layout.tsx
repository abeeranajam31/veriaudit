import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const siteUrl = "https://veriaudit.vercel.app";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "VERIAUDIT — Cross-Lingual AI Safety Evaluation",
    template: "%s — VERIAUDIT",
  },
  description:
    "VERIAUDIT is an open-source platform for red-teaming and evaluating AI safety across languages, with an initial focus on Urdu, Roman Urdu, and code-switched language.",
  keywords: [
    "AI safety",
    "red-teaming",
    "cross-lingual evaluation",
    "LLM evaluation",
    "Urdu NLP",
    "AI governance",
    "jailbreak robustness",
  ],
  authors: [{ name: "Abeera Najam" }],
  openGraph: {
    title: "VERIAUDIT — Cross-Lingual AI Safety Evaluation",
    description:
      "An open-source red-teaming platform for cross-lingual AI safety evaluation. Does AI safety survive translation?",
    url: siteUrl,
    siteName: "VERIAUDIT",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "VERIAUDIT — Cross-Lingual AI Safety Evaluation",
    description: "Does AI safety survive translation?",
  },
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-bg text-ink">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:m-3 focus:rounded-md focus:bg-ink focus:px-4 focus:py-2 focus:text-bg"
        >
          Skip to content
        </a>
        <Nav />
        <main id="main-content" className="flex-1">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
