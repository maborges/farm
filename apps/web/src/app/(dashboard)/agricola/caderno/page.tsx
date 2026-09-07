"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CadernoTimeline, type TimelineItem } from "@/components/agricola/caderno/CadernoTimeline";
import { EntradaDrawer } from "@/components/agricola/caderno/EntradaDrawer";
import { BookOpen, Download, FileText, CalendarDays, Lock } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import Link from "next/link";
import { useHasTier } from "@/hooks/use-has-tier";
import { trackMonetizationEvent, useMonetizationPromptTracking } from "@/lib/monetization";

interface Safra {
  id: string;
  ano_safra: string;
  cultura: string;
  status: string;
}

interface Talhao {
  id: string;
  nome: string;
}

interface ExportacaoResponse {
  id: string;
  safra_id: string;
  url_pdf: string;
  data_geracao: string;
  assinado_por?: string;
  crea_rt?: string;
  modelo_certificacao: string;
}

const MODELO_LABEL: Record<string, string> = {
  padrao: "Padrão",
  globalgap: "GlobalG.A.P.",
  organico: "Orgânico (USDA/IBD)",
  mapa: "MAPA",
  INTERNO: "Padrão",
  GLOBALGAP: "GlobalG.A.P.",
  ORGANICO: "Orgânico",
};

