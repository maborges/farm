import { SafraContextHeader } from "@/components/agricola/safra-context-header";

export default async function SafraLayout({
    children,
    params,
}: {
    children: React.ReactNode;
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;

    return (
        <div className="flex flex-1 flex-col">
            <SafraContextHeader safraId={id} />
            <div className="flex-1">{children}</div>
        </div>
    );
}
