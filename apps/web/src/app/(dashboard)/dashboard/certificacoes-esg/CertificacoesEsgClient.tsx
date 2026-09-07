"use client";

import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import {
  AlertCircle,
  ClipboardList,
  FileCheck2,
  FilePlus2,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";
import { StatCard } from "@/components/shared/stat-card";
import { Skeleton } from "@/components/ui/skeleton";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  useCriarEvidencia,
  useCriarNaoConformidade,
  useCriarPlanoAcao,
  useAtualizarNaoConformidadeStatus,
  useAtualizarPlanoAcaoStatus,
  useCertificacoesEsgEvidencias,
  useCertificacoesEsgNaoConformidades,
  useCertificacoesEsgPlanosAcao,
  useCertificacoesEsgProgramas,
  useCriarPrograma,
  useAtualizarPrograma,
} from "@/lib/hooks/use-certificacoes-esg";
import type {
  EvidenciaCertificacao,
  NaoConformidadeCertificacao,
  PlanoAcaoCertificacao,
  PrioridadePlanoAcao,
  SeveridadeNaoConformidade,
  StatusNaoConformidade,
  StatusPlanoAcao,
  TipoEvidencia,
  ProgramaCertificacao,
  TipoCertificacao,
} from "@/services/certificacoes-esg/service";
import { cn } from "@/lib/utils";

const NaoConformidadeLabels: Record<string, string> = {
  ABERTA: "Aberta",
  EM_ANALISE: "Em análise",
  EM_CORRECAO: "Em correção",
  RESOLVIDA: "Resolvida",
  CANCELADA: "Cancelada",
};

const PlanoAcaoLabels: Record<string, string> = {
  PENDENTE: "Pendente",
  EM_ANDAMENTO: "Em andamento",
  CONCLUIDO: "Concluído",
  ATRASADO: "Atrasado",
  CANCELADO: "Cancelado",
};

function domainStatusClass(status: string) {
  if (status === "RESOLVIDA" || status === "CONCLUIDO") return "bg-emerald-500/10 text-emerald-700 border-emerald-500/20";
  if (status === "EM_ANALISE" || status === "EM_ANDAMENTO") return "bg-blue-500/10 text-blue-700 border-blue-500/20";
  if (status === "EM_CORRECAO" || status === "PENDENTE") return "bg-amber-500/10 text-amber-700 border-amber-500/20";
  if (status === "ATRASADO") return "bg-orange-500/10 text-orange-700 border-orange-500/20";
  if (status === "CANCELADA" || status === "CANCELADO") return "bg-red-500/10 text-red-700 border-red-500/20";
  return "bg-muted text-muted-foreground border-muted";
}

function isoNow() {
  return new Date().toISOString();
}

function pendenteOuAtrasado(plano: PlanoAcaoCertificacao) {
  if (plano.status === "PENDENTE" || plano.status === "ATRASADO") return true;
  if (plano.status === "CANCELADO" || plano.status === "CONCLUIDO") return false;
  return new Date(plano.prazo).getTime() < Date.now();
}

function SectionShell({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="border-b">
        <CardTitle className="text-base">{title}</CardTitle>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardHeader>
      <CardContent className="p-4">{children}</CardContent>
    </Card>
  );
}

function datetimeLocalNow(offsetDays = 0) {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 16);
}

const evidenciaTipos: TipoEvidencia[] = ["DOCUMENTO_PDF", "FOTO_CAMPO", "DADO_SATELITE", "OUTRO"];
const naoConformidadeSeveridades: SeveridadeNaoConformidade[] = ["MENOR", "MAIOR", "CRITICA"];
const naoConformidadeStatus: StatusNaoConformidade[] = ["ABERTA", "EM_ANALISE", "EM_CORRECAO", "RESOLVIDA", "CANCELADA"];
const planoPrioridades: PrioridadePlanoAcao[] = ["BAIXA", "MEDIA", "ALTA", "URGENTE"];
const planoStatus: StatusPlanoAcao[] = ["PENDENTE", "EM_ANDAMENTO", "CONCLUIDO", "ATRASADO", "CANCELADO"];

