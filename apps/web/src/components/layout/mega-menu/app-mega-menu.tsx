"use client";

import React, { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import { AppWindow } from "lucide-react";
import { useVisibleNavigation } from "@/hooks/use-visible-navigation";
import { useIsMobile } from "@/hooks/use-mobile";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { MegaMenuDesktop } from "./mega-menu-desktop";
import { MegaMenuMobile } from "./mega-menu-mobile";

export function AppMegaMenu() {
    const [isOpen, setIsOpen] = useState(false);
    const pathname = usePathname();
    const isMobile = useIsMobile();
    const { moduleGroups, accessItems, settingsItems, searchParams, activeModule } = useVisibleNavigation();

    // Fecha o menu automaticamente quando a rota mudar
    useEffect(() => {
        setIsOpen(false);
    }, [pathname, searchParams]);
    
    const activeLabel = activeModule === "CADASTROS" ? "Cadastros" : moduleGroups.find(g => g.key === activeModule)?.label;

    // O gatilho do Menu (acessível)
    const Trigger = React.forwardRef<HTMLButtonElement, React.ComponentPropsWithoutRef<typeof Button>>((props, ref) => (
        <Button
            ref={ref}
            variant="ghost"
            size="icon-sm"
            className="text-primary"
            aria-expanded={isOpen}
            aria-controls="app-mega-menu-panel"
            aria-label="Abrir Mega Menu"
            {...props}
        >
            <AppWindow className="h-4 w-4" />
            <span className="sr-only">Abrir Mega Menu</span>
        </Button>
    ));
    Trigger.displayName = "Trigger";

    if (isMobile) {
        return (
            <Sheet open={isOpen} onOpenChange={setIsOpen}>
                <SheetTrigger asChild>
                    <Trigger />
                </SheetTrigger>
                <SheetContent side="left" className="w-[85vw] max-w-[320px] p-0 flex flex-col" id="app-mega-menu-panel">
                    <MegaMenuMobile moduleGroups={moduleGroups} accessItems={accessItems} settingsItems={settingsItems} pathname={pathname} searchParams={searchParams} onClose={() => setIsOpen(false)} />
                </SheetContent>
            </Sheet>
        );
    }

    return (
        <Popover open={isOpen} onOpenChange={setIsOpen}>
            <PopoverTrigger asChild>
                <Trigger />
            </PopoverTrigger>
            <PopoverContent 
                id="app-mega-menu-panel"
                className="w-[95vw] max-w-[1200px] p-0 shadow-lg border-muted overflow-hidden" 
                align="start" 
                sideOffset={8}
            >
                <MegaMenuDesktop moduleGroups={moduleGroups} accessItems={accessItems} settingsItems={settingsItems} pathname={pathname} searchParams={searchParams} onClose={() => setIsOpen(false)} />
            </PopoverContent>
        </Popover>
    );
}
