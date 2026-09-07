"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import {
  Warehouse, ShoppingCart, Package, ClipboardList,
  AlertTriangle, Lock, ArrowRight, BarChart3, FileSpreadsheet,
} from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface Alerta { produto_id: string; produto_nome: string; deficit: number; }
interface Reserva { id: string; status: string; }
interface Requisicao { id: string; status: string; }
interface PedidoCompra { id: string; status: string; }

export default function SuprimentosPage() {
  const { activeFazendaId } = useAppStore();
  const fazendaParam = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";

  const { data: alertas = [] } = useQuery<Alerta[]>({
    queryKey: ["estoque-alertas", activeFazendaId],
    queryFn: () => apiFetch(`/estoque/alertas${fazendaParam}`),
  });
  const { data: reservas = [] } = useQuery<Reserva[]>({
    queryKey: ["estoque-reservas", activeFazendaId],
    queryFn: () => apiFetch(`/estoque/reservas?status=ATIVA`),
  });
  const { data: requisicoes = [] } = useQuery<Requisicao[]>({
    queryKey: ["estoque-requisicoes", activeFazendaId],
    queryFn: () => apiFetch(`/estoque/requisicoes${fazendaParam}&status=PENDENTE`),
  });
  const { data: pedidos = [] } = useQuery<PedidoCompra[]>({
    queryKey: ["compras-pedidos", activeFazendaId],
    queryFn: () => apiFetch(`/compras/pedidos${fazendaParam}`),
  });

  const pedidosAbertos = pedidos.filter(p => ["RASCUNHO", "APROVADO", "EM_RECEBIMENTO"].includes(p.status));

  const cards = [
    {
      href: "/suprimentos/saldos",
      icon: BarChart3,
      title: "Saldos de Estoque",
      description: "Visão consolidada e dashboards de disponibilidade por depósito.",
      color: "text-purple-600",
      bg: "bg-purple-50",
      badge: null,
    },
    {
      href: "/suprimentos/estoque",
      icon: Warehouse,
      title: "Almoxarifado",
      description: "Entradas, saídas, transferências, ajustes e inventário físico.",
      color: "text-primary",
      bg: "bg-primary/5",
      badge: alertas.length > 0 ? { label: `${alertas.length} repor`, variant: "red" } : null,
    },
    {
      href: "/suprimentos/estoque/implantacao-assistida",
      icon: FileSpreadsheet,
      title: "Implantação Assistida",
      description: "Carga inicial guiada para gravar SALDO_INICIAL sem misturar onboarding com operação normal.",
      color: "text-sky-600",
      bg: "bg-sky-50",
      badge: null,
    },
    {
      href: "/suprimentos/compras",
      icon: ShoppingCart,
      title: "Compras",
      description: "Pedidos de compra, recebimento parcial e devoluções a fornecedores.",
      color: "text-blue-600",
      bg: "bg-blue-50",
      badge: pedidosAbertos.length > 0 ? { label: `${pedidosAbertos.length} abertos`, variant: "blue" } : null,
    },
    {
      href: "/suprimentos/lotes",
      icon: Package,
      title: "Lotes de Estoque",
      description: "Rastreabilidade por lote — validade, quantidade e origem.",
      color: "text-emerald-600",
      bg: "bg-emerald-50",
      badge: null,
    },
    {
      href: "/suprimentos/requisicoes",
      icon: ClipboardList,
      title: "Requisições Internas",
      description: "Fluxo de aprovação de materiais entre equipes e depósitos.",
      color: "text-orange-600",
      bg: "bg-orange-50",
      badge: requisicoes.length > 0 ? { label: `${requisicoes.length} pendentes`, variant: "orange" } : null,
    },
  ];

  const badgeClass: Record<string, string> = {
    red:    "bg-red-100 text-red-700 border-red-200",
    blue:   "bg-blue-100 text-blue-700 border-blue-200",
    orange: "bg-orange-100 text-orange-700 border-orange-200",
    purple: "bg-purple-100 text-purple-700 border-purple-200",
  };

  return (
    <div className="p-6 space-y-6 w-full">
      <PageHeader
        title="Estoque & Suprimentos"
        description="Gestão completa de materiais — do pedido ao consumo."
        icon={<Warehouse className="text-primary" />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Suprimentos" },
        ]}
      />

      {/* Alertas de atenção */}
      {(alertas.length > 0 || reservas.length > 0 || requisicoes.length > 0) && (
        <div className="flex flex-wrap gap-3">
          {alertas.length > 0 && (
            <div className="flex items-center gap-2 rounded-sm border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              <AlertTriangle size={13} />
              <strong>{alertas.length}</strong> produto(s) abaixo do estoque mínimo
            </div>
          )}
          {reservas.length > 0 && (
            <div className="flex items-center gap-2 rounded-sm border border-purple-200 bg-purple-50 px-3 py-2 text-xs text-purple-700">
              <Lock size={13} />
              <strong>{reservas.length}</strong> reserva(s) ativa(s)
            </div>
          )}
          {requisicoes.length > 0 && (
            <div className="flex items-center gap-2 rounded-sm border border-orange-200 bg-orange-50 px-3 py-2 text-xs text-orange-700">
              <ClipboardList size={13} />
              <strong>{requisicoes.length}</strong> requisição(ões) aguardando aprovação
            </div>
          )}
        </div>
      )}

      {/* Cards de navegação */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {cards.map(card => (
          <Link key={card.href} href={card.href}>
            <Card className="h-full shadow-sm hover:shadow-md transition-shadow cursor-pointer group">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className={cn("p-2.5 rounded-sm", card.bg)}>
                    <card.icon className={cn("size-5", card.color)} />
                  </div>
                  <div className="flex items-center gap-2">
                    {card.badge && (
                      <Badge className={cn("text-[10px] border font-normal", badgeClass[card.badge.variant])}>
                        {card.badge.label}
                      </Badge>
                    )}
                    <ArrowRight size={16} className="text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </div>
                <CardTitle className="text-base mt-3">{card.title}</CardTitle>
                <CardDescription className="text-xs">{card.description}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