export default function CadernoGlobalPage() {
  const [safraId, setSafraId] = useState<string>("all");
  const [talhaoId, setTalhaoId] = useState<string>("all");
  const [selectedItem, setSelectedItem] = useState<TimelineItem | null>(null);
  const hasEnterpriseTier = useHasTier("ENTERPRISE");
  useMonetizationPromptTracking(!hasEnterpriseTier, {
    feature: "agricola.caderno.exportacao",
    surface: "agricola.caderno.page",
    requiredTier: "ENTERPRISE",
    ctaLabel: "Ver planos",
  });

  // Fetch safras
  const { data: safras = [], isLoading: isLoadingSafras } = useQuery<Safra[]>({
    queryKey: ["safras"],
    queryFn: () => apiFetch("/safras"),
  });

  const activeSafras = safras.filter((s) => !["ENCERRADA", "CANCELADA"].includes(s.status));

  // Fetch talhões da safra selecionada
  const { data: talhoes = [], isLoading: isLoadingTalhoes } = useQuery<Talhao[]>({
    queryKey: ["talhoes", safraId],
    queryFn: () => apiFetch(`/safras/${safraId}/talhoes`),
    enabled: safraId !== "all",
  });

  // Fetch timeline global
  const safraParam = safraId !== "all" ? safraId : undefined;
  const talhaoParam = talhaoId !== "all" ? talhaoId : undefined;

  const timelineQuery = new URLSearchParams();
  if (safraParam) timelineQuery.set("safra_id", safraParam);
  if (talhaoParam) timelineQuery.set("talhao_id", talhaoParam);

  const { data: timelineItems = [], isLoading: isLoadingTimeline } = useQuery<TimelineItem[]>({
    queryKey: ["caderno-timeline-global", safraParam, talhaoParam],
    queryFn: () => apiFetch(`/caderno/timeline?${timelineQuery.toString()}`),
  });

  // Fetch exportacoes globais
  const { data: exportacoes = [], isLoading: isLoadingExportacoes } = useQuery<ExportacaoResponse[]>({
    queryKey: ["caderno-exportacoes-global"],
    queryFn: () => apiFetch("/caderno/exportacoes"),
    enabled: hasEnterpriseTier,
  });

  const modeloLabel = (modelo: string) => MODELO_LABEL[modelo] || modelo;

  if (isLoadingSafras) {
    return (
      <div className="space-y-6 p-8">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Caderno de Campo"
        description="Registro e acompanhamento de todas as operações de campo, certificações e exportações."
        icon={<BookOpen className="text-primary" size={22} />}
        breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Caderno de Campo" }]}
      />

      {!hasEnterpriseTier && (
        <Alert className="rounded-sm">
          <Lock className="size-4" />
          <AlertTitle>Exportações e assinaturas disponíveis no ENTERPRISE</AlertTitle>
          <AlertDescription className="space-y-3">
            <p>O caderno operacional continua acessível. Exportar PDF, listar exportações e assinar documentos exigem tier ENTERPRISE.</p>
            <Button
              asChild
              size="sm"
              className="rounded-sm"
              onClick={() => trackMonetizationEvent("monetization_cta_clicked", {
                feature: "agricola.caderno.exportacao",
                surface: "agricola.caderno.page",
                requiredTier: "ENTERPRISE",
                ctaLabel: "Ver planos",
              })}
            >
              <Link href="/dashboard/settings/billing">Ver planos</Link>
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Filtros */}
      <Card className="shadow-sm flex items-center px-6 border-dashed rounded-sm">
        <div className="flex gap-4 w-full py-4 border-l-4 border-emerald-500 pl-4 flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <Badge variant="outline" className="mb-2 bg-emerald-50 text-emerald-700 rounded-sm">
              <BookOpen className="size-3 mr-1" /> Filtro Ativo
            </Badge>
            <Select value={safraId} onValueChange={(v: string) => { setSafraId(v); setTalhaoId("all"); }}>
              <SelectTrigger className="w-full font-medium h-8 text-xs rounded-sm">
                <SelectValue placeholder="Todas as Safras" />
              </SelectTrigger>
              <SelectContent className="rounded-sm">
                <SelectItem value="all">Todas as Safras (Ativas e Histórico)</SelectItem>
                {activeSafras.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.cultura} — {s.ano_safra}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {safraId !== "all" && !isLoadingTalhoes && talhoes.length > 0 && (
            <div className="flex-1 min-w-[200px]">
              <Select value={talhaoId} onValueChange={setTalhaoId}>
                <SelectTrigger className="w-full font-medium h-8 text-xs rounded-sm mt-6">
                  <SelectValue placeholder="Todos os Talhões" />
                </SelectTrigger>
                <SelectContent className="rounded-sm">
                  <SelectItem value="all">Todos os Talhões</SelectItem>
                  {talhoes.map((t) => (
                    <SelectItem key={t.id} value={t.id}>
                      {t.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>
      </Card>

      {/* Timeline */}
      <Card className="shadow-sm rounded-sm">
        <CardHeader className="pb-3 px-6 pt-6">
          <CardTitle className="flex items-center gap-2 text-lg">
            <CalendarDays className="size-5 text-emerald-600" />
            Timeline de Registros
          </CardTitle>
        </CardHeader>
        <CardContent className="px-6 pb-6 pt-0">
          <CadernoTimeline
            items={timelineItems}
            isLoading={isLoadingTimeline}
            onSelect={setSelectedItem}
          />
        </CardContent>
      </Card>

      {/* Histórico de Exportações */}
      <Card className="shadow-sm rounded-sm">
        <CardHeader className="pb-3 px-6 pt-6">
          <CardTitle className="flex items-center gap-2 text-lg">
            <FileText className="size-5 text-emerald-600" />
            Histórico de Exportações
          </CardTitle>
        </CardHeader>
        <CardContent className="px-6 pb-6 pt-0">
          {isLoadingExportacoes ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : exportacoes.length === 0 ? (
            <div className="py-8 flex flex-col items-center justify-center text-center text-muted-foreground">
              <FileText className="size-8 opacity-20 mb-2" />
              <p className="text-sm">Nenhuma exportação gerada ainda.</p>
              <p className="text-xs mt-1">Use o botão Exportar na página de safra para gerar o caderno em PDF.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data</TableHead>
                  <TableHead>Modelo</TableHead>
                  <TableHead>Safra</TableHead>
                  <TableHead>Responsável</TableHead>
                  <TableHead>CREA</TableHead>
                  <TableHead className="text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {exportacoes.map((exp) => (
                  <TableRow key={exp.id}>
                    <TableCell className="text-sm">
                      {format(new Date(exp.data_geracao), "dd/MM/yyyy HH:mm", { locale: ptBR })}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="rounded-sm font-bold text-[10px]">{modeloLabel(exp.modelo_certificacao)}</Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {exp.safra_id.substring(0, 8)}
                    </TableCell>
                    <TableCell className="text-sm">{exp.assinado_por || "—"}</TableCell>
                    <TableCell className="text-sm">{exp.crea_rt || "—"}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        className="rounded-sm h-7 text-xs"
                        asChild
                      >
                        <a href={exp.url_pdf} target="_blank" rel="noopener noreferrer">
                          <Download className="size-3.5 mr-1.5" />
                          Baixar
                        </a>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Drawer de detalhes */}
      <EntradaDrawer item={selectedItem} onClose={() => setSelectedItem(null)} />
    </div>
  );
}
