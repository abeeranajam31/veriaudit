import type { Metadata } from "next";
import { PlatformDashboard } from "@/components/platform/PlatformDashboard";

export const metadata: Metadata = {
  title: "Platform",
  description:
    "Generate linguistic variants, run demo evaluations, and inspect the Cross-Lingual Safety Gap for VERIAUDIT pilot intents.",
};

export default function PlatformPage() {
  return <PlatformDashboard />;
}
