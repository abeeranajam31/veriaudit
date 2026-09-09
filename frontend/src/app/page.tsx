import { Hero } from "@/components/landing/Hero";
import { Problem } from "@/components/landing/Problem";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { MetricSection } from "@/components/landing/MetricSection";
import { PricingTeaser } from "@/components/landing/PricingTeaser";
import { Roadmap } from "@/components/landing/Roadmap";
import { FounderTeaser } from "@/components/landing/FounderTeaser";
import { FinalCta } from "@/components/landing/FinalCta";

export default function Home() {
  return (
    <>
      <Hero />
      <Problem />
      <HowItWorks />
      <MetricSection />
      <PricingTeaser />
      <Roadmap />
      <FounderTeaser />
      <FinalCta />
    </>
  );
}
