import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { AppFrame } from "@/components/layout/AppFrame";
import { AuthProvider } from "@/context/AuthContext";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "BIS SAATHI — Indian Standards & Certification Assistant",
  description:
    "Agentic AI-powered assistant for Indian Standards, BIS certification, testing laboratories, hallmarking and consumer help.",
  icons: { icon: "/logo.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans">
        <AuthProvider>
          <AppFrame>{children}</AppFrame>
        </AuthProvider>
      </body>
    </html>
  );
}
