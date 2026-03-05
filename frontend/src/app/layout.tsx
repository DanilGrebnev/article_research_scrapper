import type { Metadata } from "next";
import Link from "next/link";
import Providers from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Springer Scrapper",
  description: "Web scraper for SpringerLink articles",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body>
        <nav className="nav-bar">
          <div className="nav-bar__inner">
            <Link href="/" className="nav-bar__brand">Springer Scrapper</Link>
            <div className="nav-bar__links">
              <Link href="/" className="nav-bar__link">Скраппер</Link>
              <Link href="/history" className="nav-bar__link">История</Link>
            </div>
          </div>
        </nav>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
