import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Atrium",
  description: "Quién entra a Iterum, Domi y Vocatio.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
