import "./globals.css";

export const metadata = {
  title: "Belgium Concert Ads",
  description: "Read-only status for the Belgium concert ad campaign"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
