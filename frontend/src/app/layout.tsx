import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "./ThemeContext";
import { SessionProvider } from "./SessionContext";
import "./globals.css";
// Import DevToolsWrapper which handles the dynamic loading
import DevToolsWrapper from "./components/DevToolsWrapper";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Telegram Dialog Processor",
  description: "Process and manage your Telegram conversations",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased
          bg-gray-50 text-gray-900 transition-colors duration-200
          dark:bg-gray-900 dark:text-gray-100`}
      >
        <SessionProvider>
          <ThemeProvider>
            {children}
            {/* Add DevToolsWrapper - it will only show in development mode */}
            <DevToolsWrapper />
          </ThemeProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
