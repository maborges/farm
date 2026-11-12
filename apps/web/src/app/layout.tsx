import type { Metadata, Viewport } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://app.deepfarms.com.br"),
  title: "DeepFarms | Gestão Rural",
  description: "Sistema Integrado de Gestão do Agronegócio",
  applicationName: "DeepFarms",
  robots: { index: true, follow: true },
  openGraph: {
    type: "website",
    locale: "pt_BR",
    siteName: "DeepFarms",
    title: "DeepFarms | Gestão Rural",
    description: "Sistema Integrado de Gestão do Agronegócio",
    url: "https://app.deepfarms.com.br/",
    images: [{ url: "/images/deepfarms-hero.webp", width: 1200, height: 630, alt: "DeepFarms — Gestão Rural Integrada" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "DeepFarms | Gestão Rural",
    description: "Sistema Integrado de Gestão do Agronegócio",
    images: ["/images/deepfarms-hero.webp"],
  },
  alternates: { canonical: "/" },
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "DeepFarms Gestão",
  },
};

export const viewport: Viewport = {
  themeColor: "#006B3D",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning className={`${outfit.variable} font-sans`}>
      <body
        className="antialiased bg-background text-foreground"
        suppressHydrationWarning
      >
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
