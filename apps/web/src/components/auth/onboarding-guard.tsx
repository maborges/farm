"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAppStore } from "@/lib/stores/app-store";
import { apiFetch } from "@/lib/api";

interface OnboardingStatusResponse {
  completo: boolean;
  etapa1_produtor: boolean;
  etapa2_propriedade: boolean;
  etapa3_equipe: boolean;
}

const ONBOARDING_ALLOWED_PATHS = [
  "/dashboard/implantacao/wizard",
  "/cadastros/propriedades",
  "/cadastros/propriedades/talhoes",
  "/cadastros/produtos",
  "/cadastros/equipamentos",
  "/cadastros/culturas",
  "/dashboard/pecuaria/piquetes",
  "/dashboard/financeiro/planos-conta",
  "/suprimentos/estoque",
  "/dashboard/settings/integracoes/erp",
  "/dashboard/settings/propriedades",
];

function isOnboardingAllowedPath(pathname: string): boolean {
  return ONBOARDING_ALLOWED_PATHS.some(
    (allowedPath) => pathname === allowedPath || pathname.startsWith(`${allowedPath}/`),
  );
}

/**
 * Usa o endpoint real de onboarding como fonte de verdade para impedir
 * acesso ao dashboard até a configuração inicial ser concluída.
 */
export function OnboardingGuard({ children }: { children: React.ReactNode }) {
  const { tenant, user, _hasHydrated } = useAppStore();
  const router = useRouter();
  const pathname = usePathname();
  const [isCheckingStatus, setIsCheckingStatus] = useState(true);
  const tenantId = tenant?.id ?? null;
  const isAllowedPath = isOnboardingAllowedPath(pathname);
  const needsStatusCheck = _hasHydrated && !!tenantId && !user?.is_superuser;

  useEffect(() => {
    if (!needsStatusCheck || isAllowedPath) {
      setIsCheckingStatus(false);
      return;
    }

    let cancelled = false;

    apiFetch<OnboardingStatusResponse>("/onboarding/status", {
      suppressErrorLog: true,
    })
      .then((status) => {
        if (cancelled) {
          return;
        }

        if (!status.completo) {
          if (!isAllowedPath) {
            router.replace("/dashboard/implantacao/wizard");
          } else {
            setIsCheckingStatus(false);
          }
          return;
        }

        setIsCheckingStatus(false);
      })
      .catch(() => {
        if (!cancelled) {
          setIsCheckingStatus(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [isAllowedPath, needsStatusCheck, pathname, router, tenantId]);

  if (!needsStatusCheck || isAllowedPath) {
    return <>{children}</>;
  }

  if (isCheckingStatus) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-neutral-900">
        <div className="size-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
      </div>
    );
  }

  return <>{children}</>;
}
