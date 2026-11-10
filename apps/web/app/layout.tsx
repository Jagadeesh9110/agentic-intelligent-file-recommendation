import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Intelligent File Recommendation",
  description: "Natural-language file discovery workspace",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
