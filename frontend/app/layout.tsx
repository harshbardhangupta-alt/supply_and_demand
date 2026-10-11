import "./globals.css";
import type { Metadata } from "next";
import Shell from "@/components/Shell";

export const metadata: Metadata = {
  title: "Institutional S&D / SMC Terminal",
  description:
    "Multi-market institutional Supply & Demand (SMC) automated trading terminal",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-bg text-txt antialiased">
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
