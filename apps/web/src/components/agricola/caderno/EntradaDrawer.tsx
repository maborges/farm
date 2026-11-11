"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetFooter } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Camera, MapPin, Trash2, CheckCircle2, XCircle, ShieldCheck } from "lucide-react";
import Image from "next/image";
import { cn } from "@/lib/utils";
import { FotoUpload } from "./FotoUpload";

interface Foto {
  id: string;
  url: string;
  latitude?: number;
  longitude?: number;
}

interface TimelineItem {
  id: string;
  tipo: string;
  tipo_evento?: string;
  subtipo?: string;
  descricao: string;
  data_registro: string;
  talhao_id: string;
  usuario_id?: string;
  executado_por_pessoa_id?: string;
  status_evento?: string;
  status_evento_atualizado_em?: string;
  pendente_aprovacao?: boolean;
  aprovado?: boolean;
  consolidado?: boolean;
  rejeitado?: boolean;
  nivel_severidade?: string;
  fotos_count: number;
  excluida: boolean;
  origem: string;
  origem_invalidada?: boolean;
  origem_invalidada_em?: string | null;
  origem_invalidada_por?: string | null;
  motivo_invalidacao_origem?: string | null;
  documental_status?: string | null;
  retifica_evento_id?: string | null;
  retificado_por_evento_id?: string | null;
  motivo_retificacao?: string | null;
  retificado_em?: string | null;
  retificado_por_usuario_id?: string | null;
  versao_vigente?: boolean;
  retificado?: boolean;
  retificador?: boolean;
}

interface Props {
  item: TimelineItem | null;
  onClose: () => void;
  onDelete?: (id: string) => void;
  canManageStatus?: boolean;
  onUpdateStatus?: (id: string, status: string, justificativa?: string) => Promise<void> | void;
  onRetificar?: (id: string, motivo: string, dadosCorrigidos?: Record<string, unknown>) => Promise<void> | void;
  allowUpload?: boolean;
}

const TIPO_LABEL: Record<string, string> = {
  OPERACAO_AUTO: "Operação",
  MONITORAMENTO: "Monitoramento",
  VISITA_TECNICA: "Visita Técnica",
  EPI_ENTREGA: "Entrega EPI",
  OBSERVACAO: "Observação",
  CLIMA: "Clima",
  SOLO: "Solo",
};

const SEVERIDADE_COLOR: Record<string, string> = {
  BAIXO: "bg-green-100 text-green-800",
  MEDIO: "bg-yellow-100 text-yellow-800",
  ALTO: "bg-orange-100 text-orange-800",
  CRITICO: "bg-red-100 text-red-800",
};

