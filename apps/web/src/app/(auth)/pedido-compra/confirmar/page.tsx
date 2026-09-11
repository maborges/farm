"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Loader2, CheckCircle2, XCircle, Sprout, ShieldCheck, Ban } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { AuthLayout } from "@/components/auth/auth-layout";

interface ItemPedidoConfirmacao {
  produto_nome: string;
  quantidade: number;
  unidade: string;
  preco_unitario: number;
  valor_total: number;
}

interface PedidoConfirmacaoDetails {
  status: "PENDENTE" | "CONFIRMADO" | "RECUSADO" | "EXPIRADO";
  fornecedor_nome: string;
  tenant_nome: string;
  itens: ItemPedidoConfirmacao[];
  valor_total: number;
  condicoes_pagamento?: string | null;
}

const formatarBRL = (valor: number) =>
  valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function ConfirmarPedidoContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"loading" | "details" | "confirmado" | "recusado" | "error">("loading");
  const [pedido, setPedido] = useState<PedidoConfirmacaoDetails | null>(null);
  const [message, setMessage] = useState("");
  const [senha, setSenha] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("O link de confirmação é inválido ou está corrompido.");
      return;
    }
    (async () => {
      try {
        const data = await apiFetch<PedidoConfirmacaoDetails>(`/compras-publico/pedidos/confirmar/${token}`);
        setPedido(data);
        if (data.status === "CONFIRMADO") setStatus("confirmado");
        else if (data.status === "RECUSADO") setStatus("recusado");
        else if (data.status === "EXPIRADO") { setStatus("error"); setMessage("Este link de confirmação expirou."); }
        else setStatus("details");
      } catch (error: any) {
        setStatus("error");
        setMessage(error.message || "Este link não é mais válido.");
      }
    })();
  }, [token]);

  const responder = async (aceito: boolean) => {
    if (!senha.trim()) {
      toast.error("Informe a senha de confirmação recebida no e-mail.");
      return;
    }
    setIsProcessing(true);
    try {
      const data = await apiFetch<PedidoConfirmacaoDetails>(`/compras-publico/pedidos/confirmar/${token}`, {
        method: "POST",
        body: JSON.stringify({ senha, aceito }),
      });
      setPedido(data);
      setStatus(aceito ? "confirmado" : "recusado");
      toast.success(aceito ? "Pedido confirmado com sucesso!" : "Pedido recusado.");
    } catch (error: any) {
      toast.error(error.message || "Senha incorreta ou link inválido.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="w-full max-w-[620px] animate-in fade-in zoom-in duration-500">
      <div className="flex flex-col items-center mb-8 gap-3">
        <div className="flex size-11 items-center justify-center rounded-sm bg-primary border border-primary/20 shadow-lg shadow-primary/20">
          <Sprout className="size-6 text-primary-foreground" />
        </div>
      </div>

      <Card className="rounded-sm border-border bg-card/60 backdrop-blur-xl shadow-premium p-8 relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-[1.5px] bg-gradient-to-r from-transparent via-primary/40 to-transparent" />

        {status === "loading" && (
          <div className="flex flex-col items-center py-8 gap-4 text-center">
            <Loader2 className="size-10 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground font-medium animate-pulse">Carregando pedido de compra...</p>
          </div>
        )}

        {status === "details" && pedido && (
          <div className="space-y-6">
            <div className="space-y-2 text-center">
              <Badge variant="outline" className="bg-primary/5 border-primary/20 text-primary text-[10px] uppercase font-black tracking-widest px-2 py-0.5">
                Pedido de Compra
              </Badge>
              <h3 className="text-2xl font-black text-foreground leading-tight tracking-tight">
                {pedido.tenant_nome}
              </h3>
              <p className="text-sm text-muted-foreground">
                Aguarda sua confirmação de aceite, {pedido.fornecedor_nome}.
              </p>
            </div>

            <div className="py-4 border-y border-border/10 text-sm space-y-3">
              <div className="overflow-x-auto -mx-1">
                <table className="w-full text-xs min-w-[340px]">
                  <thead>
                    <tr className="border-b border-border/20 text-muted-foreground">
                      <th className="text-left font-semibold uppercase tracking-wider py-1.5 px-1">Produto</th>
                      <th className="text-right font-semibold uppercase tracking-wider py-1.5 px-1">Qtd.</th>
                      <th className="text-right font-semibold uppercase tracking-wider py-1.5 px-1">Preço unit.</th>
                      <th className="text-right font-semibold uppercase tracking-wider py-1.5 px-1">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pedido.itens.map((item, idx) => (
                      <tr key={idx} className="border-b border-border/10 last:border-0">
                        <td className="py-1.5 px-1 text-foreground font-medium">{item.produto_nome}</td>
                        <td className="py-1.5 px-1 text-right text-foreground">{item.quantidade} {item.unidade}</td>
                        <td className="py-1.5 px-1 text-right text-foreground">{formatarBRL(item.preco_unitario)}</td>
                        <td className="py-1.5 px-1 text-right text-foreground font-bold">{formatarBRL(item.valor_total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex justify-between items-center pt-1">
                <span className="text-muted-foreground font-medium">Valor total do pedido</span>
                <span className="text-foreground font-bold">{formatarBRL(pedido.valor_total)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground font-medium">Condições de pagamento</span>
                <span className="text-foreground font-bold">{pedido.condicoes_pagamento || "A combinar"}</span>
              </div>
            </div>

            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="senha-confirmacao" className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                  Senha de confirmação (recebida por e-mail)
                </Label>
                <Input
                  id="senha-confirmacao"
                  placeholder="000000"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                />
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                A senha existe para evitar confirmações acidentais — só prossiga se você realmente aceita este pedido.
              </p>
              <div className="grid grid-cols-2 gap-3 pt-2">
                <Button
                  variant="outline"
                  disabled={isProcessing}
                  className="border-destructive/30 text-destructive hover:bg-destructive/5 font-black uppercase tracking-widest text-xs"
                  onClick={() => responder(false)}
                >
                  <Ban size={14} className="mr-2" /> Recusar
                </Button>
                <Button
                  disabled={isProcessing}
                  className="bg-primary hover:bg-primary/90 text-primary-foreground font-black uppercase tracking-widest text-xs"
                  onClick={() => responder(true)}
                >
                  {isProcessing ? <Loader2 className="animate-spin size-4" /> : <><ShieldCheck size={14} className="mr-2" /> Confirmar</>}
                </Button>
              </div>
            </div>
          </div>
        )}

        {status === "confirmado" && (
          <div className="flex flex-col items-center text-center py-6 space-y-6">
            <div className="size-20 rounded-full bg-primary/10 flex items-center justify-center border border-primary/20">
              <CheckCircle2 className="size-10 text-primary" />
            </div>
            <div className="space-y-2">
              <h3 className="text-2xl font-black text-foreground tracking-tight">Pedido Confirmado!</h3>
              <p className="text-sm text-muted-foreground leading-relaxed max-w-[280px]">
                Obrigado por confirmar. {pedido?.tenant_nome} foi notificado do seu aceite.
              </p>
            </div>
          </div>
        )}

        {status === "recusado" && (
          <div className="flex flex-col items-center text-center py-6 space-y-6">
            <div className="size-20 rounded-full bg-muted flex items-center justify-center border border-border">
              <Ban className="size-10 text-muted-foreground" />
            </div>
            <div className="space-y-2">
              <h3 className="text-2xl font-black text-foreground tracking-tight">Pedido Recusado</h3>
              <p className="text-sm text-muted-foreground leading-relaxed max-w-[280px]">
                Sua recusa foi registrada e {pedido?.tenant_nome} foi notificado.
              </p>
            </div>
          </div>
        )}

        {status === "error" && (
          <div className="flex flex-col items-center text-center py-6 space-y-6">
            <div className="size-20 rounded-full bg-destructive/10 flex items-center justify-center border border-destructive/20">
              <XCircle className="size-10 text-destructive" />
            </div>
            <div className="space-y-2">
              <h3 className="text-2xl font-black text-foreground">Link Indisponível</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{message}</p>
            </div>
          </div>
        )}
      </Card>

      <p className="text-center text-[10px] text-muted-foreground/30 mt-8 font-bold uppercase tracking-widest">
        Segurança DeepFarms · 2026
      </p>
    </div>
  );
}

export default function ConfirmarPedidoPage() {
  return (
    <AuthLayout badgeLabel="Confirmação de Pedido" contentMaxWidthClassName="max-w-[620px]">
      <Suspense fallback={
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="animate-spin text-primary size-12" />
          <p className="text-white/20 text-xs font-bold uppercase tracking-widest">Carregando...</p>
        </div>
      }>
        <ConfirmarPedidoContent />
      </Suspense>
    </AuthLayout>
  );
}
