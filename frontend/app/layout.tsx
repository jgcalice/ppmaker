import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geist = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PPMaker — AI Presentation Builder",
  description:
    "Transforme texto em apresentações profissionais com inteligência artificial.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className="dark">
      <body className={`${geist.variable} font-sans antialiased noise-bg`}>
        <div className="relative z-10 min-h-screen">{children}</div>
      </body>
    </html>
  );
}
