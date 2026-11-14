import type { MetadataRoute } from "next";

const siteUrl = "https://veriiaudit.vercel.app";

const routes = [
  "",
  "/results",
  "/research",
  "/methodology",
  "/benchmark",
  "/open-source",
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
