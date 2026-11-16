import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Naukri Radar Pro - Latest Sarkari Jobs",
  description: "Find latest government jobs, results, and admit cards in one place.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-gray-50">
        {children}
      </body>
    </html>
  );
}