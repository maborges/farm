"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import {
  LayoutDashboard, Warehouse, ShoppingCart, Package, ClipboardList,
  AlertTriangle, Lock, BarChart3, FileSpreadsheet, CheckCircle2,
} from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { QuickActionGrid } from "@/components/ui/quick-action-grid";
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

  const actionCommands = [
    {
      href: "/suprimentos/saldos",
      icon: BarChart3,
      title: "Saldos de Estoque",
      description: "Disponibilidade por depósito",
      color: "text-purple-600 dark:text-purple-400",
      bg: "bg-purple-500/10",
      badge: null,
    },
    {
      href: "/suprimentos/estoque",
      icon: Warehouse,
      title: "Almoxarifado",
      description: "Entradas, saídas e transferências",
      color: "text-primary",
      bg: "bg-primary/10",
      badge: alertas.length > 0 ? `${alertas.length} repor` : null,
      badgeColor: "text-red-700 border-red-300 bg-red-50 dark:bg-red-950/20",
    },
    {
      href: "/suprimentos/compras",
      icon: ShoppingCart,
      title: "Compras",
      description: "Pedidos e recebimentos",
      color: "text-blue-600 dark:text-blue-400",
      bg: "bg-blue-500/10",
      badge: pedidosAbertos.length > 0 ? `${pedidosAbertos.length} abertos` : null,
      badgeColor: "text-blue-700 border-blue-300 bg-blue-50 dark:bg-blue-950/20",
    },
    {
      href: "/suprimentos/requisicoes",
      icon: ClipboardList,
      title: "Requisições",
      description: "Aprovações e solicitações internas",
      color: "text-orange-600 dark:text-orange-400",
      bg: "bg-orange-500/10",
      badge: requisicoes.length > 0 ? `${requisicoes.length} pendentes` : null,
      badgeColor: "text-orange-700 border-orange-300 bg-orange-50 dark:bg-orange-950/20",
    },
    {
      href: "/suprimentos/lotes",
      icon: Package,
      title: "Lotes & Validade",
      description: "Rastreabilidade e quarentena",
      color: "text-emerald-600 dark:text-emerald-400",
      bg: "bg-emerald-500/10",
      badge: null,
    },
    {
      href: "/suprimentos/estoque/implantacao-assistida",
      icon: FileSpreadsheet,
      title: "Implantação Assistida",
      description: "Carga inicial e inventário físico",
      color: "text-sky-600 dark:text-sky-400",
      bg: "bg-sky-500/10",
      badge: null,
    },
  ];

  const hasPendencias = alertas.length > 0 || reservas.length > 0 || requisicoes.length > 0 || pedidosAbertos.length > 0;

  return (
    <div className="p-6 space-y-6 w-full">
      <PageHeader
        title="Painel de Suprimentos"
        description="Gestão integrada de estoques, insumos agrícolas, compras e requisições de campo."
        icon={<LayoutDashboard className="text-primary" />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Suprimentos" },
        ]}
      />

      {/* ── Central de Ações & Comandos Rápidos ── */}
      <QuickActionGrid
        label="Ações & Atalhos de Suprimentos"
        columnsClassName="grid-cols-2 sm:grid-cols-3 lg:grid-cols-6"
        actions={actionCommands.map((cmd) => ({
          title: cmd.title,
          description: cmd.description,
          icon: cmd.icon,
          href: cmd.href,
          badge: cmd.badge,
        }))}
      />

      {/* ── Seção de Atenção e Pendências Críticas ── */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
          Precisa de Atenção no Almoxarifado
        </h3>

        {hasPendencias ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {alertas.length > 0 && (
              <div className="rounded-sm border border-red-200 bg-red-50/60 p-4 dark:border-red-900/50 dark:bg-red-950/20 flex flex-col justify-between">
                <div className="flex items-center gap-2 text-red-700 dark:text-red-400 font-semibold text-xs">
                  <AlertTriangle className="size-4 shrink-0" />
                  <span>Estoque Mínimo Atingido</span>
                </div>
                <p className="text-2xl font-bold text-red-800 dark:text-red-300 mt-2">{alertas.length} produto(s)</p>
                <p className="text-[11px] text-muted-foreground mt-1">Exigem pedido de reposição urgente.</p>
                <Button asChild size="sm" variant="outline" className="mt-3 w-fit h-7 text-xs rounded-sm border-red-300 hover:bg-red-100 dark:border-red-800">
                  <Link href="/suprimentos/saldos">Verificar déficit</Link>
                </Button>
              </div>
            )}

            {requisicoes.length > 0 && (
              <div className="rounded-sm border border-orange-200 bg-orange-50/60 p-4 dark:border-orange-900/50 dark:bg-orange-950/20 flex flex-col justify-between">
                <div className="flex items-center gap-2 text-orange-700 dark:text-orange-400 font-semibold text-xs">
                  <ClipboardList className="size-4 shrink-0" />
                  <span>Requisições Pendentes</span>
                </div>
                <p className="text-2xl font-bold text-orange-800 dark:text-orange-300 mt-2">{requisicoes.length} solicitação(ões)</p>
                <p className="text-[11px] text-muted-foreground mt-1">Aguardando aprovação para saída.</p>
                <Button asChild size="sm" variant="outline" className="mt-3 w-fit h-7 text-xs rounded-sm border-orange-300 hover:bg-orange-100 dark:border-orange-800">
                  <Link href="/suprimentos/requisicoes">Aprovar requisições</Link>
                </Button>
              </div>
            )}

            {pedidosAbertos.length > 0 && (
              <div className="rounded-sm border border-blue-200 bg-blue-50/60 p-4 dark:border-blue-900/50 dark:bg-blue-950/20 flex flex-col justify-between">
                <div className="flex items-center gap-2 text-blue-700 dark:text-blue-400 font-semibold text-xs">
                  <ShoppingCart className="size-4 shrink-0" />
                  <span>Compras em Andamento</span>
                </div>
                <p className="text-2xl font-bold text-blue-800 dark:text-blue-300 mt-2">{pedidosAbertos.length} pedido(s)</p>
                <p className="text-[11px] text-muted-foreground mt-1">Em rascunho, aprovados ou aguardando recebimento.</p>
                <Button asChild size="sm" variant="outline" className="mt-3 w-fit h-7 text-xs rounded-sm border-blue-300 hover:bg-blue-100 dark:border-blue-800">
                  <Link href="/suprimentos/compras">Acompanhar compras</Link>
                </Button>
              </div>
            )}

            {reservas.length > 0 && (
              <div className="rounded-sm border border-purple-200 bg-purple-50/60 p-4 dark:border-purple-900/50 dark:bg-purple-950/20 flex flex-col justify-between">
                <div className="flex items-center gap-2 text-purple-700 dark:text-purple-400 font-semibold text-xs">
                  <Lock className="size-4 shrink-0" />
                  <span>Reservas Ativas</span>
                </div>
                <p className="text-2xl font-bold text-purple-800 dark:text-purple-300 mt-2">{reservas.length} lote(s)</p>
                <p className="text-[11px] text-muted-foreground mt-1">Materiais alocados para ordens de serviço.</p>
                <Button asChild size="sm" variant="outline" className="mt-3 w-fit h-7 text-xs rounded-sm border-purple-300 hover:bg-purple-100 dark:border-purple-800">
                  <Link href="/suprimentos/estoque">Consultar reservas</Link>
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="rounded-sm border border-emerald-500/20 bg-emerald-500/5 p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-sm bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="size-5" />
              </div>
              <div>
                <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">Almoxarifado em dia</p>
                <p className="text-xs text-muted-foreground">Nenhum produto em ruptura de estoque e todas as requisições estão processadas.</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

