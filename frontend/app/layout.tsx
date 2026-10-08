import { ThemeProvider } from "@/components/layout/ThemeProvider";
import { Toaster } from "@/components/ui/sonner";
import { SITE_URL } from "@/config/env";
import type { Metadata } from "next";
import { DM_Sans, Open_Sans } from "next/font/google";
import "./globals.css";

const openSans = Open_Sans({
    subsets: ["latin"],
    display: "swap",
    variable: "--font-open-sans",
});

// Wordmark only. Body text stays on the theme's Open Sans.
const dmSans = DM_Sans({
    subsets: ["latin"],
    weight: ["600"],
    display: "swap",
    variable: "--font-dm-sans",
});

// What a pasted link shows: the landing hero's line, under the brand's name.
const SHARE_TITLE = "Accretion: every app begins as a sentence";
const DESCRIPTION =
    "Describe an app in plain words. Accretion plans it with you, then builds it with a real server and database.";

export const metadata: Metadata = {
    metadataBase: new URL(SITE_URL),
    title: "Accretion",
    description: DESCRIPTION,
    icons: {
        icon: { url: "/brand/accretion-mark.svg", type: "image/svg+xml" },
    },
    openGraph: {
        title: SHARE_TITLE,
        siteName: "Accretion",
        description: DESCRIPTION,
        images: [
            {
                url: "/brand/accretion-social.jpg",
                width: 1200,
                height: 630,
                alt: "Accretion. Every app begins as a sentence, over a meadow, with a prompt bar in Plan mode",
            },
        ],
        type: "website",
    },
    twitter: {
        card: "summary_large_image",
        title: SHARE_TITLE,
        description: DESCRIPTION,
        images: ["/brand/accretion-social.jpg"],
    },
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" data-theme="dark" className={`${openSans.variable} ${dmSans.variable}`}>
            <body className="font-sans antialiased">
                <ThemeProvider>
                    {children}
                    <Toaster />
                </ThemeProvider>
            </body>
        </html>
    );
}
