"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import {
    Mail, Phone, Building2, FileText, CheckCircle2, ShoppingCart, XCircle, RotateCcw, Plus
} from "lucide-react";
import {
    Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";

import { Lead, PlanoComercial, ORIGENS, STATUS_CONFIG, ATIVIDADE_TIPOS } from "./types";

interface CrmLeadDetailSheetProps {
  selectedLead: Lead | null;
  onClose: () => void;
  onShowOferta: () => void;
  onConvert: (leadId: string) => void;
  onLose: (lead: Lead) => void;
  onReopen: (leadId: string) => void;
  planos: PlanoComercial[] | undefined;
  formatCurrency: (val: number) => string;
}

export function CrmLeadDetailSheet({
  selectedLead,
  onClose,
  onShowOferta,
  onConvert,
  onLose,
  onReopen,
  planos,
  formatCurrency,
}: CrmLeadDetailSheetProps) {
  const queryClient = useQueryClient();
  const [showNewAtividade, setShowNewAtividade] = useState(false);
  const [newAtividade, setNewAtividade] = useState({ tipo: "nota", descricao: "" });

  const { data: leadDetail } = useQuery<Lead>({
      queryKey: ["crm", "lead", selectedLead?.id],
      queryFn: () => apiFetch(`/backoffice/crm/leads/${selectedLead!.id}`),
      enabled: !!selectedLead,
  });

  const createAtividadeMutation = useMutation({
      mutationFn: ({ leadId, data }: { leadId: string; data: Record<string, unknown> }) =>
          apiFetch(`/backoffice/crm/leads/${leadId}/atividades`, {
              method: "POST",
              body: JSON.stringify(data),
          }),
      onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: ["crm", "lead", selectedLead?.id] });
          setShowNewAtividade(false);
          setNewAtividade({ tipo: "nota", descricao: "" });
          toast.success("Atividade registrada!");
      },
      onError: (err: any) => toast.error(err.message || "Erro ao registrar atividade"),
  });

  const toggleAtividadeMutation = useMutation({
      mutationFn: (atividadeId: string) =>
          apiFetch(`/backoffice/crm/atividades/${atividadeId}/toggle`, { method: "PATCH" }),
      onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: ["crm", "lead", selectedLead?.id] });
      },
  });

  function handleCreateAtividade() {
      if (!newAtividade.descricao || !selectedLead) {
          toast.error("Descrição é obrigatória");
          return;
      }
      createAtividadeMutation.mutate({
          leadId: selectedLead.id,
          data: { tipo: newAtividade.tipo, descricao: newAtividade.descricao },
      });
  }

  return (
    <Sheet open={!!selectedLead} onOpenChange={onClose}>
        <SheetContent className="w-[calc(100vw-1rem)] sm:max-w-[480px] overflow-hidden p-0 flex flex-col">
            <SheetHeader className="border-b px-4 py-4">
                <SheetTitle className="flex items-center gap-2">
                    {selectedLead?.nome}
                    {selectedLead && (
                        <Badge className={`text-[9px] border ${STATUS_CONFIG[selectedLead.status]?.color}`}>
                            {STATUS_CONFIG[selectedLead.status]?.label}
                        </Badge>
                    )}
                </SheetTitle>
                <SheetDescription>
                    {selectedLead?.empresa && `${selectedLead.empresa} · `}
                    Criado {selectedLead && formatDistanceToNow(new Date(selectedLead.created_at), { addSuffix: true, locale: ptBR })}
                </SheetDescription>
            </SheetHeader>

            {selectedLead && (
                <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
                    {/* Contact Info */}
                    <div className="space-y-2">
                        <h4 className="text-xs font-bold uppercase text-muted-foreground tracking-widest">Contato</h4>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                            {selectedLead.email && (
                                <div className="flex items-center gap-2">
                                    <Mail className="size-3 text-muted-foreground" />
                                    <span className="truncate">{selectedLead.email}</span>
                                </div>
                            )}
                            {selectedLead.telefone && (
                                <div className="flex items-center gap-2">
                                    <Phone className="size-3 text-muted-foreground" />
                                    <span>{selectedLead.telefone}</span>
                                </div>
                            )}
                            {selectedLead.empresa && (
                                <div className="flex items-center gap-2">
                                    <Building2 className="size-3 text-muted-foreground" />
                                    <span>{selectedLead.empresa}</span>
                                </div>
                            )}
                            {selectedLead.documento && (
                                <div className="flex items-center gap-2">
                                    <FileText className="size-3 text-muted-foreground" />
                                    <span>{selectedLead.documento}</span>
                                </div>
                            )}
                        </div>
                    </div>

                    <Separator />

                    {/* Pipeline Info */}
                    <div className="space-y-2">
                        <h4 className="text-xs font-bold uppercase text-muted-foreground tracking-widest">Pipeline</h4>
                        <div className="text-sm">
                            <span className="text-muted-foreground text-xs">Estágio Atual:</span>
                            <p className="font-semibold">
                                {selectedLead?.estagio ? (
                                    <span style={{ display: 'inline-block', marginRight: '6px', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: selectedLead.estagio.cor }} />
                                ) : null}
                                {selectedLead?.estagio?.nome ?? "Desconhecido"}
                            </p>
                        </div>
                    </div>

                    <Separator />

                    {/* Commercial Info */}
                    <div className="space-y-2">
                        <h4 className="text-xs font-bold uppercase text-muted-foreground tracking-widest">Comercial</h4>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                            <div>
                                <span className="text-muted-foreground text-xs">Origem:</span>
                                <p>{ORIGENS[selectedLead.origem]?.label ?? selectedLead.origem}</p>
                            </div>
                            <div>
                                <span className="text-muted-foreground text-xs">Valor:</span>
                                <p className="font-semibold">{selectedLead.valor_estimado ? formatCurrency(selectedLead.valor_estimado) : "—"}</p>
                            </div>
                            {selectedLead.plano_interesse && (
                                <div>
                                    <span className="text-muted-foreground text-xs">Plano:</span>
                                    <p>
                                        {planos?.find(p => p.id === selectedLead.plano_interesse || p.nome === selectedLead.plano_interesse)?.nome ?? selectedLead.plano_interesse}
                                    </p>
                                </div>
                            )}
                            {selectedLead.qtd_fazendas != null && (
                                <div>
                                    <span className="text-muted-foreground text-xs">Fazendas:</span>
                                    <p>{selectedLead.qtd_fazendas}</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {selectedLead.notas && (
                        <>
                            <Separator />
                            <div>
                                <h4 className="text-xs font-bold uppercase text-muted-foreground tracking-widest mb-1">Notas</h4>
                                <p className="text-sm whitespace-pre-wrap">{selectedLead.notas}</p>
                            </div>
                        </>
                    )}

                    {selectedLead.motivo_perda && (
                        <>
                            <Separator />
                            <div className="bg-red-50 border border-red-200 rounded p-3">
                                <h4 className="text-xs font-bold text-red-600 uppercase mb-1">Motivo da Perda</h4>
                                <p className="text-sm text-red-700">{selectedLead.motivo_perda}</p>
                            </div>
                        </>
                    )}

                    <Separator />

                    {/* Actions */}
                    <div className="flex gap-2 flex-wrap">
                        {(selectedLead.status === "ativo" || selectedLead.status === "aprovado") && (
                            <>
                                <Button size="sm" variant="outline" className="text-blue-600" onClick={onShowOferta}>
                                    <ShoppingCart className="size-3 mr-1" /> Oferta
                                </Button>
                                <Button size="sm" variant="outline" className="text-green-600" onClick={() => onConvert(selectedLead.id)}>
                                    <CheckCircle2 className="size-3 mr-1" /> Converter
                                </Button>
                                <Button size="sm" variant="outline" className="text-red-600" onClick={() => onLose(selectedLead)}>
                                    <XCircle className="size-3 mr-1" /> Perdido
                                </Button>
                            </>
                        )}
                        {(selectedLead.status === "perdido" || selectedLead.status === "convertido") && (
                            <Button size="sm" variant="outline" onClick={() => onReopen(selectedLead.id)}>
                                <RotateCcw className="size-3 mr-1" /> Reabrir
                            </Button>
                        )}
                    </div>

                    <Separator />

                    {/* Atividades */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <h4 className="text-xs font-bold uppercase text-muted-foreground tracking-widest">Atividades</h4>
                            <Button size="sm" variant="outline" onClick={() => setShowNewAtividade(true)}>
                                <Plus className="size-3 mr-1" /> Adicionar
                            </Button>
                        </div>

                        {leadDetail?.atividades.length === 0 && (
                            <p className="text-sm text-muted-foreground text-center py-4">Nenhuma atividade registrada.</p>
                        )}

                        {leadDetail?.atividades.map((atv) => {
                            const tipoConfig = ATIVIDADE_TIPOS[atv.tipo] ?? ATIVIDADE_TIPOS.nota;
                            const TipoIcon = tipoConfig.icon;
                            return (
                                <div
                                    key={atv.id}
                                    className={`flex gap-3 p-2 rounded border text-sm ${atv.concluida ? "opacity-50" : ""}`}
                                >
                                    <button
                                        onClick={() => toggleAtividadeMutation.mutate(atv.id)}
                                        className="mt-0.5"
                                    >
                                        <CheckCircle2
                                            className={`size-4 ${atv.concluida ? "text-green-500" : "text-muted-foreground"}`}
                                        />
                                    </button>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-0.5">
                                            <Badge variant="outline" className="text-[9px] gap-0.5">
                                                <TipoIcon className="size-2.5" /> {tipoConfig.label}
                                            </Badge>
                                            <span className="text-[10px] text-muted-foreground">
                                                {formatDistanceToNow(new Date(atv.created_at), { addSuffix: true, locale: ptBR })}
                                            </span>
                                        </div>
                                        <p className={`text-sm ${atv.concluida ? "line-through" : ""}`}>{atv.descricao}</p>
                                        {atv.admin_email && (
                                            <p className="text-[10px] text-muted-foreground mt-0.5">por {atv.admin_email}</p>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* New Atividade inline */}
                    {showNewAtividade && (
                        <div className="border rounded p-3 space-y-3 bg-muted/20">
                            <Select value={newAtividade.tipo} onValueChange={(v: string) => setNewAtividade({ ...newAtividade, tipo: v })}>
                                <SelectTrigger className="h-8 text-xs">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {Object.entries(ATIVIDADE_TIPOS).map(([k, v]) => (
                                        <SelectItem key={k} value={k}>{v.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <Textarea
                                value={newAtividade.descricao}
                                onChange={(e) => setNewAtividade({ ...newAtividade, descricao: e.target.value })}
                                placeholder="Descreva a atividade..."
                                rows={2}
                                className="text-sm"
                            />
                            <div className="flex gap-2 justify-end">
                                <Button variant="ghost" onClick={() => setShowNewAtividade(false)}>Cancelar</Button>
                                <Button onClick={handleCreateAtividade} disabled={createAtividadeMutation.isPending}>
                                    Salvar
                                </Button>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </SheetContent>
    </Sheet>
  );
}
