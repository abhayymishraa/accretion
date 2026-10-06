import AddByAddress from "@/components/mcp/AddByAddress";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Add a service · Accretion" };

export default function Page() {
    return <AddByAddress />;
}
