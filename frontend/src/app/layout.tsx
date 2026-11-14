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

const siteUrl = "https://veriiaudit.vercel.app";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "VeriAudit — Measuring Multilingual AI Safety Evaluation",
    template: "%s — VERIAUDIT",
  },
  description:
    "Independent research and an open-source framework on whether multilingual AI safety evaluations measure what they claim: refusal detection, denominator choices and language understanding across English, Urdu script, Roman Urdu and code-switching.",
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
    title: "VeriAudit — Measuring Multilingual AI Safety Evaluation",
    description:
      "When a model looks less safe in Urdu, is it unsafe, confused, or misjudged? Independent research with an open-source evaluation framework.",
    url: siteUrl,
    siteName: "VERIAUDIT",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "VeriAudit — Measuring Multilingual AI Safety Evaluation",
    description: "When a model looks less safe in Urdu, is it unsafe, confused, or misjudged?",
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
