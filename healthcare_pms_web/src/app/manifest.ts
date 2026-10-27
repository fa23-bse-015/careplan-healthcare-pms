import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "CarePlan Healthcare Project Management",
    short_name: "CarePlan",
    description: "Project planning, control, and evidence for the five-hospital software case.",
    start_url: "/",
    display: "standalone",
    background_color: "#f4f7fb",
    theme_color: "#f4f7fb",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
