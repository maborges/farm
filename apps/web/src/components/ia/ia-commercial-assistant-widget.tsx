"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Bot, MessageCircleMore, SendHorizontal, Sparkles, TrendingUp } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import {
  useIAGrowthAssistenteComercialContexto,
  useIAGrowthAssistenteComercialMensagem,
  type IAGrowthAssistenteContextoResponse,
} from "@/hooks";

type ChatRole = "assistant" | "user";

interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  ctaLabel?: string;
  ctaUrl?: string;
  planoRecomendado?: string;
  acaoSugerida?: string;
}

interface IACommercialAssistantWidgetProps {
  surface: "performance" | "billing" | "upgrade-card" | string;
  compact?: boolean;
  className?: string;
  triggerLabel?: string;
}

const QUICK_QUESTIONS = [
  "Por que esse plano é recomendado?",
  "O que ganho com o Profissional?",
  "Vale a pena ir para Enterprise?",
  "Como aproveitar melhor meu plano atual?",
];

const TIPO_OFERTA_BADGE: Record<string, { label: string; className: string }> = {
  SEM_INCENTIVO: { label: "Recomendado", className: "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400" },
  INCENTIVO_LEVE: { label: "Sugestão", className: "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400" },
  INCENTIVO_FORTE: { label: "Oportunidade", className: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400" },
  EDUCATIVO: { label: "Ajuda", className: "bg-sky-100 text-sky-700 border-sky-200 dark:bg-sky-900/30 dark:text-sky-400" },
  CONSULTIVO: { label: "Ajuda", className: "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-900/30 dark:text-slate-300" },
};

function buildIntro(contexto: IAGrowthAssistenteContextoResponse) {
  return [
    contexto.oportunidade_identificada,
    contexto.motivo_principal,
  ].join(" ");
}

export function IACommercialAssistantWidget({
  surface,
  compact = false,
  className,
  triggerLabel,
}: IACommercialAssistantWidgetProps) {
  const router = useRouter();
  const contextoQuery = useIAGrowthAssistenteComercialContexto();
  const mensagemMut = useIAGrowthAssistenteComercialMensagem();
  const [contexto, setContexto] = React.useState<IAGrowthAssistenteContextoResponse | null>(null);
  const [messages, setMessages] = React.useState<ChatMessage[]>([]);
  const [texto, setTexto] = React.useState("");
  const seededRef = React.useRef(false);

  React.useEffect(() => {
    if (contextoQuery.data) {
      setContexto(contextoQuery.data);
    }
  }, [contextoQuery.data]);

  React.useEffect(() => {
    if (seededRef.current || !contexto) return;
    seededRef.current = true;
    setMessages([
      {
        id: "assistant-initial",
        role: "assistant",
        content: buildIntro(contexto),
      },
    ]);
  }, [contexto]);

  const quickQuestions = contexto?.perguntas_sugeridas?.length
    ? contexto.perguntas_sugeridas.slice(0, 4)
    : QUICK_QUESTIONS;

  const enviarMensagem = async (textoUsuario: string) => {
    const mensagem = textoUsuario.trim();
    if (!mensagem) return;

    const contextoAtual = contexto ?? contextoQuery.data ?? null;
    const mensagemUsuario: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: mensagem,
    };

    setMessages((prev) => [...prev, mensagemUsuario]);
    setTexto("");

    try {
      const resultado = await mensagemMut.mutateAsync({
        mensagem_usuario: mensagem,
        contexto_atual: contextoAtual ?? undefined,
      });

      if (resultado.contexto) {
        setContexto(resultado.contexto);
      }

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: resultado.resposta_ia,
          ctaLabel: resultado.cta_sugerido,
          ctaUrl: resultado.cta_url,
          planoRecomendado: resultado.plano_recomendado,
          acaoSugerida: resultado.acao_sugerida,
        },
      ]);
    } catch {
      toast.error("Não foi possível responder agora. Tente novamente.");
    }
  };

  const handleQuickQuestion = (question: string) => {
    void enviarMensagem(question);
  };

  return (
    <Sheet data-surface={surface}>
      <SheetTrigger asChild>
        <Button
          variant={compact ? "outline" : "secondary"}
          size={compact ? "sm" : "default"}
          className={cn("gap-2 rounded-sm font-bold", className)}
        >
          <MessageCircleMore data-icon="inline-start" />
          {compact ? (triggerLabel ?? "Assistente") : (triggerLabel ?? "Assistente comercial")}
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="flex w-full flex-col gap-0 p-0 sm:max-w-xl">
        <SheetHeader className="border-b px-5 py-4">
          <div className="flex items-center gap-2">
            <span className="flex size-9 items-center justify-center rounded-sm bg-primary/10 text-primary">
              <Sparkles className="size-4" />
            </span>
            <div className="min-w-0">
              <SheetTitle className="flex items-center gap-2 text-base font-bold">
                <Bot className="size-4 text-primary" />
                Assistente Comercial IA
              </SheetTitle>
              <SheetDescription>
                Orientação consultiva para o seu plano, com foco em valor prático e próximo passo.
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div className="border-b bg-muted/30 px-5 py-4">
          {contextoQuery.isLoading && !contexto ? (
            <div className="space-y-2 text-sm text-muted-foreground">
              <p>Carregando contexto do assistente...</p>
            </div>
          ) : contexto ? (
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary" className="rounded-sm text-[10px] font-black uppercase">
                  {contexto.plano_atual_label}
                </Badge>
                <Badge variant="outline" className="rounded-sm text-[10px] font-black uppercase">
                  Sugestão: {contexto.plano_sugerido_label}
                </Badge>
                <Badge
                  variant="outline"
                  className={cn(
                    "rounded-sm text-[10px] font-black uppercase",
                    TIPO_OFERTA_BADGE[contexto.tipo_oferta]?.className ?? TIPO_OFERTA_BADGE.CONSULTIVO.className,
                  )}
                >
                  {TIPO_OFERTA_BADGE[contexto.tipo_oferta]?.label ?? TIPO_OFERTA_BADGE.CONSULTIVO.label}
                </Badge>
                <Badge variant="outline" className="rounded-sm text-[10px] font-black uppercase">
                  Fit {Math.round(contexto.score_fit * 100)}%
                </Badge>
                {contexto.visao_completa && (
                  <Badge
                    variant="outline"
                    className={cn(
                      "rounded-sm text-[10px] font-black uppercase",
                      contexto.churn_risk_level === "ALTO" && "border-amber-500/30 text-amber-600 bg-amber-500/5",
                      contexto.churn_risk_level === "MEDIO" && "border-blue-500/30 text-blue-600 bg-blue-500/5",
                      contexto.churn_risk_level === "BAIXO" && "border-emerald-500/30 text-emerald-600 bg-emerald-500/5",
                    )}
                  >
                    Risco {contexto.churn_risk_level.toLowerCase()}
                  </Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground">{contexto.resumo_perfil}</p>
              {contexto.mensagem_oferta && (
                <p className="text-xs text-muted-foreground/90">{contexto.mensagem_oferta}</p>
              )}
              {contexto.visao_completa ? (
                <div className="flex flex-col gap-2">
                  <div className="flex flex-wrap gap-2 text-[10px] font-bold uppercase">
                    {contexto.persona && (
                      <Badge variant="outline" className="rounded-sm">
                        Persona {contexto.persona}
                      </Badge>
                    )}
                    {contexto.safra_ano && (
                      <Badge variant="outline" className="rounded-sm">
                        Safra {contexto.safra_ano}
                      </Badge>
                    )}
                    {contexto.estagio_safra && (
                      <Badge variant="outline" className="rounded-sm">
                        Etapa {contexto.estagio_safra}
                      </Badge>
                    )}
                    {contexto.modulos_usados.slice(0, 3).map((modulo) => (
                      <Badge key={modulo} variant="secondary" className="rounded-sm">
                        {modulo}
                      </Badge>
                    ))}
                    <Badge variant="outline" className="rounded-sm">
                      CTA {contexto.cta_recente.clicks ?? 0}/{contexto.cta_recente.views ?? 0}
                    </Badge>
                  </div>
                  {contexto.features_bloqueadas.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {contexto.features_bloqueadas.slice(0, 2).map((feature) => (
                        <Badge key={feature} variant="outline" className="rounded-sm text-[10px] font-medium">
                          Bloqueado: {feature}
                        </Badge>
                      ))}
                    </div>
                  )}
                  {contexto.beneficio_destacado && (
                    <p className="text-[11px] text-emerald-700 dark:text-emerald-400 font-semibold">
                      Benefício destacado: {contexto.beneficio_destacado}
                    </p>
                  )}
                  {contexto.incentivo && contexto.incentivo.status === "OFERECIDO" && (
                    <div className="rounded-sm border border-blue-500/20 bg-blue-500/5 px-3 py-2">
                      <p className="text-[10px] font-black uppercase tracking-widest text-blue-700 dark:text-blue-300">
                        Benefício temporário disponível
                      </p>
                      <p className="mt-1 text-[11px] text-muted-foreground">
                        {contexto.incentivo.motivo} Válido até {new Date(contexto.incentivo.validade_fim).toLocaleDateString("pt-BR")}.
                      </p>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        <ScrollArea className="flex-1 px-5 py-4">
          <div className="flex flex-col gap-3">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex max-w-[92%] flex-col gap-2 rounded-sm border px-3 py-2 text-sm",
                  message.role === "user"
                    ? "ml-auto border-primary/20 bg-primary/5"
                    : "mr-auto border-border bg-background",
                )}
              >
                <div className="whitespace-pre-wrap leading-relaxed text-foreground">{message.content}</div>
                {message.role === "assistant" && message.ctaLabel && message.ctaUrl && (
                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-8 rounded-sm text-xs font-bold"
                      onClick={() => router.push(message.ctaUrl!)}
                    >
                      <TrendingUp data-icon="inline-start" />
                      {message.ctaLabel}
                    </Button>
                    {message.planoRecomendado && (
                      <Badge variant="secondary" className="rounded-sm text-[10px] font-black uppercase">
                        {message.planoRecomendado}
                      </Badge>
                    )}
                    {message.acaoSugerida && (
                      <Badge variant="outline" className="rounded-sm text-[10px] font-black uppercase">
                        {message.acaoSugerida}
                      </Badge>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>

        <div className="border-t bg-background px-5 py-4">
          <div className="flex flex-wrap gap-2">
            {quickQuestions.map((question) => (
              <Button
                key={question}
                type="button"
                variant="outline"
                size="sm"
                className="h-8 rounded-sm text-xs font-medium"
                onClick={() => handleQuickQuestion(question)}
              >
                {question}
              </Button>
            ))}
          </div>

          <Separator className="my-4" />

          <form
            className="flex flex-col gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              void enviarMensagem(texto);
            }}
          >
            <Textarea
              value={texto}
              onChange={(event) => setTexto(event.target.value)}
              placeholder="Escreva sua dúvida sobre planos, valor ou próximo passo..."
              className="min-h-24 resize-none rounded-sm"
            />
            <div className="flex items-center justify-between gap-3">
              <p className="text-[11px] text-muted-foreground">
                Sem upgrade automático. A decisão continua com você.
              </p>
              <Button
                type="submit"
                className="h-9 rounded-sm text-xs font-bold"
                disabled={mensagemMut.isPending}
              >
                <SendHorizontal data-icon="inline-start" />
                Enviar
              </Button>
            </div>
          </form>
        </div>
      </SheetContent>
    </Sheet>
  );
}
