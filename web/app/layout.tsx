import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Svitch — The AI Control Layer",
  description:
    "Switch between LLMs without losing context. Block every data leak. Cut AI costs 80%. Prove compliance on demand.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" style={{ background: "#FAFAF8" }}>
      <body>{children}</body>
    </html>
  );
}