const evidenciaFormSchema = z.object({
  programa_id: z.string().min(1, "Programa obrigatório"),
  tipo_evidencia: z.enum(["DOCUMENTO_PDF", "FOTO_CAMPO", "DADO_SATELITE", "OUTRO"]),
  titulo: z.string().min(1, "Título obrigatório").max(160),
  descricao: z.string().min(1, "Descrição obrigatória").max(1000),
  origem_tipo: z.string().min(1, "Origem obrigatória").max(80),
  origem_id: z.string().min(1, "Origem obrigatória").max(80),
  publico: z.boolean().default(false),
});

const naoConformidadeFormSchema = z.object({
  programa_id: z.string().min(1, "Programa obrigatório"),
  titulo: z.string().min(1, "Título obrigatório").max(160),
  descricao: z.string().min(1, "Descrição obrigatória").max(1000),
  severidade: z.enum(["MENOR", "MAIOR", "CRITICA"]),
  status: z.enum(["ABERTA", "EM_ANALISE", "EM_CORRECAO", "RESOLVIDA", "CANCELADA"]),
  detectada_em: z.string().min(1, "Data de detecção obrigatória"),
  prazo_correcao: z.string().optional().default(""),
});

const planoAcaoFormSchema = z.object({
  programa_id: z.string().min(1, "Programa obrigatório"),
  titulo: z.string().min(1, "Título obrigatório").max(160),
  descricao: z.string().min(1, "Descrição obrigatória").max(1000),
  prioridade: z.enum(["BAIXA", "MEDIA", "ALTA", "URGENTE"]),
  status: z.enum(["PENDENTE", "EM_ANDAMENTO", "CONCLUIDO", "ATRASADO", "CANCELADO"]),
  prazo: z.string().min(1, "Prazo obrigatório"),
});

type EvidenceFormValues = z.infer<typeof evidenciaFormSchema>;
type NaoConformidadeFormValues = z.infer<typeof naoConformidadeFormSchema>;
type PlanoAcaoFormValues = z.infer<typeof planoAcaoFormSchema>;

function FormFeedback({
  feedback,
  testId,
}: {
  feedback: { kind: "success" | "error"; message: string } | null;
  testId: string;
}) {
  if (!feedback) return null;

  return (
    <div
      role="status"
      data-testid={testId}
      className={cn(
        "rounded-sm border px-3 py-2 text-xs",
        feedback.kind === "success" ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-700" : "border-destructive/20 bg-destructive/5 text-destructive",
      )}
    >
      {feedback.message}
    </div>
  );
}

