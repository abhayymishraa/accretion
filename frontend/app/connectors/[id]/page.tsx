import ServiceDetail from "@/components/mcp/ServiceDetail";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Connection · Accretion" };

// Every service's page is the same shell filled in the browser, so nothing renders per request.
export function generateStaticParams() {
    return [];
}

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    return <ServiceDetail key={id} id={id} />;
}
