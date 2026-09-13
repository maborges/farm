import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "DeepFarms",
    short_name: "DeepFarms",
    description: "Gestão integrada da operação rural",
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#f8faf9",
    theme_color: "#D97757",
    icons: [{ src: "/logos/deepfarms-mark.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
  };
}
