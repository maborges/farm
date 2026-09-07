import React, { useState } from "react";
import Link from "next/link";
import { Search, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { isItemActive } from "@/lib/sidebar-navigation";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { SheetHeader, SheetTitle } from "@/components/ui/sheet";
import type { SidebarModuleGroup, SidebarMenuItem } from "@/lib/sidebar-config";

function Highlight({ text, highlight }: { text: string; highlight: string }) {
    if (!highlight.trim()) return <>{text}</>;
    const regex = new RegExp(`(${highlight})`, "gi");
    const parts = text.split(regex);
    return (
        <>
            {parts.map((part, i) =>
                regex.test(part) ? <span key={i} className="bg-primary/20 text-primary font-medium rounded-sm px-0.5">{part}</span> : <span key={i}>{part}</span>
            )}
        </>
    );
}

interface MegaMenuMobileProps {
    moduleGroups: SidebarModuleGroup[];
    accessItems?: SidebarMenuItem[];
    settingsItems?: SidebarMenuItem[];
    pathname: string;
    searchParams: URLSearchParams;
    onClose: () => void;
}

export function MegaMenuMobile({ moduleGroups, accessItems = [], settingsItems = [], pathname, searchParams, onClose }: MegaMenuMobileProps) {
    const [search, setSearch] = useState("");

    const term = search.toLowerCase();

    const footerGroup: SidebarModuleGroup | null = (accessItems.length > 0 || settingsItems.length > 0) ? {
        key: "footer-conta",
        label: "Acessos e Configurações",
        icon: Settings,
        moduleId: "CORE",
        sections: [
            ...(accessItems.length > 0 ? [{ key: "footer-acessos", label: "Gestão de Acessos", icon: Settings, items: accessItems }] : []),
            ...(settingsItems.length > 0 ? [{ key: "footer-config", label: "Configurações", icon: Settings, items: settingsItems }] : []),
        ],
    } : null;

    const allGroups = footerGroup ? [...moduleGroups, footerGroup] : moduleGroups;

    const filteredGroups = allGroups.map(group => {
        const matchedSections = group.sections.map(sec => {
            const matchedItems = sec.items.filter(item => 
                item.label.toLowerCase().includes(term) || sec.label.toLowerCase().includes(term) || group.label.toLowerCase().includes(term)
            );
            return { ...sec, items: matchedItems };
        }).filter(sec => sec.items.length > 0);
        return { ...group, sections: matchedSections };
    }).filter(group => group.sections.length > 0);

    // Abre os accordions automaticamente se houver busca
    const accordionValue = search ? filteredGroups.map(g => g.key) : undefined;

    return (
        <>
            <SheetHeader className="p-4 border-b text-left">
                <SheetTitle className="text-lg">Menu</SheetTitle>
            </SheetHeader>
            <div className="p-4 border-b">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input 
                        placeholder="Buscar..." 
                        className="pl-9 h-9" 
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />
                </div>
            </div>
            <ScrollArea className="flex-1">
                {filteredGroups.length === 0 ? (
                    <div className="p-8 text-center text-sm text-muted-foreground">Nenhum resultado encontrado.</div>
                ) : (
                    <nav aria-label="Navegação Principal">
                        <Accordion 
                            type="multiple" 
                            className="w-full" 
                            defaultValue={accordionValue}
                            value={accordionValue} // Controlado temporariamente se houver busca, senão defaultValue cuida
                        >
                            {filteredGroups.map(group => {
                                const GroupIcon = group.icon;
                                return (
                                    <AccordionItem value={group.key} key={group.key} className="border-b-0">
                                        <AccordionTrigger className="px-4 py-3 hover:bg-muted/50 data-[state=open]:bg-muted/30">
                                            <div className="flex items-center gap-3 text-left">
                                                <GroupIcon className="h-5 w-5 text-primary" aria-hidden="true" />
                                                <span className="font-medium text-sm">{group.label}</span>
                                            </div>
                                        </AccordionTrigger>
                                        <AccordionContent className="pb-2 pt-0 px-4 bg-muted/10">
                                            <div className="flex flex-col gap-4 mt-3">
                                                {group.sections.map(section => (
                                                    <div key={section.key} className="flex flex-col gap-1.5">
                                                        <h4 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider pl-1" id={`m-section-${section.key}`}>
                                                            {section.label}
                                                        </h4>
                                                        <ul className="flex flex-col" aria-labelledby={`m-section-${section.key}`}>
                                                            {section.items.map(item => {
                                                                const isActive = isItemActive(item.href, pathname, searchParams);
                                                                const ItemIcon = item.icon;
                                                                return (
                                                                    <li key={item.href}>
                                                                        <Link 
                                                                            href={item.href}
                                                                            onClick={onClose}
                                                                            className={cn(
                                                                                "flex items-center gap-3 py-3 pl-2 pr-3 rounded-md text-sm transition-colors",
                                                                                isActive 
                                                                                    ? "bg-sidebar-accent text-primary font-semibold" 
                                                                                    : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                                                                            )}
                                                                            aria-current={isActive ? "page" : undefined}
                                                                        >
                                                                            {ItemIcon && <ItemIcon className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />}
                                                                            <span>
                                                                                <Highlight text={item.label} highlight={search} />
                                                                                {search && (
                                                                                    <span className="text-xs text-muted-foreground ml-2 opacity-60">
                                                                                        ({group.label} › {section.label})
                                                                                    </span>
                                                                                )}
                                                                            </span>
                                                                        </Link>
                                                                    </li>
                                                                );
                                                            })}
                                                        </ul>
                                                    </div>
                                                ))}
                                            </div>
                                        </AccordionContent>
                                    </AccordionItem>
                                );
                            })}
                        </Accordion>
                    </nav>
                )}
            </ScrollArea>
        </>
    );
}
