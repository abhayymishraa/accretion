import { ThemeProvider } from "@/components/layout/ThemeProvider";
import { Toaster } from "@/components/ui/sonner";
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

export const metadata: Metadata = {
    metadataBase: new URL(process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000"),
    title: "Accretion",
    description: "Build React applications with AI",
    icons: {
        icon: { url: "/brand/accretion-mark.svg", type: "image/svg+xml" },
    },
    openGraph: {
        title: "Accretion",
        description:
            "Build applications faster with AI-powered code generation and intelligent development assistance.",
        images: [
            {
                url: "/brand/accretion-social.png",
                width: 1774,
                height: 887,
                alt: "Accretion: blue orbit ring with a gathered core and one accreting body, beside the wordmark",
            },
        ],
        type: "website",
    },
    twitter: {
        card: "summary_large_image",
        title: "Accretion",
        description:
            "Build applications faster with AI-powered code generation and intelligent development assistance.",
        images: ["/brand/accretion-social.png"],
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
