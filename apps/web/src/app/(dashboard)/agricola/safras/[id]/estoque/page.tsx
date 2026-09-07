"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { EstoqueTab } from "@/components/safras/EstoqueTab";
import { Skeleton } from "@/components/ui/skeleton";
import { getSafraLabel } from "@/lib/safra-label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";

interface Safra {
  id: string;
  cultura: string | null;
  ano_safra: string;
  status: string;
}

export default function EstoquePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  const { data: safra, isLoading: loadingSafra, isError: safraIsError } = useQuery<Safra>({
    queryKey: ["safra", id],
    queryFn: () => apiFetch(`/safras/${id}`),
    retry: false,
  });
  const safraLabel = getSafraLabel(safra);

  if (loadingSafra) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (safraIsError || !safra) {
    return (
      <div className="space-y-6 p-6">
        <PageHeader
          title="Estoque"
          description="Safra não encontrada ou indisponível"
        />
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Safra indisponível</AlertTitle>
          <AlertDescription>
            Não foi possível carregar a safra informada. Verifique se o registro existe e se você tem acesso a ele.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title={`Estoque — ${safraLabel}`}
        description={safraLabel}
      />

      <EstoqueTab safraId={id} />
    </div>
  );
}
