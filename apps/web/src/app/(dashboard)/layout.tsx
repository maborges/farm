import { Topbar } from "@/components/layout/topbar";
import { NavigationShell } from "@/components/layout/navigation-shell";
import { AdaptiveDashboardShell } from "@/components/layout/adaptive-dashboard-shell";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SessionGuard } from "@/components/auth/session-guard";
import { DemoExpiredGuard } from "@/components/auth/demo-expired-guard";
import { OnboardingGuard } from "@/components/auth/onboarding-guard";
import { FazendasSync } from "@/components/auth/fazendas-sync";
import { AuthBootstrap } from "@/components/auth/auth-bootstrap";
import { TenantTabSyncWarning } from "@/components/auth/tenant-tab-sync-warning";
import { FazendaPermissionSync } from "@/components/auth/fazenda-permission-sync";
import { RecentNavigationTracker } from "@/components/layout/recent-navigation-tracker";
import { NavigationShortcuts } from "@/components/layout/navigation-shortcuts";
import { ServiceWorkerRegistration } from "@/components/pwa/service-worker-registration";
import { SessionIdleGuard } from "@/components/auth/session-idle-guard";
import { OfflineStatus } from "@/components/pwa/offline-status";
import { cookies } from "next/headers";

export default async function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const cookieStore = await cookies();
    const tokenFromCookie = cookieStore.get("token")?.value ?? null;
    const tenantIdFromCookie = cookieStore.get("tenant_id")?.value ?? null;
    const fazendaIdFromCookie = cookieStore.get("unidade_produtiva_id")?.value ?? null;
    const sidebarState = cookieStore.get("sidebar_state")?.value;
    const hasExplicitSidebarCookie = sidebarState === "true" || sidebarState === "false";
    const sidebarOpen = sidebarState !== "false";

    return (
        <SessionGuard>
            <OnboardingGuard>
                <SidebarProvider defaultOpen={sidebarOpen}>
                    <TooltipProvider delay={200} className="flex min-h-svh w-full">
                        <AuthBootstrap
                            tokenFromCookie={tokenFromCookie}
                            tenantIdFromCookie={tenantIdFromCookie}
                            fazendaIdFromCookie={fazendaIdFromCookie}
                        />
                        <SessionIdleGuard />
                        <FazendasSync />
                        <TenantTabSyncWarning />
                        <FazendaPermissionSync />
                        <RecentNavigationTracker />
                        <NavigationShortcuts />
                        <ServiceWorkerRegistration />
                        <OfflineStatus />
                        <NavigationShell />
                        <SidebarInset className="h-svh min-w-0 overflow-hidden bg-background text-foreground">
                            <Topbar />
                            <main className="flex min-h-0 flex-1 w-full overflow-y-auto overflow-x-hidden">
                                <AdaptiveDashboardShell hasExplicitSidebarCookie={hasExplicitSidebarCookie}>
                                    <DemoExpiredGuard>{children}</DemoExpiredGuard>
                                </AdaptiveDashboardShell>
                            </main>
                        </SidebarInset>
                    </TooltipProvider>
                </SidebarProvider>
            </OnboardingGuard>
        </SessionGuard>
    );
}
