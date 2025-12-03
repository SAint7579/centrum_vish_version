import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Centrum - Your Digital Twin",
  description: "Create your AI-powered dating profile with voice cloning",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}

