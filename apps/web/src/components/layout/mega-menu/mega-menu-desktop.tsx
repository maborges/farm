import React, { useState } from "react";
import Link from "next/link";
import { Search, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { isItemActive } from "@/lib/sidebar-navigation";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
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

interface MegaMenuDesktopProps {
    moduleGroups: SidebarModuleGroup[];
    accessItems?: SidebarMenuItem[];
    settingsItems?: SidebarMenuItem[];
    pathname: string;
    searchParams: URLSearchParams;
    onClose: () => void;
}

export function MegaMenuDesktop({ moduleGroups, accessItems = [], settingsItems = [], pathname, searchParams, onClose }: MegaMenuDesktopProps) {
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

    // Filtro simplificado no protótipo: retorna grupos com itens que deram match
    const filteredGroups = allGroups.map(group => {
        const matchedSections = group.sections.map(sec => {
            const matchedItems = sec.items.filter(item =>
                item.label.toLowerCase().includes(term) || sec.label.toLowerCase().includes(term) || group.label.toLowerCase().includes(term)
            );
            return { ...sec, items: matchedItems };
        }).filter(sec => sec.items.length > 0);
        return { ...group, sections: matchedSections };
    }).filter(group => group.sections.length > 0);

    return (
        <div className="flex flex-col max-h-[85vh] bg-card rounded-md overflow-hidden" role="dialog" aria-modal="true" aria-label="Mega Menu">
            <div className="p-4 border-b flex gap-4 items-center bg-muted/30">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input 
                        placeholder="Buscar em módulos, seções e destinos..." 
                        className="pl-9 bg-background" 
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        autoFocus
                    />
                </div>
            </div>
            
            <ScrollArea className="flex-1 overflow-auto max-h-[70vh]">
                {filteredGroups.length === 0 ? (
                    <div className="p-8 text-center text-muted-foreground">Nenhum resultado encontrado.</div>
                ) : (
                    <nav
                        aria-label="Navegação Principal"
                        className="columns-1 sm:columns-2 md:columns-3 lg:columns-4 xl:columns-5 gap-5 p-6 [column-fill:_balance]"
                    >
                        {filteredGroups.map(group => {
                            const Icon = group.icon;
                            const isDense = group.sections.length > 4;
                            return (
                                <div
                                    key={group.key}
                                    className="flex flex-col gap-3 mb-5 break-inside-avoid rounded-xl border border-transparent hover:border-border/60 hover:bg-card hover-lift p-3 -m-3 transition-all"
                                >
                                    <div className="flex items-center gap-1.5 text-primary font-semibold border-b pb-1.5 text-sm">
                                        <Icon className="h-4 w-4" aria-hidden="true" />
                                        <span>{group.label}</span>
                                    </div>
                                    <div className={cn("flex flex-col gap-3", isDense && "gap-2")}>
                                        {group.sections.map(section => (
                                            <div key={section.key} className="flex flex-col gap-0.5">
                                                <h4 className="font-medium text-muted-foreground uppercase tracking-wider text-[10px]" id={`section-${section.key}`}>
                                                    {section.label}
                                                </h4>
                                                <ul className="flex flex-col" aria-labelledby={`section-${section.key}`}>
                                                    {section.items.map(item => {
                                                        const isActive = isItemActive(item.href, pathname, searchParams);
                                                        const ItemIcon = item.icon;
                                                        return (
                                                            <li key={item.href}>
                                                                    <Link
                                                                        href={item.href}
                                                                        onClick={onClose}
                                                                        className={cn(
                                                                            "flex items-center gap-2 px-2 py-1.5 -mx-2 rounded-md text-[13px] transition-colors",
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
                                </div>
                            );
                        })}
                    </nav>
                )}
            </ScrollArea>
            <div className="p-4 border-t bg-muted/20 text-xs text-muted-foreground flex justify-between items-center">
                <span>Navegue usando o teclado</span>
                <span className="flex gap-1 items-center">
                    <kbd className="px-1.5 py-0.5 rounded border bg-background text-[10px] shadow-sm">Tab</kbd>
                    <kbd className="px-1.5 py-0.5 rounded border bg-background text-[10px] shadow-sm">Enter</kbd>
                    <kbd className="px-1.5 py-0.5 rounded border bg-background text-[10px] shadow-sm">Esc</kbd>
                </span>
            </div>
        </div>
    );
}
