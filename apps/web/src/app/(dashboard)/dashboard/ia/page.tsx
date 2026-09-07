import React from "react";
import { IADashboardView } from "@/components/ia/ia-dashboard-view";

export default async function IADashboardPage(props: { searchParams?: Promise<{ safra_id?: string }> }) {
    const searchParams = props.searchParams ? await props.searchParams : {};
    const safraId = searchParams.safra_id || undefined;
    return <IADashboardView initialSafraId={safraId} />;
}
