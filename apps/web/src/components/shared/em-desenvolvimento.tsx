"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Construction,
  Rocket,
  Bell,
  CheckCircle2,
  ArrowLeft
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

interface EmDesenvolvimentoProps {
  titulo?: string;
  descricao?: string;
  funcionalidades?: string[];
  previsao?: string;
  voltarPara?: string;
  interesseHref?: string;
}

export function EmDesenvolvimento({
  titulo,
  descricao,
  funcionalidades,
  previsao,
  voltarPara,
  interesseHref = "/dashboard/settings/support",
}: EmDesenvolvimentoProps) {
  const router = useRouter();

  // Busca configurações padrão do SaaS
  interface EmDesenvolvimentoConfig {
    valor?: {
      titulo?: string;
      descricao?: string;
      funcionalidades?: string[];
      previsao?: string;
      voltarPara?: string;
    };
  }

  const { data: configsData } = useQuery<EmDesenvolvimentoConfig>({
    queryKey: ["saas-config-em-desenvolvimento"],
    queryFn: () => apiFetch("/config/saas/em_desenvolvimento"),
    retry: 1,
    staleTime: 1000 * 60 * 5, // 5 min
  });

  // Use provided props, fallback to SaaS config, then hardcoded defaults
  const tituloFinal = titulo || configsData?.valor?.titulo || "Em Desenvolvimento";
  const descricaoFinal = descricao || configsData?.valor?.descricao || "Esta funcionalidade está sendo construída com muito carinho e estará disponível em breve.";
  const funcionalidadesFinal = funcionalidades || configsData?.valor?.funcionalidades || [];
  const previsaoFinal = previsao || configsData?.valor?.previsao || undefined;
  const voltarParaFinal = voltarPara || configsData?.valor?.voltarPara || "/dashboard";

  return (
    <div className="flex items-center justify-center min-h-[80vh] p-8">
      <Card className="w-full max-w-2xl rounded-sm">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
              <Construction className="h-10 w-10 text-primary" />
            </div>
          </div>

          <CardTitle className="text-3xl">{tituloFinal}</CardTitle>
          <CardDescription className="text-lg mt-2">
            {descricaoFinal}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Funcionalidades que estão sendo construídas */}
          {funcionalidadesFinal.length > 0 && (
            <div className="space-y-3">
              <h3 className="font-semibold text-lg flex items-center gap-2">
                <Rocket className="h-5 w-5" />
                O que está sendo construído:
              </h3>
              <ul className="grid gap-2">
                {funcionalidadesFinal.map((func, index) => (
                  <li
                    key={index}
                    className="flex items-center gap-2 text-sm bg-muted/50 px-3 py-2 rounded-md"
                  >
                    <Rocket className="h-4 w-4 text-primary" />
                    {func}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Previsão de lançamento */}
          {previsaoFinal && (
            <div className="flex gap-3 p-4 bg-blue-50 border border-blue-200 rounded-md">
              <Bell className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
              <div className="text-blue-800 text-sm">
                <strong>Previsão de lançamento:</strong> {previsaoFinal}
              </div>
            </div>
          )}

          {/* Progresso */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Progresso</span>
              <span className="font-medium">Em construção</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div className="h-full w-1/3 bg-primary animate-pulse" />
            </div>
          </div>

          {/* Ações */}
          <div className="flex gap-3 pt-4">
            <Button
              variant="outline"
              onClick={() => router.back()}
              className="flex-1"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Voltar
            </Button>

            <Button
              variant="default"
              asChild
              className="flex-1"
            >
              <Link href={voltarParaFinal}>
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Ir para Dashboard
              </Link>
            </Button>
          </div>

          {/* Notificação de lançamento */}
          <div className="flex flex-col items-center gap-3 border-t pt-4 text-center sm:flex-row sm:justify-between sm:text-left">
            <p className="text-xs text-muted-foreground">
              Quer ser notificado quando esta funcionalidade for lançada?
            </p>
            <Button asChild variant="outline" size="sm" className="shrink-0">
              <Link href={interesseHref}>
                <Bell className="mr-2 size-4" />
                Demonstrar interesse
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
