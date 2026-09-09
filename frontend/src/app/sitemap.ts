import type { MetadataRoute } from "next";

const siteUrl = "https://veriaudit.vercel.app";

const routes = [
  "",
  "/platform",
  "/research",
  "/methodology",
  "/benchmark",
  "/leaderboard",
  "/open-source",
  "/pricing",
  "/about",
  "/contact",
];

export default function sitemap(): MetadataRoute.Sitemap {
  return routes.map((route) => ({
    url: `${siteUrl}${route}`,
    lastModified: new Date(),
    changeFrequency: "weekly",
    priority: route === "" ? 1 : 0.7,
  }));
}
