import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FabriGuard Industrial AI",
  description: "Real-time industrial defect detection and manufacturing quality monitoring.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
