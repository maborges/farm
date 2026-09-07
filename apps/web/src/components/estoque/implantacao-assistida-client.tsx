"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Ban,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  Download,
  Eye,
  FileSpreadsheet,
  FileUp,
  Filter,
  Loader2,
  PackageCheck,
  RefreshCw,
  Search,
  ShieldCheck,
  TriangleAlert,
  Upload,
  Warehouse,
} from "lucide-react";

import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { cn } from "@/lib/utils";
import { usePermission } from "@/hooks/use-permission";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

type SessaoStatus =
  | "RASCUNHO"
  | "PREVIEW_GERADO"
  | "VALIDADO_COM_ERROS"
  | "PRONTO_PARA_CORRECAO"
  | "PRONTO_PARA_CONFIRMAR"
  | "CANCELADO"
  | "CONFIRMADO";

type ItemStatus = "VALIDA" | "AVISO" | "ERRO" | "CORRIGIDO" | "IGNORADO";

interface PreviewMessage {
  linha?: number | null;
  campo?: string | null;
  codigo: string;
  mensagem: string;
}

interface PreviewItem {
  numero_linha: number;
  status: "VALIDA" | "AVISO" | "ERRO";
  payload_original: Record<string, string>;
  dados_normalizados: Record<string, unknown>;
  erros: PreviewMessage[];
  avisos: PreviewMessage[];
  sugestoes: Record<string, string[]>;
}

interface PreviewResponse {
  arquivo_nome: string;
  extensao: string;
  encoding?: string | null;
  delimitador?: string | null;
  estrutura_minima_valida: boolean;
  colunas_detectadas: string[];
  mapeamento_utilizado: Record<string, string>;
  total_linhas: number;
  linhas_validas: number;
  linhas_com_erro: number;
  linhas_com_aviso: number;
  produtos_nao_encontrados: string[];
  depositos_nao_encontrados: string[];
  valor_total_estimado: number;
  itens: PreviewItem[];
  erros_arquivo: PreviewMessage[];
}

interface ImplantacaoItem {
  id: string;
  numero_linha: number;
  status: ItemStatus;
  ignorado: boolean;
  payload_original: Record<string, string>;
  dados_normalizados: Record<string, unknown>;
  produto_id_resolvido?: string | null;
  deposito_id_resolvido?: string | null;
  erros: PreviewMessage[];
  avisos: PreviewMessage[];
  sugestoes: Record<string, string[]>;
  criado_em: string;
  atualizado_em: string;
}

interface ImplantacaoSessao {
  id: string;
  tenant_id: string;
  unidade_produtiva_id?: string | null;
  arquivo_nome: string;
  arquivo_hash: string;
  status: SessaoStatus;
  mapeamento_colunas: Record<string, string>;
  colunas_detectadas: string[];
  total_linhas: number;
  linhas_validas: number;
  linhas_com_erro: number;
  linhas_com_aviso: number;
  valor_total_estimado: number;
  criado_por?: string | null;
  criado_em: string;
  atualizado_em: string;
  cancelado_em?: string | null;
  confirmado_em?: string | null;
  confirmado_por?: string | null;
  total_itens: number;
  limit: number;
  offset: number;
  itens: ImplantacaoItem[];
}

interface SessaoListResponse {
  itens: ImplantacaoSessao[];
  total: number;
  limit: number;
  offset: number;
}

interface ItemListResponse {
  itens: ImplantacaoItem[];
  total: number;
  limit: number;
  offset: number;
}

interface AptidaoConfirmacao {
  apta: boolean;
  erros_bloqueantes: string[];
  avisos: string[];
  total_itens_confirmaveis: number;
  valor_total_confirmavel: number;
}

interface AuditLogItem {
  id: string;
  action: string;
  resource: string;
  resource_id?: string | null;
  user_id?: string | null;
  created_at: string;
}

interface AuditLogListResponse {
  items: AuditLogItem[];
  total: number;
  page: number;
  page_size: number;
}

interface Produto {
  id: string;
  nome: string;
  codigo_interno?: string | null;
  sku?: string | null;
}

interface Deposito {
  id: string;
  nome: string;
  unidade_produtiva_id?: string | null;
}

const SESSION_STATUS_LABELS: Record<SessaoStatus, string> = {
  RASCUNHO: "Rascunho",
  PREVIEW_GERADO: "Preview gerado",
  VALIDADO_COM_ERROS: "Validado com erros",
  PRONTO_PARA_CORRECAO: "Pronto para correção",
  PRONTO_PARA_CONFIRMAR: "Pronto para confirmar",
  CANCELADO: "Cancelado",
  CONFIRMADO: "Confirmado",
};

const ITEM_STATUS_LABELS: Record<ItemStatus, string> = {
  VALIDA: "Válida",
  AVISO: "Aviso",
  ERRO: "Erro",
  CORRIGIDO: "Corrigido",
  IGNORADO: "Ignorado",
};

const STATUS_CLASSES: Record<SessaoStatus | ItemStatus, string> = {
  RASCUNHO: "border-slate-200 bg-slate-100 text-slate-700",
  PREVIEW_GERADO: "border-blue-200 bg-blue-100 text-blue-700",
  VALIDADO_COM_ERROS: "border-red-200 bg-red-100 text-red-700",
  PRONTO_PARA_CORRECAO: "border-amber-200 bg-amber-100 text-amber-800",
  PRONTO_PARA_CONFIRMAR: "border-emerald-200 bg-emerald-100 text-emerald-700",
  CANCELADO: "border-slate-300 bg-slate-200 text-slate-700",
  CONFIRMADO: "border-sky-200 bg-sky-100 text-sky-700",
  VALIDA: "border-emerald-200 bg-emerald-100 text-emerald-700",
  AVISO: "border-amber-200 bg-amber-100 text-amber-800",
  ERRO: "border-red-200 bg-red-100 text-red-700",
  CORRIGIDO: "border-emerald-200 bg-emerald-100 text-emerald-700",
  IGNORADO: "border-slate-200 bg-slate-100 text-slate-700",
};

const ITEM_STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "TODOS", label: "Todos" },
  { value: "ERRO", label: "Erro" },
  { value: "AVISO", label: "Aviso" },
  { value: "VALIDA", label: "Válida" },
  { value: "CORRIGIDO", label: "Corrigido" },
  { value: "IGNORADO", label: "Ignorado" },
];

