"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { templateService } from "@/services/agro/template-service";
import { 
  Sheet, SheetContent, SheetHeader, SheetTitle, 
  SheetDescription, SheetFooter 
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Check, Info, LayoutTemplate, Lock, Zap, MapPin } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useHasTier } from "@/hooks/use-has-tier";
import { trackMonetizationEvent, useMonetizationPromptTracking } from "@/lib/monetization";

interface ApplyTemplateSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  safraId: string;
  cultura: string;
  fase: string;
  type: "PHASE" | "OPERATION";
  onApplied?: () => void;
}

interface CultivoArea {
  id: string;
  area_id: string;
  area_nome?: string | null;
  area_ha?: number | null;
}

interface CultivoComAreas {
  areas?: CultivoArea[];
}

interface AreaRural {
  id: string;
  nome: string;
}

export function ApplyTemplateSheet({ 
  open, onOpenChange, safraId, cultura, fase, type, onApplied 
}: ApplyTemplateSheetProps) {
  const queryClient = useQueryClient();
  const hasProfessionalTier = useHasTier("PROFISSIONAL");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedTalhoes, setSelectedTalhoes] = useState<string[]>([]);

  useMonetizationPromptTracking(!hasProfessionalTier, {
    feature: "agricola.templates",
    surface: "agricola.templates.sheet",
    requiredTier: "PROFISSIONAL",
    ctaLabel: "Ver opções de upgrade",
  });

  const { data: templates, isLoading } = useQuery({
    queryKey: ["templates", type, cultura, fase],
    queryFn: () => type === "PHASE" 
      ? templateService.listPhaseTemplates(cultura, fase)
      : templateService.listOperationTemplates(cultura, fase),
    enabled: open && hasProfessionalTier,
  });

  const { data: cultivos = [] } = useQuery<CultivoComAreas[]>({
    queryKey: ["safra-cultivos", safraId],
    queryFn: () => apiFetch(`/safras/${safraId}/cultivos`),
    enabled: open && hasProfessionalTier && type === "OPERATION",
  });

  const { data: todasAreas = [] } = useQuery<AreaRural[]>({
    queryKey: ["areas-rurais-talhoes"],
    queryFn: () => apiFetch("/cadastros/areas-rurais?tipo=TALHAO"),
    enabled: open && hasProfessionalTier && type === "OPERATION",
  });

  const allAreas = cultivos.flatMap(c => c.areas || []);
  const nomeTalhao = (areaId: string) =>
    todasAreas.find(a => a.id === areaId)?.nome || `Talhão ${areaId.substring(0, 4)}`;

  const toggleAllTalhoes = () => {
    if (selectedTalhoes.length === allAreas.length) setSelectedTalhoes([]);
    else setSelectedTalhoes(allAreas.map(a => a.area_id));
  };

  const toggleTalhao = (areaId: string) => {
    setSelectedTalhoes(prev =>
      prev.includes(areaId)
        ? prev.filter(id => id !== areaId)
        : [...prev, areaId]
    );
  };

  const applyMutation = useMutation({
    mutationFn: () => type === "PHASE"
      ? templateService.applyPhaseTemplate(safraId, selectedId!)
      : templateService.applyOperationTemplate(safraId, selectedId!, selectedTalhoes),
    onSuccess: () => {
      toast.success("Template aplicado com sucesso!");
      queryClient.invalidateQueries({ queryKey: ["checklist", safraId] });
      queryClient.invalidateQueries({ queryKey: ["safras", safraId, "tarefas"] });
      onOpenChange(false);
      onApplied?.();
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : "Erro ao aplicar template");
    }
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="sm:max-w-md flex flex-col h-full p-0">
        <SheetHeader className="p-6 pb-4 border-b space-y-1">
          <SheetTitle className="flex items-center gap-2 text-lg font-bold">
            <LayoutTemplate className="size-5 text-primary" />
            {type === "PHASE" ? "Templates de Governança" : "Templates Operacionais"}
          </SheetTitle>
          <SheetDescription className="text-xs leading-relaxed">
            Selecione um template pré-definido para instanciar tarefas e checklists na safra atual.
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="px-6 py-4">
              {!hasProfessionalTier ? (
                <Alert>
                  <Lock data-icon="inline-start" />
                  <AlertTitle>Recurso do plano Profissional</AlertTitle>
                  <AlertDescription>
                    <div className="flex flex-col gap-3">
                      <p>
                        A aplicação de templates automáticos exige plano PROFISSIONAL. A operação manual da safra continua disponível.
                      </p>
                      <Button
                        asChild
                        size="sm"
                        className="w-fit"
                        onClick={() => trackMonetizationEvent("monetization_cta_clicked", {
                          feature: "agricola.templates",
                          surface: "agricola.templates.sheet",
                          requiredTier: "PROFISSIONAL",
                          ctaLabel: "Ver opções de upgrade",
                        })}
                      >
                        <Link href="/dashboard/settings/billing">
                          Ver opções de upgrade
                        </Link>
                      </Button>
                    </div>
                  </AlertDescription>
                </Alert>
              ) : isLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map(i => <Skeleton key={i} className="h-20 w-full rounded-sm" />)}
                </div>
              ) : templates?.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground border border-dashed rounded-sm bg-muted/5">
                  <Info className="size-8 mb-2 opacity-20" />
                  <p className="text-sm font-medium">Nenhum template encontrado.</p>
                  <p className="text-[10px] uppercase tracking-widest mt-1 opacity-60">{cultura} • {fase}</p>
                </div>
              ) : (
                <div className="space-y-2.5">
                  <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-3 flex items-center gap-2">
                    <div className="h-px flex-1 bg-border" />
                    Disponíveis para {fase}
                    <div className="h-px flex-1 bg-border" />
                  </div>
                  {templates?.map((tmpl) => (
                    <button
                      type="button"
                      key={tmpl.id}
                      onClick={() => setSelectedId(tmpl.id)}
                      aria-pressed={selectedId === tmpl.id}
                      className={cn(
                        "group relative w-full p-3 rounded-sm border text-left transition-all duration-200",
                        selectedId === tmpl.id 
                          ? "border-primary/60 bg-primary/[0.03] shadow-sm ring-1 ring-primary/20" 
                          : "bg-card hover:bg-muted/30 hover:border-primary/30"
                      )}
                    >
                      <div className="flex justify-between items-center gap-2">
                        <h4 className={cn(
                          "text-sm font-bold truncate",
                          selectedId === tmpl.id ? "text-primary" : "text-foreground"
                        )}>
                          {tmpl.titulo}
                        </h4>
                        <div className="flex items-center gap-1.5 shrink-0">
                          {tmpl.is_system_default && (
                            <Badge variant="secondary" className="text-[9px] h-4 font-bold tracking-tight px-1 rounded-sm bg-primary/10 text-primary border-none">SISTEMA</Badge>
                          )}
                          {selectedId === tmpl.id && (
                            <div className="bg-primary text-primary-foreground rounded-full p-0.5">
                              <Check className="size-3" />
                            </div>
                          )}
                        </div>
                      </div>
                      {tmpl.descricao && (
                        <p className="text-[11px] text-muted-foreground line-clamp-2 mt-1.5 leading-tight opacity-80">
                          {tmpl.descricao}
                        </p>
                      )}
                      
                      <div className="flex items-center gap-2 mt-2.5">
                         <Badge variant="outline" className="text-[9px] py-0 border-primary/20 text-primary/70 font-bold rounded-sm h-4">
                           {tmpl.fase}
                         </Badge>
                         {tmpl.cultura && (
                           <Badge variant="outline" className="text-[9px] py-0 font-medium uppercase tracking-tighter rounded-sm h-4">
                             {tmpl.cultura}
                           </Badge>
                         )}
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Seleção de Talhões para Templates Operacionais */}
              {type === "OPERATION" && selectedId && allAreas.length > 0 && (
                <div className="mt-8 space-y-4 pb-4">
                  <div className="flex items-center gap-2 border-b pb-2">
                    <MapPin className="size-4 text-primary" />
                    <h4 className="text-sm font-bold">Onde aplicar?</h4>
                    <span className="text-[10px] text-muted-foreground uppercase ml-auto">
                      {selectedTalhoes.length} selecionado(s)
                    </span>
                  </div>
                  <div className="grid gap-2">
                    <div
                      className="flex items-center space-x-2 p-2 rounded-sm hover:bg-muted/30 cursor-pointer border border-transparent"
                      onClick={toggleAllTalhoes}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          toggleAllTalhoes();
                        }
                      }}
                      role="button"
                      tabIndex={0}
                      aria-pressed={selectedTalhoes.length === allAreas.length && allAreas.length > 0}
                    >
                      <Checkbox
                        checked={selectedTalhoes.length === allAreas.length && allAreas.length > 0}
                        tabIndex={-1}
                      />
                      <Label className="text-xs font-bold cursor-pointer">Selecionar todos os talhões</Label>
                    </div>
                    {allAreas.map((area) => (
                      <div
                        key={area.id} 
                        className={cn(
                          "flex items-center space-x-2 p-2 rounded-sm border transition-colors cursor-pointer hover:bg-muted/20",
                          selectedTalhoes.includes(area.area_id) ? "border-primary/20 bg-primary/5" : "border-transparent"
                        )}
                        onClick={() => toggleTalhao(area.area_id)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            toggleTalhao(area.area_id);
                          }
                        }}
                        role="button"
                        tabIndex={0}
                        aria-pressed={selectedTalhoes.includes(area.area_id)}
                      >
                        <Checkbox
                          checked={selectedTalhoes.includes(area.area_id)}
                          tabIndex={-1}
                        />
                        <Label className="text-xs cursor-pointer flex-1">
                          {nomeTalhao(area.area_id)}
                          <span className="text-[10px] text-muted-foreground ml-2">({area.area_ha} ha)</span>
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        <SheetFooter className="p-6 pt-4 border-t mt-auto">
          <div className="flex items-center justify-between w-full gap-3">
            <Button 
              variant="outline" 
              size="sm" 
              className="flex-1"
              onClick={() => onOpenChange(false)}
            >
              Cancelar
            </Button>
            <Button 
              size="sm" 
              className="flex-1"
              disabled={
                !hasProfessionalTier ||
                !selectedId ||
                applyMutation.isPending ||
                (type === "OPERATION" && selectedTalhoes.length === 0)
              }
              onClick={() => applyMutation.mutate()}
            >
              {applyMutation.isPending ? "Aplicando..." : "Aplicar agora"}
              {!applyMutation.isPending && <Zap className="size-3.5 ml-1.5" />}
            </Button>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
