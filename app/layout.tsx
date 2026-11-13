import type { Metadata, Viewport } from "next";
import Script from "next/script";
import "../styles/globals.css";
export const metadata: Metadata = { title: "CryptoNOVA", description: "Your Digital Assets. Your Universe. (Educational simulator)", icons: { icon: "/favicon.svg" } };
export const viewport: Viewport = { width: "device-width", initialScale: 1, maximumScale: 1, viewportFit: "cover" };
export default function Root({ children }: { children: React.ReactNode }) {
  return (<html lang="en"><body>
    <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
    {children}
  </body></html>);
}