const SESSION_STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "TODOS", label: "Todos os status" },
  { value: "VALIDADO_COM_ERROS", label: "Com erros" },
  { value: "PRONTO_PARA_CORRECAO", label: "Pronto para correção" },
  { value: "PRONTO_PARA_CONFIRMAR", label: "Pronto para confirmar" },
  { value: "CONFIRMADO", label: "Confirmado" },
  { value: "CANCELADO", label: "Cancelado" },
];

function StatusBadge({ status }: { status: SessaoStatus | ItemStatus }) {
  const label = SESSION_STATUS_LABELS[status as SessaoStatus] ?? ITEM_STATUS_LABELS[status as ItemStatus] ?? status;
  return <Badge className={cn("border text-[10px] font-semibold uppercase tracking-wide", STATUS_CLASSES[status])}>{label}</Badge>;
}

function StatCard({
  title,
  value,
  hint,
  tone = "slate",
}: {
  title: string;
  value: string;
  hint: string;
  tone?: "slate" | "emerald" | "amber" | "red" | "sky";
}) {
  const toneMap = {
    slate: "border-l-slate-400 bg-slate-50/70",
    emerald: "border-l-emerald-500 bg-emerald-50/70",
    amber: "border-l-amber-500 bg-amber-50/70",
    red: "border-l-red-500 bg-red-50/70",
    sky: "border-l-sky-500 bg-sky-50/70",
  };
  return (
    <Card className={cn("border-l-4 shadow-sm", toneMap[tone])}>
      <CardContent className="p-4">
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{title}</p>
        <p className="mt-2 text-2xl font-black tracking-tight">{value}</p>
        <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
      </CardContent>
    </Card>
  );
}

function SectionEmpty({ title, description }: { title: string; description: string }) {
  return (
    <Card className="border-dashed shadow-none">
      <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
        <PackageCheck className="size-8 text-muted-foreground/50" />
        <p className="text-sm font-semibold">{title}</p>
        <p className="max-w-xl text-sm text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}

function formatCurrency(value?: number | null) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value ?? 0);
}

function formatDateTime(value?: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString("pt-BR");
}

function serializeMapping(raw: string) {
  if (!raw.trim()) return null;
  const parsed = JSON.parse(raw);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("O mapeamento precisa ser um objeto JSON.");
  }
  return JSON.stringify(parsed);
}

async function downloadTemplateCsv() {
  const text = await apiFetch<string>("/estoque/implantacao-assistida/template", {
    responseType: "text",
  });
  const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "estoque_implantacao_template.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ImplantacaoAssistidaListPage() {
  const canView = usePermission("estoque:implantacao_assistida:view");
  const canList = usePermission("estoque:implantacao_assistida:list");
  const canCreate = usePermission("estoque:implantacao_assistida:create");
  const [status, setStatus] = useState("TODOS");
  const [arquivoNome, setArquivoNome] = useState("");
  const deferredArquivoNome = useDeferredValue(arquivoNome);

  const { data, isLoading } = useQuery<SessaoListResponse>({
    queryKey: ["estoque-implantacao-sessoes", status, deferredArquivoNome],
    enabled: canView && canList,
    queryFn: () =>
      apiFetch("/estoque/implantacao-assistida/sessoes", {
        params: {
          status: status === "TODOS" ? undefined : status,
          arquivo_nome: deferredArquivoNome || undefined,
          limit: 100,
          offset: 0,
        },
      }),
  });

  const sessoes = useMemo(() => data?.itens ?? [], [data]);
  const resumo = useMemo(() => {
    return {
      total: sessoes.length,
      confirmadas: sessoes.filter((sessao) => sessao.status === "CONFIRMADO").length,
      pendentes: sessoes.filter((sessao) => sessao.status === "PRONTO_PARA_CONFIRMAR").length,
      comErro: sessoes.filter((sessao) => sessao.linhas_com_erro > 0).length,
    };
  }, [sessoes]);

  return (
    <div className="p-6 space-y-6 w-full">
      <PageHeader
        title="Implantação Assistida de Estoque"
        description="Sessões de carga inicial que gravam SALDO_INICIAL, sem misturar a implantação com entradas operacionais comuns."
        icon={<Warehouse className="size-4 text-primary" />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Suprimentos", href: "/suprimentos" },
          { label: "Estoque", href: "/suprimentos/estoque" },
          { label: "Implantação Assistida" },
        ]}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => void downloadTemplateCsv()} disabled={!canCreate}>
              <Download size={14} /> Template CSV
            </Button>
            {canCreate ? (
              <Button asChild>
                <Link href="/suprimentos/estoque/implantacao-assistida/nova">
                  <Upload size={14} /> Nova implantação
                </Link>
              </Button>
            ) : (
              <Button disabled>
                <Upload size={14} /> Nova implantação
              </Button>
            )}
          </div>
        }
      />

      {!canView || !canList ? (
        <SectionEmpty
          title="Acesso restrito"
          description="Seu perfil não possui permissão para listar sessões de Implantação Assistida de Estoque."
        />
      ) : null}

      {canView && canList ? <div className="grid gap-4 md:grid-cols-4">
        <StatCard title="Sessões" value={String(resumo.total)} hint="processos listados no tenant atual" />
        <StatCard title="Confirmadas" value={String(resumo.confirmadas)} hint="já gravadas como saldo inicial" tone="sky" />
        <StatCard title="Prontas" value={String(resumo.pendentes)} hint="aptas para confirmação" tone="emerald" />
        <StatCard title="Com Erros" value={String(resumo.comErro)} hint="ainda exigem correção por linha" tone="red" />
      </div> : null}

      {canView && canList ? <Card className="shadow-sm">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <Filter className="size-4 text-primary" />
            Filtros de sessão
          </CardTitle>
          <CardDescription>Use os filtros para localizar implantações em andamento, confirmadas ou com erro.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 pt-4 md:grid-cols-[220px_1fr]">
          <div className="space-y-2">
            <Label>Status</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger>
                <SelectValue placeholder="Filtrar status" />
              </SelectTrigger>
              <SelectContent>
                {SESSION_STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Arquivo</Label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={arquivoNome}
                onChange={(event) => setArquivoNome(event.target.value)}
                placeholder="Buscar por nome do arquivo"
                className="pl-9"
              />
            </div>
          </div>
        </CardContent>
      </Card> : null}

      {canView && canList ? <Card className="shadow-sm">
        <CardHeader className="border-b">
          <CardTitle className="text-base">Sessões persistidas</CardTitle>
          <CardDescription>Cada sessão representa uma carga assistida e sua trilha de validação.</CardDescription>
        </CardHeader>
        <CardContent className="pt-4">
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-16 w-full" />
              ))}
            </div>
          ) : !sessoes.length ? (
            <SectionEmpty
              title="Nenhuma sessão encontrada"
              description="Inicie uma nova implantação a partir de um CSV legado para visualizar o preview, corrigir as linhas e confirmar o saldo inicial."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Arquivo</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Linhas</TableHead>
                  <TableHead>Estimado</TableHead>
                  <TableHead>Criada em</TableHead>
                  <TableHead className="text-right">Ação</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessoes.map((sessao) => (
                  <TableRow key={sessao.id}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-semibold">{sessao.arquivo_nome}</p>
                        <p className="text-xs text-muted-foreground">Hash {sessao.arquivo_hash.slice(0, 12)}...</p>
                      </div>
                    </TableCell>
                    <TableCell><StatusBadge status={sessao.status} /></TableCell>
                    <TableCell>
                      <div className="text-xs leading-5 text-muted-foreground">
                        <div>{sessao.total_linhas} total</div>
                        <div>{sessao.linhas_validas} válidas • {sessao.linhas_com_erro} erro • {sessao.linhas_com_aviso} aviso</div>
                      </div>
                    </TableCell>
                    <TableCell className="font-semibold">{formatCurrency(sessao.valor_total_estimado)}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{formatDateTime(sessao.criado_em)}</TableCell>
                    <TableCell className="text-right">
                      <Button asChild>
                        <Link href={`/suprimentos/estoque/implantacao-assistida/${sessao.id}`}>
                          Abrir <ChevronRight size={14} />
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card> : null}
    </div>
  );
}

