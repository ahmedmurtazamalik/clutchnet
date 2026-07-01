import type { Metadata } from "next";
import { Outfit, Inter, Barlow_Condensed } from "next/font/google";
import "./globals.css";

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const barlowCondensed = Barlow_Condensed({
  variable: "--font-barlow-condensed",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
});

export const metadata: Metadata = {
  title: "ClutchNet | Real-Time NBA Win Probability & Game State Engine",
  description: "Experience basketball state changes live. Powered by PyTorch ensemble neural models and high-performance WebSocket streaming to track play-by-play momentum shifts.",
  keywords: ["NBA", "Win Probability", "Basketball Analytics", "Live Sports Data", "PyTorch", "FastAPI", "Next.js"],
  authors: [{ name: "ClutchNet Team" }],
  openGraph: {
    title: "ClutchNet - Real-Time NBA Win Probability Engine",
    description: "Deep learning models analyzing live NBA match momentum under pressure.",
    type: "website",
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${outfit.variable} ${inter.variable} ${barlowCondensed.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-slate-950 text-slate-100 selection:bg-neon-blue/30 selection:text-white">
        {children}
      </body>
    </html>
  );
}
