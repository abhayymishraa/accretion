import ChatWorkspace from "@/components/chat/ChatWorkspace";

// The page renders nothing that depends on the server, so each chat URL is rendered once on its
// first visit and then served from the CDN, not rendered for every request in another region.
export function generateStaticParams() {
    return [];
}

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    return <ChatWorkspace key={id} chatId={id} />;
}
