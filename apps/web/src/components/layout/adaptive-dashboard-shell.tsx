"use client";

import * as React from "react";
import { useSidebar } from "@/components/ui/sidebar";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { cn } from "@/lib/utils";
import { MobileBottomNav } from "./mobile-bottom-nav";

interface AdaptiveDashboardShellProps {
  children: React.ReactNode;
  hasExplicitSidebarCookie: boolean;
}

export function AdaptiveDashboardShell({
  children,
  hasExplicitSidebarCookie,
}: AdaptiveDashboardShellProps): React.ReactElement {
  const { deviceCategory, executionMode, isHydrated } = useDeviceContext();
  const { setOpen } = useSidebar();
  const appliedInitialDeviceRuleRef = React.useRef(false);

  React.useEffect(() => {
    if (!isHydrated || appliedInitialDeviceRuleRef.current) {
      return;
    }
    appliedInitialDeviceRuleRef.current = true;

    if (!hasExplicitSidebarCookie && deviceCategory === "tablet") {
      setOpen(false);
    }
  }, [deviceCategory, hasExplicitSidebarCookie, isHydrated, setOpen]);

  return (
    <div
      data-testid="web-adaptive-shell"
      data-device={deviceCategory}
      data-execution-mode={executionMode}
      className={cn(
        "flex min-h-0 flex-1 w-full flex-col",
        deviceCategory === "mobile" && "pb-16"
      )}
    >
      <div className="flex w-full min-w-0 flex-1 flex-col pb-16 md:pb-0">
        {children}
      </div>
      <MobileBottomNav />
    </div>
  );
}