export function EntradaDrawer({ item, onClose, onDelete, canManageStatus = false, onUpdateStatus, onRetificar, allowUpload = true }: Props) {
  // Busca fotos detalhados da entrada
  const { data: fotos = [] } = useQuery<Foto[]>({
    queryKey: ["caderno-fotos", item?.id],
    queryFn: async () => {
      if (!item) return [];
      const entrada = await apiFetch<{ fotos: Foto[] }>(`/caderno/entradas/${item.id}`);
      return entrada?.fotos || [];
    },
    enabled: !!item,
  });

  const { data: pessoas = [] } = useQuery<{ id: string; nome_exibicao: string }[]>({
    queryKey: ["pessoas", "ativo"],
    queryFn: () => apiFetch("/cadastros/pessoas?ativo=true"),
    enabled: !!item && !!item.executado_por_pessoa_id,
  });

  const executor = pessoas.find((p) => p.id === item?.executado_por_pessoa_id);

  if (!item) return null;

  const isAuto = item.origem === "operacao";
  const tipoEvento = item.tipo_evento ?? item.tipo;
  const labelTipo = isAuto ? `${TIPO_LABEL.OPERACAO_AUTO} — ${item.subtipo ?? ""}` : (TIPO_LABEL[tipoEvento] ?? tipoEvento);
  const hasFotos = fotos.length > 0;
  const podeAprovar = canManageStatus && !!onUpdateStatus && !item.excluida && !isAuto;
  const statusAtual = item.status_evento ?? "CONSOLIDADO";
  const exibeAcoesGovernanca = podeAprovar && ["RASCUNHO", "PENDENTE_SINCRONIZACAO", "SINCRONIZADO", "PENDENTE_APROVACAO", "APROVADO"].includes(statusAtual);
  const podeRetificar = canManageStatus && !!onRetificar && !item.excluida && !item.retificado_por_evento_id;

  const handleRejeitar = async () => {
    const justificativa = window.prompt("Informe a justificativa da rejeição:");
    if (!justificativa?.trim()) return;
    await onUpdateStatus?.(item.id, "REJEITADO", justificativa.trim());
  };

  const handleRetificar = async () => {
    const motivo = window.prompt("Informe o motivo da retificação:");
    if (!motivo?.trim()) return;
    const novaDescricao = window.prompt("Informe a descrição corrigida (opcional):", item.descricao) ?? "";
    const dadosCorrigidos: Record<string, unknown> = {};
    if (novaDescricao.trim() && novaDescricao.trim() !== item.descricao) {
      dadosCorrigidos.descricao = novaDescricao.trim();
    }
    await onRetificar?.(item.id, motivo.trim(), dadosCorrigidos);
  };

  return (
    <Sheet open={!!item} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full sm:max-w-md flex flex-col">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2 text-base">
            {labelTipo}
            {item.status_evento && (
              <WorkflowStatusBadge status={item.status_evento} className="h-5 px-2 text-[10px]" />
            )}
            {item.versao_vigente && (
              <Badge variant="secondary" className="text-[10px] rounded-sm font-bold uppercase">Versão vigente</Badge>
            )}
            {item.retificado && (
              <Badge variant="outline" className="text-[10px] rounded-sm font-bold uppercase">Retificado</Badge>
            )}
            {item.retificador && (
              <Badge variant="outline" className="text-[10px] rounded-sm font-bold uppercase">Retificador</Badge>
            )}
            {item.origem_invalidada && (
              <Badge variant="destructive" className="text-[10px] rounded-sm font-bold uppercase">Origem invalidada</Badge>
            )}
            {item.nivel_severidade && (
              <span className={cn("text-[10px] px-2 py-0.5 rounded-sm font-bold uppercase", SEVERIDADE_COLOR[item.nivel_severidade] ?? "")}>
                {item.nivel_severidade}
              </span>
            )}
            {isAuto && (
              <Badge variant="secondary" className="text-[10px] rounded-sm font-bold uppercase">Automático</Badge>
            )}
          </SheetTitle>
          <p className="text-xs text-muted-foreground">
            {format(new Date(item.data_registro + "T12:00:00"), "dd 'de' MMMM 'de' yyyy", { locale: ptBR })}
          </p>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          <div className="rounded-sm bg-muted/40 p-4 border border-border/40">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{item.descricao}</p>
            
            <div className="mt-4 pt-3 border-t border-border/50 grid grid-cols-2 gap-4 text-[11px]">
              <div>
                <p className="text-muted-foreground font-medium mb-1">Registrado por</p>
                <p className="text-foreground">{item.usuario_id?.split("-")[0] ?? "Sistêmico"}</p>
              </div>
              <div>
                <p className="text-muted-foreground font-medium mb-1">Executado por</p>
                <p className="text-foreground">{executor ? executor.nome_exibicao : (item.executado_por_pessoa_id ? "..." : "Não informado")}</p>
              </div>
            </div>

            {(item.retifica_evento_id || item.retificado_por_evento_id || item.motivo_retificacao) && (
              <div className="mt-3 space-y-1 text-xs text-muted-foreground border-t border-border/50 pt-3">
                {item.retifica_evento_id && (
                  <p><strong>Retifica:</strong> {item.retifica_evento_id}</p>
                )}
                {item.retificado_por_evento_id && (
                  <p><strong>Retificado por:</strong> {item.retificado_por_evento_id}</p>
                )}
                {item.motivo_retificacao && (
                  <p><strong>Motivo:</strong> {item.motivo_retificacao}</p>
                )}
              </div>
            )}
            {item.origem_invalidada && (
              <div className="mt-3 space-y-1 text-xs text-destructive border-t border-destructive/20 pt-3">
                <p><strong>Status documental:</strong> {item.documental_status ?? "ORIGEM_INVALIDADA"}</p>
                {item.origem_invalidada_em && (
                  <p><strong>Invalidada em:</strong> {format(new Date(item.origem_invalidada_em), "dd/MM/yyyy HH:mm", { locale: ptBR })}</p>
                )}
                {item.origem_invalidada_por && (
                  <p><strong>Usuário:</strong> {item.origem_invalidada_por}</p>
                )}
                {item.motivo_invalidacao_origem && (
                  <p><strong>Motivo:</strong> {item.motivo_invalidacao_origem}</p>
                )}
              </div>
            )}
          </div>

          {/* Galeria de fotos */}
          {hasFotos && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium flex items-center gap-1.5">
                <Camera className="size-3.5" />
                Fotos ({fotos.length})
              </h4>
              <div className="grid grid-cols-3 gap-2">
                {fotos.map((f) => (
                  <div key={f.id} className="relative aspect-square rounded-sm overflow-hidden bg-muted group border border-border/20">
                    <Image src={f.url} alt="Foto" fill className="object-cover" sizes="150px" />
                    {f.latitude && f.longitude && (
                      <MapPin className="absolute bottom-1 right-1 size-3 text-white drop-shadow" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upload de foto (apenas entradas manuais não excluídas) */}
          {allowUpload && !isAuto && !item.excluida && (
            <div className="space-y-2">
              <FotoUpload entradaId={item.id} fotosExistentes={fotos} />
            </div>
          )}

          {item.excluida && (
            <div className="rounded-sm bg-destructive/10 border border-destructive/20 p-3">
              <p className="text-[10px] text-destructive font-bold uppercase">Entrada excluída (auditoria mantida)</p>
            </div>
          )}

          {exibeAcoesGovernanca && (
            <div className="rounded-sm border border-border/60 bg-muted/30 p-3 space-y-2">
              <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                <ShieldCheck className="size-3.5" />
                Governança de status
              </div>
              <div className="flex flex-wrap gap-2">
                {statusAtual !== "APROVADO" && statusAtual !== "CONSOLIDADO" && (
                  <Button
                    size="sm"
                    className="rounded-sm"
                    onClick={() => onUpdateStatus?.(item.id, "APROVADO", "Aprovado após conferência técnica")}
                  >
                    <CheckCircle2 className="size-3.5 mr-1.5" />
                    Aprovar
                  </Button>
                )}
                {statusAtual === "APROVADO" && (
                  <Button
                    size="sm"
                    variant="secondary"
                    className="rounded-sm"
                    onClick={() => onUpdateStatus?.(item.id, "CONSOLIDADO", "Evento consolidado após aprovação")}
                  >
                    <ShieldCheck className="size-3.5 mr-1.5" />
                    Consolidar
                  </Button>
                )}
                {statusAtual !== "REJEITADO" && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="rounded-sm text-destructive hover:text-destructive"
                    onClick={handleRejeitar}
                  >
                    <XCircle className="size-3.5 mr-1.5" />
                    Rejeitar
                  </Button>
                )}
              </div>
            </div>
          )}

          {podeRetificar && (
            <div className="rounded-sm border border-amber-500/30 bg-amber-500/10 dark:bg-amber-950/20 p-3 space-y-2">
              <div className="flex items-center gap-2 text-[11px] text-amber-800 dark:text-amber-300">
                <ShieldCheck className="size-3.5" />
                Retificação documental
              </div>
              <Button
                size="sm"
                variant="outline"
                className="rounded-sm border-amber-500/30 text-amber-900 dark:text-amber-300 hover:bg-amber-500/15"
                onClick={handleRetificar}
              >
                Retificar
              </Button>
            </div>
          )}
        </div>

        <SheetFooter className="flex-col gap-2 sm:flex-row">
          {!isAuto && !item.excluida && onDelete && (
            <Button
              variant="outline"
              size="sm"
              className="text-destructive hover:text-destructive"
              onClick={() => onDelete(item.id)}
            >
              <Trash2 className="size-3.5 mr-1.5" />
              Excluir
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={onClose} className="flex-1 rounded-sm">
            Fechar
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
