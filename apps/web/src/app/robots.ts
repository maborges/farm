import type { MetadataRoute } from "next";

const baseUrl = "https://app.deepfarms.com.br";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: "*", allow: ["/", "/agro", "/p/rastreabilidade/", "/public/passaportes/"], disallow: ["/dashboard/", "/api/", "/auth/", "/login", "/register", "/onboarding/", "/integracoes/"] },
    ],
    sitemap: `${baseUrl}/sitemap.xml`,
    host: baseUrl,
  };
}