export function ImplantacaoAssistidaNewPage() {
  const router = useRouter();
  const { activeFazendaId } = useAppStore();
  const canCreate = usePermission("estoque:implantacao_assistida:create");
  const [file, setFile] = useState<File | null>(null);
  const [mappingText, setMappingText] = useState("");
  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null);

  const previewMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Selecione um arquivo CSV para gerar a prévia.");
      const form = new FormData();
      form.append("file", file);
      const mapping = serializeMapping(mappingText);
      if (mapping) form.append("mapeamento", mapping);
      return apiFetch<PreviewResponse>("/estoque/implantacao-assistida/preview", {
        method: "POST",
        body: form,
      });
    },
    onSuccess: (response) => {
      setPreviewData(response);
      toast.success("Prévia gerada. Revise as colunas e as primeiras linhas antes de persistir a sessão.");
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Selecione um arquivo CSV para criar a sessão.");
      const form = new FormData();
      form.append("file", file);
      const mapping = serializeMapping(mappingText);
      if (mapping) form.append("mapeamento", mapping);
      if (activeFazendaId) form.append("unidade_produtiva_id", activeFazendaId);
      return apiFetch<ImplantacaoSessao>("/estoque/implantacao-assistida/sessoes", {
        method: "POST",
        body: form,
      });
    },
    onSuccess: (sessao) => {
      toast.success("Sessão persistida. Agora você pode corrigir linha a linha antes da confirmação.");
      router.push(`/suprimentos/estoque/implantacao-assistida/${sessao.id}`);
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  return (
    <div className="p-6 space-y-6 w-full">
      <PageHeader
        title="Nova Implantação Assistida"
        description="Envie um CSV legado, gere a prévia, persista a sessão e siga para a correção antes de gravar o saldo inicial."
        icon={<FileSpreadsheet className="size-4 text-primary" />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Suprimentos", href: "/suprimentos" },
          { label: "Estoque", href: "/suprimentos/estoque" },
          { label: "Implantação Assistida", href: "/suprimentos/estoque/implantacao-assistida" },
          { label: "Nova" },
        ]}
        actions={
          <Button variant="outline" onClick={() => void downloadTemplateCsv()}>
            <Download size={14} /> Baixar template
          </Button>
        }
      />

      {!canCreate ? (
        <SectionEmpty
          title="Acesso restrito"
          description="Seu perfil não possui permissão para iniciar uma implantação assistida de estoque."
        />
      ) : null}

      {canCreate ? <Card className="shadow-sm">
        <CardHeader className="border-b">
          <CardTitle className="text-base">Upload do legado</CardTitle>
          <CardDescription>Esta etapa aceita apenas CSV. Nenhum saldo é alterado até a confirmação final da sessão.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-5 pt-5 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-4">
            <div className="rounded-sm border border-dashed border-primary/30 bg-primary/5 p-5">
              <Label htmlFor="csv-upload" className="text-sm font-semibold">Arquivo CSV</Label>
              <Input
                id="csv-upload"
                type="file"
                accept=".csv,text/csv"
                className="mt-3"
                data-testid="implantacao-upload-input"
                onChange={(event) => {
                  const nextFile = event.target.files?.[0] ?? null;
                  setFile(nextFile);
                  setPreviewData(null);
                }}
              />
              <p className="mt-3 text-xs text-muted-foreground">
                Colunas suportadas: `produto_codigo`, `produto_nome`, `deposito_nome`, `quantidade`, `unidade`, `custo_unitario`, `lote`, `validade`, `observacoes`.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="mapping-json">Mapeamento opcional de colunas</Label>
              <Textarea
                id="mapping-json"
                value={mappingText}
                onChange={(event) => setMappingText(event.target.value)}
                placeholder='{"descricao":"produto_nome","almoxarifado":"deposito_nome","saldo":"quantidade"}'
                className="min-h-32 font-mono text-xs"
              />
              <p className="text-xs text-muted-foreground">Use apenas quando o arquivo legado não puder ser reconhecido pelos aliases automáticos.</p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button data-testid="implantacao-gerar-previa" onClick={() => previewMutation.mutate()} disabled={!file || previewMutation.isPending}>
                {previewMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : <Eye size={14} />}
                Gerar prévia
              </Button>
              <Button
                variant="outline"
                onClick={() => createMutation.mutate()}
                disabled={!file || createMutation.isPending || !previewData}
                data-testid="implantacao-persistir-sessao"
              >
                {createMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : <FileUp size={14} />}
                Persistir sessão
              </Button>
            </div>
          </div>

          <Card className="border-slate-200 bg-slate-50/70 shadow-none">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-wide">Regra operacional</CardTitle>
              <CardDescription className="text-sm">
                A implantação assistida grava <strong>SALDO_INICIAL</strong>. Ela não gera entrada manual, ajuste operacional ou consumo agrícola.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <div className="flex gap-3 rounded-sm border border-amber-200 bg-amber-50 p-3 text-amber-900">
                <TriangleAlert className="mt-0.5 size-4 shrink-0" />
                <p>Persistir a sessão não grava estoque. A gravação definitiva só ocorre no passo de confirmação da sessão apta.</p>
              </div>
              <div className="flex gap-3 rounded-sm border border-sky-200 bg-sky-50 p-3 text-sky-900">
                <ShieldCheck className="mt-0.5 size-4 shrink-0" />
                <p>O parser e a validação já respeitam o `tenant_id` e o contexto da unidade produtiva quando aplicado ao depósito.</p>
              </div>
            </CardContent>
          </Card>
        </CardContent>
      </Card> : null}

      {canCreate && previewData && (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <StatCard title="Linhas" value={String(previewData.total_linhas)} hint="linhas analisadas no CSV" />
            <StatCard title="Válidas" value={String(previewData.linhas_validas)} hint="prontas para sessão" tone="emerald" />
            <StatCard title="Com Aviso" value={String(previewData.linhas_com_aviso)} hint="exigem revisão opcional" tone="amber" />
            <StatCard title="Com Erro" value={String(previewData.linhas_com_erro)} hint="bloqueiam a confirmação" tone="red" />
          </div>

          <Card className="shadow-sm">
            <CardHeader className="border-b">
              <CardTitle className="text-base">Prévia do upload</CardTitle>
              <CardDescription>Revise a estrutura, o mapeamento efetivo e as primeiras linhas detectadas antes de persistir a sessão.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-sm border p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Arquivo</p>
                  <p className="mt-2 font-semibold">{previewData.arquivo_nome}</p>
                </div>
                <div className="rounded-sm border p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Colunas detectadas</p>
                  <p className="mt-2 text-sm">{previewData.colunas_detectadas.join(", ") || "—"}</p>
                </div>
                <div className="rounded-sm border p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Valor estimado</p>
                  <p className="mt-2 font-semibold">{formatCurrency(previewData.valor_total_estimado)}</p>
                </div>
              </div>

              {!!previewData.erros_arquivo.length && (
                <div className="rounded-sm border border-red-200 bg-red-50 p-4">
                  <p className="text-sm font-semibold text-red-800">Erros de arquivo</p>
                  <ul className="mt-2 space-y-1 text-sm text-red-700">
                    {previewData.erros_arquivo.map((erro, index) => (
                      <li key={`${erro.codigo}-${index}`}>{erro.mensagem}</li>
                    ))}
                  </ul>
                </div>
              )}

              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Linha</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Produto</TableHead>
                    <TableHead>Depósito</TableHead>
                    <TableHead>Quantidade</TableHead>
                    <TableHead>Custo</TableHead>
                    <TableHead>Mensagens</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {previewData.itens.slice(0, 12).map((item) => (
                    <TableRow key={item.numero_linha}>
                      <TableCell className="font-semibold">{item.numero_linha}</TableCell>
                      <TableCell><StatusBadge status={item.status} /></TableCell>
                      <TableCell>{String(item.dados_normalizados.produto_nome || item.dados_normalizados.produto_codigo || "—")}</TableCell>
                      <TableCell>{String(item.dados_normalizados.deposito_nome || "—")}</TableCell>
                      <TableCell>{String(item.dados_normalizados.quantidade || "—")}</TableCell>
                      <TableCell>{String(item.dados_normalizados.custo_unitario || "—")}</TableCell>
                      <TableCell className="max-w-sm text-xs text-muted-foreground">
                        {[...item.erros, ...item.avisos].map((mensagem) => mensagem.mensagem).join(" • ") || "Sem mensagens"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function ItemCorrectionDialog({
  item,
  produtos,
  depositos,
  open,
  onOpenChange,
  onSave,
  locked,
}: {
  item: ImplantacaoItem | null;
  produtos: Produto[];
  depositos: Deposito[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (payload: Record<string, unknown>) => Promise<void>;
  locked: boolean;
}) {
  const [produtoId, setProdutoId] = useState<string>("");
  const [depositoId, setDepositoId] = useState<string>("");
  const [quantidade, setQuantidade] = useState<string>("");
  const [custoUnitario, setCustoUnitario] = useState<string>("");
  const [lote, setLote] = useState<string>("");
  const [validade, setValidade] = useState<string>("");
  const [observacoes, setObservacoes] = useState<string>("");
  const [ignorado, setIgnorado] = useState<boolean>(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!item) return;
    setProdutoId(item.produto_id_resolvido || "");
    setDepositoId(item.deposito_id_resolvido || "");
    setQuantidade(item.dados_normalizados.quantidade ? String(item.dados_normalizados.quantidade) : "");
    setCustoUnitario(item.dados_normalizados.custo_unitario ? String(item.dados_normalizados.custo_unitario) : "");
    setLote(item.dados_normalizados.lote ? String(item.dados_normalizados.lote) : "");
    setValidade(item.dados_normalizados.validade ? String(item.dados_normalizados.validade) : "");
    setObservacoes(item.dados_normalizados.observacoes ? String(item.dados_normalizados.observacoes) : "");
    setIgnorado(item.ignorado);
  }, [item]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl">
        <DialogHeader className="border-b pb-4">
          <DialogTitle className="flex items-center gap-2 text-base">
            Corrigir linha {item?.numero_linha}
            {item && <StatusBadge status={item.status} />}
          </DialogTitle>
        </DialogHeader>
        {item && (
          <div className="grid gap-6 px-6 pb-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Produto resolvido</Label>
                  <Select value={produtoId || "SEM_PRODUTO"} onValueChange={(value) => setProdutoId(value === "SEM_PRODUTO" ? "" : value)}>
                    <SelectTrigger>
                      <SelectValue placeholder="Selecionar produto" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="SEM_PRODUTO">Sem produto</SelectItem>
                      {produtos.map((produto) => (
                        <SelectItem key={produto.id} value={produto.id}>
                          {produto.nome}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Depósito resolvido</Label>
                  <Select value={depositoId || "SEM_DEPOSITO"} onValueChange={(value) => setDepositoId(value === "SEM_DEPOSITO" ? "" : value)}>
                    <SelectTrigger>
                      <SelectValue placeholder="Selecionar depósito" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="SEM_DEPOSITO">Sem depósito</SelectItem>
                      {depositos.map((deposito) => (
                        <SelectItem key={deposito.id} value={deposito.id}>
                          {deposito.nome}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Quantidade</Label>
                  <Input data-testid="implantacao-campo-quantidade" value={quantidade} onChange={(event) => setQuantidade(event.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Custo unitário</Label>
                  <Input data-testid="implantacao-campo-custo-unitario" value={custoUnitario} onChange={(event) => setCustoUnitario(event.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Lote</Label>
                  <Input value={lote} onChange={(event) => setLote(event.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Validade</Label>
                  <Input type="date" value={validade} onChange={(event) => setValidade(event.target.value)} />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Observações</Label>
                <Textarea value={observacoes} onChange={(event) => setObservacoes(event.target.value)} className="min-h-24" />
              </div>
              <div className="flex items-center gap-3 rounded-sm border bg-slate-50 px-3 py-3">
                <Checkbox checked={ignorado} onCheckedChange={setIgnorado} disabled={locked} />
                <div>
                  <p className="text-sm font-semibold">Ignorar linha</p>
                  <p className="text-xs text-muted-foreground">Itens ignorados não entram na confirmação do saldo inicial.</p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <Card className="border-slate-200 shadow-none">
                <CardHeader>
                  <CardTitle className="text-sm">Origem do arquivo</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-xs text-muted-foreground">
                  {Object.entries(item.payload_original).map(([key, value]) => (
                    <div key={key} className="flex justify-between gap-3 border-b pb-2 last:border-b-0 last:pb-0">
                      <span className="font-semibold text-foreground">{key}</span>
                      <span className="text-right">{value || "—"}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {!!item.erros.length && (
                <div className="rounded-sm border border-red-200 bg-red-50 p-4">
                  <p className="text-sm font-semibold text-red-800">Erros</p>
                  <ul className="mt-2 space-y-1 text-sm text-red-700">
                    {item.erros.map((erro, index) => (
                      <li key={`${erro.codigo}-${index}`}>{erro.mensagem}</li>
                    ))}
                  </ul>
                </div>
              )}

              {!!item.avisos.length && (
                <div className="rounded-sm border border-amber-200 bg-amber-50 p-4">
                  <p className="text-sm font-semibold text-amber-900">Avisos</p>
                  <ul className="mt-2 space-y-1 text-sm text-amber-800">
                    {item.avisos.map((aviso, index) => (
                      <li key={`${aviso.codigo}-${index}`}>{aviso.mensagem}</li>
                    ))}
                  </ul>
                </div>
              )}

              {!!Object.keys(item.sugestoes).length && (
                <div className="rounded-sm border border-sky-200 bg-sky-50 p-4">
                  <p className="text-sm font-semibold text-sky-900">Sugestões do parser</p>
                  <div className="mt-2 space-y-2 text-sm text-sky-900">
                    {Object.entries(item.sugestoes).map(([campo, sugestoes]) => (
                      <div key={campo}>
                        <p className="font-semibold">{campo}</p>
                        <p>{sugestoes.join(", ") || "Sem sugestões"}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
        <DialogFooter className="border-t px-6 pb-6 pt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>Fechar</Button>
          <Button
            data-testid="implantacao-salvar-correcao"
            disabled={!item || locked || saving}
            onClick={async () => {
              if (!item) return;
              setSaving(true);
              try {
                await onSave({
                  produto_id_resolvido: produtoId || null,
                  deposito_id_resolvido: depositoId || null,
                  quantidade: quantidade ? Number(quantidade) : null,
                  custo_unitario: custoUnitario ? Number(custoUnitario) : null,
                  lote: lote || null,
                  validade: validade || null,
                  observacoes: observacoes || null,
                  ignorado,
                });
                onOpenChange(false);
              } finally {
                setSaving(false);
              }
            }}
          >
            {saving ? <Loader2 className="size-4 animate-spin" /> : null}
            Salvar correção
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ImplantacaoAssistidaDetailPage({ sessionId }: { sessionId: string }) {
  const queryClient = useQueryClient();
  const { activeFazendaId } = useAppStore();
  const canView = usePermission("estoque:implantacao_assistida:view");
  const canEdit = usePermission("estoque:implantacao_assistida:edit");
  const canApprove = usePermission("estoque:implantacao_assistida:approve");
  const canCancel = usePermission("estoque:implantacao_assistida:delete");
  const [itemStatusFilter, setItemStatusFilter] = useState("TODOS");
  const [somenteErros, setSomenteErros] = useState(false);
  const [somenteAvisos, setSomenteAvisos] = useState(false);
  const [ignoradoFilter, setIgnoradoFilter] = useState("TODOS");
  const [editingItem, setEditingItem] = useState<ImplantacaoItem | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [confirmSaldoInicial, setConfirmSaldoInicial] = useState(false);
  const [confirmAvisos, setConfirmAvisos] = useState(false);
  const [confirmObservacao, setConfirmObservacao] = useState("");

  const fazendaParam = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";

  const { data: session, isLoading: loadingSession } = useQuery<ImplantacaoSessao>({
    queryKey: ["estoque-implantacao-sessao", sessionId],
    enabled: canView,
    queryFn: () => apiFetch(`/estoque/implantacao-assistida/sessoes/${sessionId}`, { params: { limit: 20, offset: 0 } }),
  });

  const { data: itemsData, isLoading: loadingItems } = useQuery<ItemListResponse>({
    queryKey: ["estoque-implantacao-itens", sessionId, itemStatusFilter, somenteErros, somenteAvisos, ignoradoFilter],
    enabled: canView,
    queryFn: () =>
      apiFetch(`/estoque/implantacao-assistida/sessoes/${sessionId}/itens`, {
        params: {
          status: itemStatusFilter === "TODOS" ? undefined : itemStatusFilter,
          somente_erros: somenteErros || undefined,
          somente_avisos: somenteAvisos || undefined,
          ignorado: ignoradoFilter === "TODOS" ? undefined : ignoradoFilter === "SIM",
          limit: 100,
          offset: 0,
        },
      }),
  });

  const { data: aptidao, isLoading: loadingAptidao } = useQuery<AptidaoConfirmacao>({
    queryKey: ["estoque-implantacao-aptidao", sessionId],
    enabled: canView,
    queryFn: () => apiFetch(`/estoque/implantacao-assistida/sessoes/${sessionId}/aptidao-confirmacao`),
  });

  const { data: produtos = [] } = useQuery<Produto[]>({
    queryKey: ["implantacao-produtos"],
    queryFn: () => apiFetch("/cadastros/produtos?ativo=true"),
  });

  const { data: depositos = [] } = useQuery<Deposito[]>({
    queryKey: ["implantacao-depositos", activeFazendaId],
    queryFn: () => apiFetch(`/estoque/depositos${fazendaParam}`),
  });

  const locked = session?.status === "CONFIRMADO" || session?.status === "CANCELADO";
  const items = itemsData?.itens ?? [];

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ["estoque-implantacao-sessao", sessionId] });
    queryClient.invalidateQueries({ queryKey: ["estoque-implantacao-itens", sessionId] });
    queryClient.invalidateQueries({ queryKey: ["estoque-implantacao-aptidao", sessionId] });
    queryClient.invalidateQueries({ queryKey: ["estoque-implantacao-sessoes"] });
  };

  const patchItemMutation = useMutation({
    mutationFn: ({ itemId, payload }: { itemId: string; payload: Record<string, unknown> }) =>
      apiFetch(`/estoque/implantacao-assistida/sessoes/${sessionId}/itens/${itemId}`, {
        method: "PATCH",
        body: payload,
      }),
    onSuccess: () => {
      toast.success("Linha corrigida. O resumo da sessão foi recalculado.");
      refreshAll();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const revalidateMutation = useMutation({
    mutationFn: () =>
      apiFetch(`/estoque/implantacao-assistida/sessoes/${sessionId}/revalidar`, {
        method: "POST",
      }),
    onSuccess: () => {
      toast.success("Sessão revalidada.");
      refreshAll();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const cancelMutation = useMutation({
    mutationFn: () =>
      apiFetch(`/estoque/implantacao-assistida/sessoes/${sessionId}/cancelar`, {
        method: "POST",
      }),
    onSuccess: () => {
      toast.success("Sessão cancelada. A carga ficou bloqueada para novas alterações.");
      setCancelOpen(false);
      refreshAll();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const confirmMutation = useMutation({
    mutationFn: () =>
      apiFetch(`/estoque/implantacao-assistida/sessoes/${sessionId}/confirmar`, {
        method: "POST",
        body: {
          confirmar_avisos: confirmAvisos,
          observacao: confirmObservacao || null,
        },
      }),
    onSuccess: () => {
      toast.success("Implantação confirmada. O saldo inicial foi gravado no histórico oficial.");
      setConfirmOpen(false);
      setConfirmSaldoInicial(false);
      setConfirmAvisos(false);
      setConfirmObservacao("");
      refreshAll();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  return (
    <div className="p-6 space-y-6 w-full">
      <PageHeader
        title="Sessão de Implantação Assistida"
        description="Corrija as linhas persistidas, revalide a sessão e confirme apenas quando a aptidão estiver liberada para SALDO_INICIAL."
        icon={<Warehouse className="size-4 text-primary" />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Suprimentos", href: "/suprimentos" },
          { label: "Estoque", href: "/suprimentos/estoque" },
          { label: "Implantação Assistida", href: "/suprimentos/estoque/implantacao-assistida" },
          { label: session?.arquivo_nome || "Sessão" },
        ]}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => setCancelOpen(true)} disabled={!canCancel || locked || cancelMutation.isPending || loadingSession}>
              <Ban size={14} /> Cancelar sessão
            </Button>
            <Button variant="outline" onClick={() => revalidateMutation.mutate()} disabled={!canEdit || locked || revalidateMutation.isPending || loadingSession}>
              {revalidateMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw size={14} />}
              Revalidar
            </Button>
            <Button data-testid="implantacao-abrir-confirmacao" onClick={() => setConfirmOpen(true)} disabled={!canApprove || !aptidao?.apta || locked || confirmMutation.isPending}>
              <ShieldCheck size={14} /> Confirmar saldo inicial
            </Button>
          </div>
        }
      />

      {!canView ? (
        <SectionEmpty
          title="Acesso restrito"
          description="Seu perfil não possui permissão para consultar esta sessão de Implantação Assistida."
        />
      ) : null}

      {canView && loadingSession ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-80 w-full" />
        </div>
      ) : canView && !session ? (
        <SectionEmpty title="Sessão não encontrada" description="Verifique o identificador informado ou retorne para a listagem de implantações." />
      ) : canView && session ? (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <StatCard title="Status" value={SESSION_STATUS_LABELS[session.status]} hint="situação atual da sessão" tone={session.status === "CONFIRMADO" ? "sky" : session.linhas_com_erro > 0 ? "red" : session.linhas_com_aviso > 0 ? "amber" : "emerald"} />
            <StatCard title="Itens" value={String(session.total_linhas)} hint={`${session.linhas_validas} válidos, ${session.linhas_com_erro} erro, ${session.linhas_com_aviso} aviso`} />
            <StatCard title="Estimado" value={formatCurrency(session.valor_total_estimado)} hint="valor calculado a partir das linhas persistidas" tone="emerald" />
            <StatCard title="Confirmada em" value={session.confirmado_em ? formatDateTime(session.confirmado_em) : "—"} hint={session.confirmado_por ? `usuário ${session.confirmado_por}` : "ainda não confirmada"} tone="sky" />
          </div>

          <div className="grid gap-4 xl:grid-cols-[1.3fr_0.7fr]">
            <Card className="shadow-sm">
              <CardHeader className="border-b">
                <CardTitle className="text-base">Resumo da sessão</CardTitle>
                <CardDescription>
                  Arquivo <strong>{session.arquivo_nome}</strong>, criado em {formatDateTime(session.criado_em)}. Esta trilha é auditável e separada da operação normal.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 pt-4 md:grid-cols-2">
                <div className="rounded-sm border p-4">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Colunas detectadas</p>
                  <p className="mt-2 text-sm">{session.colunas_detectadas.join(", ") || "—"}</p>
                </div>
                <div className="rounded-sm border p-4">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Mapeamento utilizado</p>
                  <div className="mt-2 space-y-1 text-sm">
                    {Object.entries(session.mapeamento_colunas).map(([origem, destino]) => (
                      <div key={origem}>
                        <strong>{origem}</strong> <span className="text-muted-foreground">→</span> {destino}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="rounded-sm border p-4 md:col-span-2">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Pós-confirmação</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button asChild variant="outline">
                      <Link href={`/suprimentos/estoque?aba=historico&origem_tipo=IMPLANTACAO&origem_id=${session.id}`}>
                        <Warehouse size={14} /> Ver movimentações
                      </Link>
                    </Button>
                    <Button asChild variant="outline">
                      <Link href="/suprimentos/saldos">
                        <PackageCheck size={14} /> Conferir saldos
                      </Link>
                    </Button>
                    <Button asChild variant="outline">
                      <Link href={`/suprimentos/estoque/implantacao-assistida/${session.id}/auditoria`}>
                        <ShieldCheck size={14} /> Ver auditoria
                      </Link>
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-sm">
              <CardHeader className="border-b">
                <CardTitle className="flex items-center gap-2 text-base">
                  <ShieldCheck className="size-4 text-primary" />
                  Aptidão para confirmação
                </CardTitle>
                <CardDescription>
                  A confirmação grava <strong>SALDO_INICIAL</strong> com origem <strong>IMPLANTACAO</strong>.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 pt-4">
                {loadingAptidao ? (
                  <Skeleton className="h-40 w-full" />
                ) : aptidao ? (
                  <>
                    <div className={cn("rounded-sm border p-4", aptidao.apta ? "border-emerald-200 bg-emerald-50" : "border-red-200 bg-red-50")}>
                      <div className="flex items-start gap-3">
                        {aptidao.apta ? (
                          <CheckCircle2 className="mt-0.5 size-5 text-emerald-700" />
                        ) : (
                          <CircleAlert className="mt-0.5 size-5 text-red-700" />
                        )}
                        <div>
                          <p className={cn("text-sm font-semibold", aptidao.apta ? "text-emerald-900" : "text-red-900")}>
                            {aptidao.apta ? "Sessão apta para confirmação" : "Sessão ainda bloqueada"}
                          </p>
                          <p className={cn("mt-1 text-sm", aptidao.apta ? "text-emerald-800" : "text-red-800")}>
                            {aptidao.total_itens_confirmaveis} itens confirmáveis • {formatCurrency(aptidao.valor_total_confirmavel)}
                          </p>
                        </div>
                      </div>
                    </div>

                    {!!aptidao.erros_bloqueantes.length && (
                      <div className="rounded-sm border border-red-200 bg-red-50 p-4">
                        <p className="text-sm font-semibold text-red-900">Bloqueios</p>
                        <ul className="mt-2 space-y-1 text-sm text-red-800">
                          {aptidao.erros_bloqueantes.map((erro) => (
                            <li key={erro}>{erro}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {!!aptidao.avisos.length && (
                      <div className="rounded-sm border border-amber-200 bg-amber-50 p-4">
                        <p className="text-sm font-semibold text-amber-900">Avisos</p>
                        <ul className="mt-2 space-y-1 text-sm text-amber-800">
                          {aptidao.avisos.map((aviso) => (
                            <li key={aviso}>{aviso}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                ) : null}
              </CardContent>
            </Card>
          </div>

          <Card className="shadow-sm">
            <CardHeader className="border-b">
              <CardTitle className="text-base">Linhas persistidas</CardTitle>
              <CardDescription>Corrija produto, depósito, quantidade e custo por linha. Após confirmação, a edição é bloqueada.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              <div className="grid gap-4 lg:grid-cols-[220px_220px_220px_1fr]">
                <div className="space-y-2">
                  <Label>Status do item</Label>
                  <Select value={itemStatusFilter} onValueChange={setItemStatusFilter}>
                    <SelectTrigger>
                      <SelectValue placeholder="Filtrar item" />
                    </SelectTrigger>
                    <SelectContent>
                      {ITEM_STATUS_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Atalhos</Label>
                  <div className="flex gap-2">
                    <Button variant={somenteErros ? "default" : "outline"} onClick={() => { setSomenteErros((current) => !current); if (!somenteErros) setSomenteAvisos(false); }}>
                      <AlertTriangle size={14} /> Erros
                    </Button>
                    <Button variant={somenteAvisos ? "default" : "outline"} onClick={() => { setSomenteAvisos((current) => !current); if (!somenteAvisos) setSomenteErros(false); }}>
                      <TriangleAlert size={14} /> Avisos
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Ignorado</Label>
                  <Select value={ignoradoFilter} onValueChange={setIgnoradoFilter}>
                    <SelectTrigger>
                      <SelectValue placeholder="Ignorado" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="TODOS">Todos</SelectItem>
                      <SelectItem value="SIM">Ignorados</SelectItem>
                      <SelectItem value="NAO">Ativos</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="rounded-sm border border-slate-200 bg-slate-50 p-3 text-xs text-muted-foreground">
                  <strong className="text-foreground">Regra de UX:</strong> linhas com <span className="font-semibold text-red-700">ERRO</span> bloqueiam a confirmação; <span className="font-semibold text-amber-800">AVISO</span> exige aceite explícito; <span className="font-semibold text-emerald-700">VALIDA/CORRIGIDO</span> segue para SALDO_INICIAL.
                </div>
              </div>

              {loadingItems ? (
                <div className="space-y-3">
                  {Array.from({ length: 4 }).map((_, index) => (
                    <Skeleton key={index} className="h-16 w-full" />
                  ))}
                </div>
              ) : !items.length ? (
                <SectionEmpty title="Nenhum item no filtro atual" description="Ajuste os filtros para voltar a enxergar as linhas da sessão." />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Linha</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Produto</TableHead>
                      <TableHead>Depósito</TableHead>
                      <TableHead>Quantidade</TableHead>
                      <TableHead>Custo</TableHead>
                      <TableHead>Mensagens</TableHead>
                      <TableHead className="text-right">Correção</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {items.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="font-semibold">{item.numero_linha}</TableCell>
                        <TableCell><StatusBadge status={item.status} /></TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            <p>{String(item.dados_normalizados.produto_nome_resolvido || item.dados_normalizados.produto_nome_original || item.dados_normalizados.produto_codigo_original || "—")}</p>
                            {item.produto_id_resolvido ? (
                              <p className="text-xs text-muted-foreground">{item.produto_id_resolvido}</p>
                            ) : null}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            <p>{String(item.dados_normalizados.deposito_nome_resolvido || item.dados_normalizados.deposito_nome || "—")}</p>
                            {item.deposito_id_resolvido ? (
                              <p className="text-xs text-muted-foreground">{item.deposito_id_resolvido}</p>
                            ) : null}
                          </div>
                        </TableCell>
                        <TableCell>{String(item.dados_normalizados.quantidade || "—")}</TableCell>
                        <TableCell>{item.dados_normalizados.custo_unitario ? formatCurrency(Number(item.dados_normalizados.custo_unitario)) : "—"}</TableCell>
                        <TableCell className="max-w-md text-xs text-muted-foreground">
                          {[...item.erros, ...item.avisos].map((mensagem) => mensagem.mensagem).join(" • ") || "Sem mensagens"}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button data-testid={`implantacao-corrigir-item-${item.numero_linha}`} variant="outline" onClick={() => setEditingItem(item)} disabled={!canEdit || locked}>
                            Corrigir
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <ItemCorrectionDialog
            item={editingItem}
            produtos={produtos}
            depositos={depositos}
            open={!!editingItem}
            onOpenChange={(open) => !open && setEditingItem(null)}
            locked={locked}
            onSave={async (payload) => {
              if (!editingItem) return;
              await patchItemMutation.mutateAsync({ itemId: editingItem.id, payload });
            }}
          />

          <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
            <AlertDialogContent className="max-w-lg">
              <AlertDialogHeader>
                <AlertDialogTitle>Confirmar implantação assistida?</AlertDialogTitle>
                <AlertDialogDescription>
                  Esta operação grava <strong>SALDO_INICIAL</strong> no histórico oficial com origem <strong>IMPLANTACAO</strong>. Ela não cria entrada operacional comum.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <div className="space-y-4 px-1 text-sm">
                <div className="rounded-sm border border-amber-200 bg-amber-50 p-4 text-amber-900">
                  <p className="font-semibold">Aviso operacional</p>
                  <p className="mt-1">
                    Após confirmar, a sessão ficará bloqueada para edição e a conferência deve ser feita em saldos/movimentações.
                  </p>
                </div>
                <div className="space-y-3">
                  <label className="flex items-start gap-3 rounded-sm border p-3">
                    <Checkbox data-testid="implantacao-confirmar-saldo-checkbox" checked={confirmSaldoInicial} onCheckedChange={setConfirmSaldoInicial} />
                    <span>
                      Confirmo que esta carga será gravada como <strong>SALDO_INICIAL</strong> e não como entrada operacional.
                    </span>
                  </label>
                  {!!aptidao?.avisos.length && (
                    <label className="flex items-start gap-3 rounded-sm border p-3">
                      <Checkbox data-testid="implantacao-confirmar-avisos-checkbox" checked={confirmAvisos} onCheckedChange={setConfirmAvisos} />
                      <span>Há avisos pendentes. Confirmo que desejo prosseguir mesmo assim.</span>
                    </label>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirm-observacao">Observação da confirmação</Label>
                  <Textarea
                    id="confirm-observacao"
                    value={confirmObservacao}
                    onChange={(event) => setConfirmObservacao(event.target.value)}
                    placeholder="Ex: Carga inicial validada pelo responsável do almoxarifado."
                  />
                </div>
              </div>
              <AlertDialogFooter>
                <AlertDialogCancel onClick={() => {
                  setConfirmSaldoInicial(false);
                  setConfirmAvisos(false);
                }}>
                  Cancelar
                </AlertDialogCancel>
                <AlertDialogAction
                  data-testid="implantacao-confirmar-final"
                  disabled={!confirmSaldoInicial || (!!aptidao?.avisos.length && !confirmAvisos) || confirmMutation.isPending || !aptidao?.apta}
                  onClick={() => confirmMutation.mutate()}
                >
                  {confirmMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
                  Confirmar saldo inicial
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>

          <AlertDialog open={cancelOpen} onOpenChange={setCancelOpen}>
            <AlertDialogContent className="max-w-lg">
              <AlertDialogHeader>
                <AlertDialogTitle>Cancelar sessão de implantação?</AlertDialogTitle>
                <AlertDialogDescription>
                  O cancelamento não apaga os dados, mas bloqueia correções e confirmação futura desta sessão.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Voltar</AlertDialogCancel>
                <AlertDialogAction
                  data-testid="implantacao-cancelar-sessao"
                  disabled={cancelMutation.isPending}
                  onClick={() => cancelMutation.mutate()}
                >
                  {cancelMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
                  Cancelar sessão
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </>
      ) : null}
    </div>
  );
}

export function ImplantacaoAssistidaAuditPage({ sessionId }: { sessionId: string }) {
  const canViewAudit = usePermission("tenant:audit:view");
  const { data, isLoading } = useQuery<AuditLogListResponse>({
    queryKey: ["estoque-implantacao-auditoria", sessionId],
    enabled: canViewAudit,
    queryFn: () =>
      apiFetch("/audit-log", {
        params: {
          resource: "estoque_implantacao_sessoes",
          resource_id: sessionId,
          page: 1,
          page_size: 50,
        },
      }),
  });

  const logs = data?.items ?? [];

  return (
    <div className="p-6 space-y-6 w-full">
      <PageHeader
        title="Auditoria da Implantação"
        description="Trilha tenant-scoped da sessão de implantação assistida."
        icon={<ShieldCheck className="size-4 text-primary" />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Suprimentos", href: "/suprimentos" },
          { label: "Estoque", href: "/suprimentos/estoque" },
          { label: "Implantação Assistida", href: "/suprimentos/estoque/implantacao-assistida" },
          { label: "Auditoria" },
        ]}
        actions={
          <Button asChild variant="outline">
            <Link href={`/suprimentos/estoque/implantacao-assistida/${sessionId}`}>Voltar à sessão</Link>
          </Button>
        }
      />

      {!canViewAudit ? (
        <SectionEmpty
          title="Acesso restrito"
          description="Seu perfil não possui permissão para consultar a auditoria do tenant."
        />
      ) : null}

      {canViewAudit ? (
        <Card className="shadow-sm">
          <CardHeader className="border-b">
            <CardTitle className="text-base">Eventos da sessão</CardTitle>
            <CardDescription>Criação, correções, revalidação, cancelamento e confirmação.</CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            {isLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-14 w-full" />
                ))}
              </div>
            ) : !logs.length ? (
              <SectionEmpty
                title="Nenhum log encontrado"
                description="Ainda não há eventos de auditoria registrados para esta sessão."
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Quando</TableHead>
                    <TableHead>Ação</TableHead>
                    <TableHead>Recurso</TableHead>
                    <TableHead>Usuário</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {logs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell>{formatDateTime(log.created_at)}</TableCell>
                      <TableCell className="font-semibold">{log.action}</TableCell>
                      <TableCell>{log.resource}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{log.user_id || "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
