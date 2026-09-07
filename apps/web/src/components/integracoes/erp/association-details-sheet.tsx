"use client";

import { useEffect, useState } from "react";
import { Loader2, Check, Link2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useToast } from "@/hooks/use-toast";
import { apiFetch } from "@/lib/api";
import { ExternalAssociationPendingItem } from "./types";
import { buildErpAssociationViewModel } from "./association-center-view-model";

interface AssociationDetailsSheetProps {
  association: ExternalAssociationPendingItem | null;
  onOpenChange: (open: boolean) => void;
  onReconciled: () => void;
}

export function AssociationDetailsSheet({
  association,
  onOpenChange,
  onReconciled,
}: AssociationDetailsSheetProps) {
  const { toast } = useToast();
  const [reconciling, setReconciling] = useState(false);
  const [draft, setDraft] = useState({
    local_entity_type: "",
    local_entity_id: "",
    reason: "",
  });

  useEffect(() => {
    if (association) {
      setDraft({
        local_entity_type: association.local_entity_type || "",
        local_entity_id: association.local_entity_id || "",
        reason: association.motivo || "",
      });
    }
  }, [association]);

  if (!association) return null;

  const vm = buildErpAssociationViewModel(association);

  async function handleReconcile() {
    if (!draft.local_entity_type || !draft.local_entity_id) {
      toast({
        title: "Erro",
        description: "Informe o cadastro interno e o identificador correspondente.",
        variant: "destructive",
      });
      return;
    }

    setReconciling(true);
    try {
      await apiFetch(`/integracoes/erp/associacoes/${association!.id}/reconciliar`, {
        method: "POST",
        body: {
          local_entity_type: draft.local_entity_type,
          local_entity_id: draft.local_entity_id,
          reason: draft.reason || "Vínculo confirmado manualmente",
          notes: "Ajuste manual de vínculo",
        },
      });
      toast({ title: "Sucesso", description: "Vínculo confirmado com sucesso." });
      onReconciled();
    } catch {
      toast({ title: "Erro", description: "Não foi possível confirmar o vínculo.", variant: "destructive" });
    } finally {
      setReconciling(false);
    }
  }

  return (
    <Sheet open={!!association} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-xl gap-0 p-0 flex flex-col">
        <SheetHeader className="border-b px-4 py-4 shrink-0">
          <div className="flex items-start gap-3 pr-8">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-sm bg-primary/10 text-primary">
              <Link2 className="size-4" />
            </div>
            <div className="min-w-0 flex-1 text-left">
              <SheetTitle>Detalhes da Associação</SheetTitle>
              <SheetDescription>
                Informações do registro no ERP e histórico de atualizações.
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto p-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Badge variant={vm.status === "ACTIVE" ? "default" : vm.status === "CONFLICT" ? "destructive" : "secondary"}>
                {vm.status}
              </Badge>
              <Badge variant="outline">{vm.externalEntityType}</Badge>
              <span className="font-medium">{vm.externalId}</span>
            </div>
            <p className="text-sm text-muted-foreground break-all">{association.external_key}</p>
            <p className="text-sm">Capability: <span className="font-medium">{vm.featureCode || "n/d"}</span></p>
            <p className="text-sm">Ambiente: <span className="font-medium">{vm.environment}</span></p>
          </div>

          <div>
            <div className="rounded-sm bg-muted/50 p-3 text-sm text-muted-foreground">
              Visualização restrita ao Backoffice. Contate o suporte técnico para auditar a carga (payload) original completa recebida da integração caso haja divergência.
              {association.external_payload && Object.keys(association.external_payload).length > 0 && (
                <div className="mt-2 text-xs">
                  <strong>Chaves indexadas:</strong>{" "}
                  {Object.keys(association.external_payload).join(", ")}
                </div>
              )}
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold border-b pb-2 mb-3">Histórico</h4>
            {vm.history.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sem histórico registrado.</p>
            ) : (
              <div className="space-y-2">
                {vm.history.slice().reverse().map((h) => (
                  <div key={h.id} className="text-xs rounded-sm border p-2 bg-muted/20">
                    <span className="font-medium">{h.event_type}</span>
                    <span className="text-muted-foreground">
                      {" "}· {h.reason || "sem observação"} · {new Date(h.created_at).toLocaleString("pt-BR")}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {vm.actions.canReconcile && (
            <div className="rounded-sm border p-4 bg-primary/5 space-y-4">
              <h4 className="text-sm font-semibold">Reconciliar Vínculo</h4>
              <div className="space-y-4">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="local-entity-type">Entidade local</Label>
                  <Input
                    id="local-entity-type"
                    className="h-8 rounded-sm text-sm"
                    value={draft.local_entity_type}
                    onChange={(e) => setDraft({ ...draft, local_entity_type: e.target.value })}
                    placeholder="Ex: Funcionario"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="local-entity-id">Identificador local</Label>
                  <Input
                    id="local-entity-id"
                    className="h-8 rounded-sm text-sm"
                    value={draft.local_entity_id}
                    onChange={(e) => setDraft({ ...draft, local_entity_id: e.target.value })}
                    placeholder="Ex: 12345"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="reason">Motivo (opcional)</Label>
                  <Input
                    id="reason"
                    className="h-8 rounded-sm text-sm"
                    value={draft.reason}
                    onChange={(e) => setDraft({ ...draft, reason: e.target.value })}
                    placeholder="Ex: Vínculo confirmado manualmente"
                  />
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full mt-2"
                  onClick={handleReconcile}
                  disabled={reconciling}
                >
                  {reconciling ? (
                    <><Loader2 data-icon="inline-start" className="animate-spin" /> Confirmando...</>
                  ) : (
                    <><Check data-icon="inline-start" /> Confirmar vínculo</>
                  )}
                </Button>
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

