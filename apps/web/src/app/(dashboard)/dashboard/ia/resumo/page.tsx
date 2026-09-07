import React from "react";
import { IAResumoView } from "@/components/ia/ia-resumo-view";

export default async function IAResumoPage(props: { searchParams?: Promise<{ safra_id?: string }> }) {
    const searchParams = props.searchParams ? await props.searchParams : {};
    const safraId = searchParams.safra_id || undefined;
    return <IAResumoView initialSafraId={safraId} />;
}