function ProgramaSelector({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const query = useCertificacoesEsgProgramas();
  const programas = query.data ?? [];

  return (
    <Select value={value} onValueChange={onChange} disabled={query.isLoading || programas.length === 0}>
      <SelectTrigger aria-label="Programa *">
        <SelectValue placeholder={query.isLoading ? "Carregando programas..." : "Selecione o programa"} />
      </SelectTrigger>
      <SelectContent>
        {programas.map((programa) => (
          <SelectItem key={programa.id} value={programa.id}>
            {programa.nome} ({programa.tipo_certificacao})
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function ProgramasSection() {
  const query = useCertificacoesEsgProgramas();
  const create = useCriarPrograma();
  const update = useAtualizarPrograma();
  const [form, setForm] = useState({ nome: "", tipo_certificacao: "ESG_INTERNO" as TipoCertificacao, data_inicio: new Date().toISOString().slice(0, 10) });
  const programas = query.data ?? [];
  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await create.mutateAsync({ ...form, status_programa: "ATIVO", data_fim: null, organismo_certificador: null });
    setForm({ nome: "", tipo_certificacao: "ESG_INTERNO", data_inicio: new Date().toISOString().slice(0, 10) });
  };

  return (
    <SectionShell title="Programas de certificação" description="Cadastre e acompanhe os programas usados pelos fluxos ESG.">
      <form className="mb-4 grid gap-3 md:grid-cols-[1fr_180px_150px_auto]" onSubmit={submit}>
        <Input aria-label="Nome do programa" required value={form.nome} placeholder="Nome do programa" onChange={(event) => setForm({ ...form, nome: event.target.value })} />
        <Select value={form.tipo_certificacao} onValueChange={(value) => setForm({ ...form, tipo_certificacao: value as TipoCertificacao })}><SelectTrigger aria-label="Tipo de certificação"><SelectValue /></SelectTrigger><SelectContent>{["ORGANICO", "GLOBALGAP", "REGENAGRI", "ESG_INTERNO", "OUTRO"].map((tipo) => <SelectItem key={tipo} value={tipo}>{tipo}</SelectItem>)}</SelectContent></Select>
        <Input aria-label="Início do programa" required type="date" value={form.data_inicio} onChange={(event) => setForm({ ...form, data_inicio: event.target.value })} />
        <Button type="submit" size="sm" disabled={create.isPending}>{create.isPending ? "Salvando..." : "Novo programa"}</Button>
      </form>
      {query.isLoading ? <Skeleton className="h-12 rounded-sm" /> : programas.length === 0 ? <EmptyState icon={<ShieldCheck />} title="Nenhum programa cadastrado" description="Cadastre o primeiro programa para habilitar os formulários ESG." /> : <div className="space-y-2">{programas.map((programa: ProgramaCertificacao) => <div key={programa.id} className="flex flex-wrap items-center justify-between gap-3 rounded-sm border p-3"><div><p className="text-sm font-medium">{programa.nome}</p><p className="text-xs text-muted-foreground">{programa.tipo_certificacao} · início {new Date(programa.data_inicio).toLocaleDateString("pt-BR")}</p></div><Select value={programa.status_programa} onValueChange={(status) => update.mutate({ id: programa.id, payload: { status_programa: status as ProgramaCertificacao["status_programa"] } })}><SelectTrigger className="h-8 w-36" aria-label={`Status do programa ${programa.nome}`}><SelectValue /></SelectTrigger><SelectContent>{["ATIVO", "SUSPENSO", "INATIVO"].map((status) => <SelectItem key={status} value={status}>{status}</SelectItem>)}</SelectContent></Select></div>)}</div>}
    </SectionShell>
  );
}

function CreateEvidenciaForm() {
  const mutation = useCriarEvidencia();
  const [feedback, setFeedback] = useState<{ kind: "success" | "error"; message: string } | null>(null);

  const form = useForm<EvidenceFormValues>({
    resolver: zodResolver(evidenciaFormSchema),
    defaultValues: {
      programa_id: "",
      tipo_evidencia: "DOCUMENTO_PDF",
      titulo: "",
      descricao: "",
      origem_tipo: "AUDITORIA_INTERNA",
      origem_id: "",
      publico: false,
    },
  });

  const submit = form.handleSubmit(async (values) => {
    setFeedback(null);
    try {
      await mutation.mutateAsync(values);
      setFeedback({ kind: "success", message: "Evidência criada com sucesso." });
      form.reset({
        programa_id: "",
        tipo_evidencia: "DOCUMENTO_PDF",
        titulo: "",
        descricao: "",
        origem_tipo: "AUDITORIA_INTERNA",
        origem_id: "",
        publico: false,
      });
    } catch (error) {
      setFeedback({
        kind: "error",
        message: error instanceof Error ? error.message : "Falha ao criar a evidência.",
      });
    }
  });

  return (
    <Card className="overflow-hidden border-dashed" data-testid="certificacoes-esg-form-evidencia">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-base">
          <FilePlus2 className="size-4 text-primary" />
          Nova evidência
        </CardTitle>
        <p className="text-sm text-muted-foreground">Registro imutável vinculado ao domínio de certificação.</p>
      </CardHeader>
      <CardContent className="space-y-4 p-4">
        <Form {...form}>
          <form className="space-y-4" onSubmit={submit}>
            <div className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="programa_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Programa *</FormLabel>
                    <FormControl><ProgramaSelector value={field.value} onChange={field.onChange} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="tipo_evidencia"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Tipo *</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {evidenciaTipos.map((option) => (
                          <SelectItem key={option} value={option}>
                            {option}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="titulo"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Título *</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="Relatório de campo" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="descricao"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Descrição *</FormLabel>
                  <FormControl>
                    <Textarea {...field} placeholder="Descreva a evidência" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="origem_tipo"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Origem *</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder="AUDITORIA_INTERNA" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="origem_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>ID de origem *</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder="UUID da origem" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="publico"
              render={({ field }) => (
                <FormItem className="flex flex-row items-start gap-3 space-y-0 rounded-sm border p-3">
                  <FormControl>
                    <Checkbox
                      data-testid="evidencia-publica-checkbox"
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                  <div className="space-y-1 leading-none">
                    <FormLabel className="text-sm">Evidência pública</FormLabel>
                    <p className="text-xs text-muted-foreground">Visível na área consultiva do domínio.</p>
                  </div>
                </FormItem>
              )}
            />

            <FormFeedback feedback={feedback} testId="certificacoes-esg-feedback-evidencia" />

            <div className="flex items-center justify-end">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}
                {mutation.isPending ? "Criando..." : "Criar evidência"}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

function CreateNaoConformidadeForm() {
  const mutation = useCriarNaoConformidade();
  const [feedback, setFeedback] = useState<{ kind: "success" | "error"; message: string } | null>(null);

  const form = useForm<NaoConformidadeFormValues>({
    resolver: zodResolver(naoConformidadeFormSchema),
    defaultValues: {
      programa_id: "",
      titulo: "",
      descricao: "",
      severidade: "MAIOR",
      status: "ABERTA",
      detectada_em: datetimeLocalNow(),
      prazo_correcao: "",
    },
  });

  const submit = form.handleSubmit(async (values) => {
    setFeedback(null);
    try {
      await mutation.mutateAsync({
        ...values,
        prazo_correcao: values.prazo_correcao || undefined,
      });
      setFeedback({ kind: "success", message: "Não conformidade criada com sucesso." });
      form.reset({
        programa_id: "",
        titulo: "",
        descricao: "",
        severidade: "MAIOR",
        status: "ABERTA",
        detectada_em: datetimeLocalNow(),
        prazo_correcao: "",
      });
    } catch (error) {
      setFeedback({
        kind: "error",
        message: error instanceof Error ? error.message : "Falha ao criar a não conformidade.",
      });
    }
  });

  return (
    <Card className="overflow-hidden border-dashed" data-testid="certificacoes-esg-form-nao-conformidade">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-base">
          <ClipboardList className="size-4 text-primary" />
          Nova não conformidade
        </CardTitle>
        <p className="text-sm text-muted-foreground">Registro de desvio, severidade e tratamento inicial.</p>
      </CardHeader>
      <CardContent className="space-y-4 p-4">
        <Form {...form}>
          <form className="space-y-4" onSubmit={submit}>
            <FormField
              control={form.control}
              name="programa_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Programa *</FormLabel>
                  <FormControl><ProgramaSelector value={field.value} onChange={field.onChange} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="titulo"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Título *</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="NC de irrigação" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="descricao"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Descrição *</FormLabel>
                  <FormControl>
                    <Textarea {...field} placeholder="Descreva a não conformidade" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="severidade"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Severidade *</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {naoConformidadeSeveridades.map((option) => (
                          <SelectItem key={option} value={option}>
                            {option}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="status"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Status *</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {naoConformidadeStatus.map((option) => (
                          <SelectItem key={option} value={option}>
                            {option}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="detectada_em"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Detectada em *</FormLabel>
                    <FormControl>
                      <Input {...field} type="datetime-local" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="prazo_correcao"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Prazo de correção</FormLabel>
                    <FormControl>
                      <Input {...field} type="datetime-local" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormFeedback feedback={feedback} testId="certificacoes-esg-feedback-nao-conformidade" />

            <div className="flex items-center justify-end">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}
                {mutation.isPending ? "Criando..." : "Criar não conformidade"}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

function CreatePlanoAcaoForm() {
  const mutation = useCriarPlanoAcao();
  const [feedback, setFeedback] = useState<{ kind: "success" | "error"; message: string } | null>(null);

  const form = useForm<PlanoAcaoFormValues>({
    resolver: zodResolver(planoAcaoFormSchema),
    defaultValues: {
      programa_id: "",
      titulo: "",
      descricao: "",
      prioridade: "MEDIA",
      status: "PENDENTE",
      prazo: datetimeLocalNow(7),
    },
  });

  const submit = form.handleSubmit(async (values) => {
    setFeedback(null);
    try {
      await mutation.mutateAsync(values);
      setFeedback({ kind: "success", message: "Plano de ação criado com sucesso." });
      form.reset({
        programa_id: "",
        titulo: "",
        descricao: "",
        prioridade: "MEDIA",
        status: "PENDENTE",
        prazo: datetimeLocalNow(7),
      });
    } catch (error) {
      setFeedback({
        kind: "error",
        message: error instanceof Error ? error.message : "Falha ao criar o plano de ação.",
      });
    }
  });

  return (
    <Card className="overflow-hidden border-dashed" data-testid="certificacoes-esg-form-plano-acao">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-base">
          <ShieldCheck className="size-4 text-primary" />
          Novo plano de ação
        </CardTitle>
        <p className="text-sm text-muted-foreground">Plano nativo do domínio de certificação, sem legado financeiro.</p>
      </CardHeader>
      <CardContent className="space-y-4 p-4">
        <Form {...form}>
          <form className="space-y-4" onSubmit={submit}>
            <FormField
              control={form.control}
              name="programa_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Programa *</FormLabel>
                  <FormControl><ProgramaSelector value={field.value} onChange={field.onChange} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="titulo"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Título *</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="Plano corretivo" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="descricao"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Descrição *</FormLabel>
                  <FormControl>
                    <Textarea {...field} placeholder="Descreva o plano de ação" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="prioridade"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Prioridade *</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {planoPrioridades.map((option) => (
                          <SelectItem key={option} value={option}>
                            {option}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="status"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Status *</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {planoStatus.map((option) => (
                          <SelectItem key={option} value={option}>
                            {option}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="prazo"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Prazo *</FormLabel>
                  <FormControl>
                    <Input {...field} type="datetime-local" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormFeedback feedback={feedback} testId="certificacoes-esg-feedback-plano-acao" />

            <div className="flex items-center justify-end">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}
                {mutation.isPending ? "Criando..." : "Criar plano"}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

function ListSkeleton() {
  return (
    <div className="space-y-3" data-testid="certificacoes-esg-loading">
      {Array.from({ length: 2 }).map((_, index) => (
        <div key={index} className="rounded-sm border p-4 space-y-2">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-3 w-64" />
          <Skeleton className="h-8 w-32" />
        </div>
      ))}
    </div>
  );
}

function EvidenceRow({ item }: { item: EvidenciaCertificacao }) {
  return (
    <div className="rounded-sm border bg-background/70 p-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold text-sm">{item.titulo}</p>
            {item.publico ? <Badge className="rounded-sm" variant="outline">Público</Badge> : <Badge className="rounded-sm" variant="outline">Privado</Badge>}
          </div>
          <p className="text-xs text-muted-foreground">{item.descricao}</p>
        </div>
        <WorkflowStatusBadge status={item.publico ? "PUBLICO" : "PRIVADO"} />
      </div>
      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
        <Badge variant="secondary" className="rounded-sm">{item.tipo_evidencia}</Badge>
        <Badge variant="outline" className="rounded-sm">{item.origem_tipo}</Badge>
        <Badge variant="outline" className="rounded-sm">{item.programa_id.slice(0, 8)}</Badge>
      </div>
    </div>
  );
}

function NaoConformidadeRow({
  item,
  onAdvance,
  pending,
}: {
  item: NaoConformidadeCertificacao;
  onAdvance: (status: "EM_ANALISE" | "RESOLVIDA") => void;
  pending: boolean;
}) {
  const isClosed = item.status === "RESOLVIDA" || item.status === "CANCELADA";
  const primaryAction = item.status === "ABERTA" ? "EM_ANALISE" : "RESOLVIDA";

  return (
    <div className="rounded-sm border bg-background/70 p-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="font-semibold text-sm">{item.titulo}</p>
          <p className="text-xs text-muted-foreground">{item.descricao}</p>
        </div>
        <span className={cn("inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-medium", domainStatusClass(item.status))}>
          {NaoConformidadeLabels[item.status] ?? item.status}
        </span>
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        <Badge variant="secondary" className="rounded-sm">{item.severidade}</Badge>
        <Badge variant="outline" className="rounded-sm">Detectada em {new Date(item.detectada_em).toLocaleDateString("pt-BR")}</Badge>
      </div>
      {!isClosed && (
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={pending}
            onClick={() => onAdvance(primaryAction)}
            aria-label={`Atualizar status da não conformidade ${item.titulo}`}
          >
            {item.status === "ABERTA" ? "Ir para análise" : "Resolver"}
          </Button>
          {item.status !== "CANCELADA" && (
            <Button
              size="sm"
              variant="ghost"
              disabled={pending}
              onClick={() => onAdvance("RESOLVIDA")}
            >
              Concluir
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

function PlanoAcaoRow({
  item,
  onAdvance,
  pending,
}: {
  item: PlanoAcaoCertificacao;
  onAdvance: (status: "EM_ANDAMENTO" | "CONCLUIDO") => void;
  pending: boolean;
}) {
  const isClosed = item.status === "CONCLUIDO" || item.status === "CANCELADO";
  const primaryAction = item.status === "PENDENTE" ? "EM_ANDAMENTO" : "CONCLUIDO";

  return (
    <div className="rounded-sm border bg-background/70 p-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="font-semibold text-sm">{item.titulo}</p>
          <p className="text-xs text-muted-foreground">{item.descricao}</p>
        </div>
        <span className={cn("inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-medium", domainStatusClass(item.status))}>
          {PlanoAcaoLabels[item.status] ?? item.status}
        </span>
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        <Badge variant="secondary" className="rounded-sm">{item.prioridade}</Badge>
        <Badge variant="outline" className={cn("rounded-sm", pendenteOuAtrasado(item) && "border-orange-400 text-orange-700")}>
          Prazo {new Date(item.prazo).toLocaleDateString("pt-BR")}
        </Badge>
      </div>
      {!isClosed && (
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={pending}
            onClick={() => onAdvance(primaryAction)}
            aria-label={`Atualizar status do plano de ação ${item.titulo}`}
          >
            {item.status === "PENDENTE" ? "Iniciar" : "Concluir"}
          </Button>
          {item.status !== "CANCELADO" && (
            <Button
              size="sm"
              variant="ghost"
              disabled={pending}
              onClick={() => onAdvance("CONCLUIDO")}
            >
              Finalizar
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

export function CertificacoesEsgClient() {
  const evidenciasQuery = useCertificacoesEsgEvidencias();
  const naoConformidadesQuery = useCertificacoesEsgNaoConformidades();
  const planosQuery = useCertificacoesEsgPlanosAcao();
  const atualizarNaoConformidade = useAtualizarNaoConformidadeStatus();
  const atualizarPlanoAcao = useAtualizarPlanoAcaoStatus();
  const evidencias = useMemo(() => evidenciasQuery.data ?? [], [evidenciasQuery.data]);
  const naoConformidades = useMemo(() => naoConformidadesQuery.data ?? [], [naoConformidadesQuery.data]);
  const planos = useMemo(() => planosQuery.data ?? [], [planosQuery.data]);

  const resumo = useMemo(() => {
    return {
      totalEvidencias: evidencias.length,
      naoConformidadesAbertas: naoConformidades.filter((item) => item.status === "ABERTA" || item.status === "EM_ANALISE" || item.status === "EM_CORRECAO").length,
      planosPendentesOuAtrasados: planos.filter(pendenteOuAtrasado).length,
      evidenciasPublicas: evidencias.filter((item) => item.publico).length,
    };
  }, [evidencias, naoConformidades, planos]);

  const loading = evidenciasQuery.isLoading || naoConformidadesQuery.isLoading || planosQuery.isLoading;

  const errorMessage =
    (evidenciasQuery.error instanceof Error && evidenciasQuery.error.message) ||
    (naoConformidadesQuery.error instanceof Error && naoConformidadesQuery.error.message) ||
    (planosQuery.error instanceof Error && planosQuery.error.message) ||
    null;

  const handleNaoConformidadeStatus = async (item: NaoConformidadeCertificacao, status: "EM_ANALISE" | "RESOLVIDA") => {
    await atualizarNaoConformidade.mutateAsync({
      id: item.id,
      payload: {
        status,
        resolvida_em: status === "RESOLVIDA" ? isoNow() : item.resolvida_em,
      },
    });
  };

  const handlePlanoStatus = async (item: PlanoAcaoCertificacao, status: "EM_ANDAMENTO" | "CONCLUIDO") => {
    await atualizarPlanoAcao.mutateAsync({
      id: item.id,
      payload: {
        status,
        concluido_em: status === "CONCLUIDO" ? isoNow() : item.concluido_em,
      },
    });
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Total de evidências"
          value={resumo.totalEvidencias}
          subtitle="Itens rastreáveis do domínio"
          icon={ShieldCheck}
          color="agro"
        />
        <StatCard
          label="NC abertas"
          value={resumo.naoConformidadesAbertas}
          subtitle="Pendentes de tratamento"
          icon={TriangleAlert}
          color="warning"
        />
        <StatCard
          label="Planos pendentes"
          value={resumo.planosPendentesOuAtrasados}
          subtitle="Em andamento ou vencidos"
          icon={AlertCircle}
          color="destructive"
        />
        <StatCard
          label="Evidências públicas"
          value={resumo.evidenciasPublicas}
          subtitle="Disponíveis para consulta"
          icon={Sparkles}
          color="backoffice"
        />
      </div>

      <ProgramasSection />

      <div className="grid gap-4 xl:grid-cols-3">
        <CreateEvidenciaForm />
        <CreateNaoConformidadeForm />
        <CreatePlanoAcaoForm />
      </div>

      {loading && <ListSkeleton />}

      {!loading && errorMessage && (
        <Card className="border-destructive/30 bg-destructive/5">
          <CardContent className="flex items-center gap-3 p-4">
            <ShieldAlert className="size-4 text-destructive" />
            <p className="text-sm text-destructive">Falha ao carregar pelo menos uma seção: {errorMessage}</p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 xl:grid-cols-3">
        <SectionShell
          title="Evidências"
          description="Registros e documentos imutáveis vinculados ao domínio de certificação."
        >
          {evidenciasQuery.isError ? (
            <EmptyState
              icon={<AlertCircle />}
              title="Falha ao carregar evidências"
              description={evidenciasQuery.error instanceof Error ? evidenciasQuery.error.message : "Tente novamente mais tarde."}
            />
          ) : evidencias.length === 0 ? (
            <EmptyState
              icon={<FileCheck2 />}
              title="Nenhuma evidência registrada"
              description="Quando existirem registros, documentos ou fotos, eles aparecerão aqui."
            />
          ) : (
            <div className="space-y-3">
              {evidencias.map((item) => (
                <EvidenceRow key={item.id} item={item} />
              ))}
            </div>
          )}
        </SectionShell>

        <SectionShell
          title="Não conformidades"
          description="Registro de desvios, severidade e ações corretivas do domínio."
        >
          {naoConformidadesQuery.isError ? (
            <EmptyState
              icon={<AlertCircle />}
              title="Falha ao carregar não conformidades"
              description={naoConformidadesQuery.error instanceof Error ? naoConformidadesQuery.error.message : "Tente novamente mais tarde."}
            />
          ) : naoConformidades.length === 0 ? (
            <EmptyState
              icon={<TriangleAlert />}
              title="Nenhuma não conformidade aberta"
              description="A triagem do domínio está limpa no momento."
            />
          ) : (
            <div className="space-y-3">
              {naoConformidades.map((item) => (
                <NaoConformidadeRow
                  key={item.id}
                  item={item}
                  pending={atualizarNaoConformidade.isPending}
                  onAdvance={(status) => handleNaoConformidadeStatus(item, status)}
                />
              ))}
            </div>
          )}
        </SectionShell>

        <SectionShell
          title="Planos de ação"
          description="Planos próprios do domínio consumidor, sem uso de legado financeiro."
        >
          {planosQuery.isError ? (
            <EmptyState
              icon={<AlertCircle />}
              title="Falha ao carregar planos de ação"
              description={planosQuery.error instanceof Error ? planosQuery.error.message : "Tente novamente mais tarde."}
            />
          ) : planos.length === 0 ? (
            <EmptyState
              icon={<ShieldCheck />}
              title="Nenhum plano de ação disponível"
              description="Os planos aparecerão quando houver não conformidades ou ações preventivas."
            />
          ) : (
            <div className="space-y-3">
              {planos.map((item) => (
                <PlanoAcaoRow
                  key={item.id}
                  item={item}
                  pending={atualizarPlanoAcao.isPending}
                  onAdvance={(status) => handlePlanoStatus(item, status)}
                />
              ))}
            </div>
          )}
        </SectionShell>
      </div>

      <Card className="border-dashed">
        <CardContent className="p-4 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <FileCheck2 className="size-4 text-primary" />
          <span>Esta tela é somente leitura para a base territorial/fundiária e só altera status no domínio de certificação.</span>
        </CardContent>
      </Card>
    </div>
  );
}
