"use client";

import * as React from "react";
import {
  DeviceContextProvider,
  useDeviceContext,
} from "@/lib/device/use-device-context";
import { AdaptiveSidebar } from "./adaptive-sidebar";
import { BottomNav } from "./bottom-nav";
import { Header } from "./header";

function AdaptiveShellInner({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  const { deviceCategory, executionMode, platformOS, layoutProfile } =
    useDeviceContext();

  return (
    <div
      id="agro-adaptive-shell"
      data-device-category={deviceCategory}
      data-execution-mode={executionMode}
      data-navigation-pattern={layoutProfile.navigationPattern}
      data-platform-os={platformOS}
      className="min-h-dvh flex flex-col bg-background text-foreground safe-area-px"
    >
      <Header />
      <div className="flex-1 flex w-full max-w-7xl mx-auto">
        <AdaptiveSidebar />
        <main className="@container/main flex-1 min-w-0 w-full max-w-5xl mx-auto px-3 sm:px-5 md:px-6 py-3 sm:py-5 pb-[calc(5.5rem+env(safe-area-inset-bottom,0px))] md:pb-8">
          {children}
        </main>
      </div>
      <BottomNav />
    </div>
  );
}

export function AdaptiveShell({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <DeviceContextProvider>
      <AdaptiveShellInner>{children}</AdaptiveShellInner>
    </DeviceContextProvider>
  );
}

