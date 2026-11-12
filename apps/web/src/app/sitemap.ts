import type { MetadataRoute } from "next";

const baseUrl = "https://app.deepfarms.com.br";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: `${baseUrl}/`, changeFrequency: "weekly", priority: 1 },
    { url: `${baseUrl}/agro`, changeFrequency: "weekly", priority: 0.8 },
  ];
}
