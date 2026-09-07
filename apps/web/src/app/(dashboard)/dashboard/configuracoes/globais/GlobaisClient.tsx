"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConfiguracoesGeraisForm } from "@/components/configuracoes/configuracoes-gerais-form";
import { CategoriasManager } from "@/components/configuracoes/categorias-manager";
import { HistoricoTable } from "@/components/configuracoes/historico-table";
import { SequenciaisManager } from "@/components/configuracoes/sequenciais-manager";
import { Settings, Tag, History, Hash } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";

interface ConfigGeral {
  ano_agricola: { mes_inicio: number; mes_fim: number };
  unidade_area: string;
  moeda: string;
  fuso_horario: string;
  idioma: string;
}

interface SequencialConfig {
  entidade: string;
  label: string;
  prefixo: string;
  digitos: number;
  escopo: "ANO" | "GLOBAL";
  personalizado: boolean;
  ultimo_numero: number;
}

interface GlobaisClientProps {
  initialConfigGeral: ConfigGeral | null;
  initialSequenciais: SequencialConfig[] | null;
}

export function GlobaisClient({ initialConfigGeral, initialSequenciais }: GlobaisClientProps) {
  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Configurações Globais"
        description="Parâmetros transversais aplicados a todos os módulos da plataforma."
        icon={<Settings className="h-8 w-8 text-primary" />}
      />

      <Tabs defaultValue="geral">
        <TabsList>
          <TabsTrigger value="geral" className="gap-1.5">
            <Settings className="w-4 h-4" />
            Geral
          </TabsTrigger>
          <TabsTrigger value="categorias" className="gap-1.5">
            <Tag className="w-4 h-4" />
            Categorias
          </TabsTrigger>
          <TabsTrigger value="sequenciais" className="gap-1.5">
            <Hash className="w-4 h-4" />
            Códigos de Referência
          </TabsTrigger>
          <TabsTrigger value="historico" className="gap-1.5">
            <History className="w-4 h-4" />
            Histórico
          </TabsTrigger>
        </TabsList>

        <TabsContent value="geral" className="mt-6">
          <ConfiguracoesGeraisForm initialData={initialConfigGeral} />
        </TabsContent>

        <TabsContent value="categorias" className="mt-6">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Categorias customizáveis usadas em despesas, receitas, operações e produtos.
              Categorias marcadas como <strong>Sistema</strong> não podem ser editadas.
            </p>
            <CategoriasManager />
          </div>
        </TabsContent>

        <TabsContent value="sequenciais" className="mt-6">
          <SequenciaisManager initialData={initialSequenciais ?? undefined} />
        </TabsContent>

        <TabsContent value="historico" className="mt-6">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Registro de todas as alterações nas configurações globais do tenant.
            </p>
            <HistoricoTable />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
