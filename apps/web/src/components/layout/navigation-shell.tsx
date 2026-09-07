"use client";

import React, { useState, useEffect } from "react";
import { AppSidebar } from "./app-sidebar";
import { useNavigationPreference } from "@/hooks/use-navigation-preference";

export function NavigationShell() {
    const { mode } = useNavigationPreference();
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    // Fallback visual neutro: não renderiza a sidebar até que o client esteja montado 
    // para evitar o flash visual de 'Sidebar aparece -> desaparece e vira Mega Menu'.
    if (!mounted) {
        return null;
    }

    if (mode === "mega-menu") {
        // AppMegaMenu is rendered natively inside Topbar to preserve correct DOM structure and flex alignment.
        // Returning null here allows SidebarInset to occupy full width.
        return null;
    }

    // Default is Sidebar
    return <AppSidebar />;
}
