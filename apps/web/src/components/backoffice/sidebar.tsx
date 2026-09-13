"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
    LayoutDashboard,
    CreditCard,
    Settings,
    Users,
    LayoutGrid,
    ChevronLeft,
    ChevronRight,
    LogOut,
    PanelLeftClose,
    PanelLeft,
    Workflow,
    ShoppingCart,
    Tags,
    Boxes,
    ListTree,
    Database,
    Ruler,
    ArrowLeftRight,
} from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"

export function AdminSidebar() {
    const pathname = usePathname()
    const [collapsed, setCollapsed] = useState(false)

    const menuItems = [
        { label: "Dashboard", icon: LayoutDashboard, href: "/backoffice" },
        { label: "CRM - Pipeline", icon: Workflow, href: "/backoffice/pipeline" },
        { label: "CRM - Ofertas", icon: ShoppingCart, href: "/backoffice/ofertas" },
        { label: "Planos", icon: CreditCard, href: "/backoffice/plans" },
        { label: "Usuários", icon: Users, href: "/backoffice/users" },
        { label: "Inscrições", icon: LayoutGrid, href: "/backoffice/subscriptions" },
        { label: "Tabelas Padrão", icon: Database, href: "/backoffice/tabelas" },
        { label: "Configurações", icon: Settings, href: "/backoffice/settings" },
    ]

    const cadastrosAuxiliares = [
        { label: "Marcas", icon: Tags, href: "/backoffice/cadastros-auxiliares/marcas" },
        { label: "Modelos", icon: Boxes, href: "/backoffice/cadastros-auxiliares/modelos" },
        { label: "Categorias", icon: ListTree, href: "/backoffice/cadastros-auxiliares/categorias" },
        { label: "Unidades de Medida", icon: Ruler, href: "/backoffice/cadastros-auxiliares/unidades-medida" },
        { label: "Conversões UoM", icon: ArrowLeftRight, href: "/backoffice/cadastros-auxiliares/unidades-conversoes" },
    ]

    return (
        <aside className={cn(
            "glass-chrome flex flex-col transition-all duration-300 h-dvh",
            collapsed ? "w-16" : "w-64"
        )}>
            <div className="p-4 border-b border-sidebar-border/50 flex justify-between items-center bg-white/5">
                {!collapsed && (
                    <span className="font-bold text-xl text-primary tracking-tighter">
                        ANDRU
                    </span>
                )}
                <Button
                    variant="ghost"
                    size="icon"
                    className="size-8 text-muted-foreground hover:text-primary"
                    aria-label={collapsed ? "Expandir menu" : "Recolher menu"}
                    onClick={() => setCollapsed(!collapsed)}
                >
                    {collapsed ? <PanelLeft className="size-4" /> : <PanelLeftClose className="size-4" />}
                </Button>
            </div>
            
            <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
                <div className="space-y-1">
                    {menuItems.map((item) => {
                        const active = pathname === item.href
                        return (
                            <Link 
                                key={item.href} 
                                href={item.href}
                                className={cn(
                                    "flex items-center p-2 rounded-sm font-medium text-sm transition-all relative overflow-hidden group",
                                    active
                                        ? "relative bg-primary/5 text-primary font-bold before:absolute before:left-0 before:top-1 before:bottom-1 before:w-[2px] before:rounded-full before:bg-primary"
                                        : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                                    collapsed && "justify-center"
                                )}
                            >
                                <item.icon className={cn("size-4 shrink-0 shadow-sm", !collapsed && "mr-3")} />
                                {!collapsed && <span className="truncate">{item.label}</span>}
                                {collapsed && (
                                    <div className="absolute left-14 bg-popover text-popover-foreground px-2 py-1 rounded text-xs invisible group-hover:visible shadow-md border whitespace-nowrap z-50">
                                        {item.label}
                                    </div>
                                )}
                            </Link>
                        )
                    })}
                </div>

                <div className="pt-4 pb-2">
                    {!collapsed ? (
                        <p className="px-2 text-[10px] font-bold tracking-wider text-sidebar-foreground/60 mb-2">
                            Cadastros Auxiliares
                        </p>
                    ) : (
                        <div className="border-t border-sidebar-border my-2" />
                    )}
                    <div className="space-y-1">
                        {cadastrosAuxiliares.map((item) => {
                            const active = pathname === item.href
                            return (
                                <Link 
                                    key={item.href} 
                                    href={item.href}
                                    className={cn(
                                        "flex items-center p-2 rounded-sm font-medium text-sm transition-all relative overflow-hidden group",
                                        active
                                            ? "relative bg-primary/5 text-primary font-bold before:absolute before:left-0 before:top-1 before:bottom-1 before:w-[2px] before:rounded-full before:bg-primary"
                                            : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                                        collapsed && "justify-center"
                                    )}
                                >
                                    <item.icon className={cn("size-4 shrink-0 shadow-sm", !collapsed && "mr-3")} />
                                    {!collapsed && <span className="truncate">{item.label}</span>}
                                    {collapsed && (
                                        <div className="absolute left-14 bg-popover text-popover-foreground px-2 py-1 rounded text-xs invisible group-hover:visible shadow-md border whitespace-nowrap z-50">
                                            {item.label}
                                        </div>
                                    )}
                                </Link>
                            )
                        })}
                    </div>
                </div>
            </nav>

            <div className="p-3 border-t border-sidebar-border">
                <Button 
                    variant="outline" 
                    size="sm"
                    className={cn(
                        "w-full h-9 flex items-center justify-start text-destructive hover:bg-destructive shadow-sm hover:text-white border-destructive/20", 
                        collapsed && "justify-center px-0"
                    )}
                    onClick={() => console.log("Logout")}
                >
                    <LogOut className={cn("size-4", !collapsed && "mr-2")} />
                    {!collapsed && <span className="text-xs font-semibold">Desconectar</span>}
                </Button>
            </div>
        </aside>
    )
}
