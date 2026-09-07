"use client";

import { ChevronDown, ChevronRight, FolderTree, Map, Sprout, Trees, Droplets, Building2, Fence, ShieldCheck, Layers, LayoutGrid, Warehouse } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { AREA_HIERARQUIA } from "@farm/zod-schemas";
import { useState } from "react";

// Ícones por tipo de área
const AREA_ICONS: Record<string, React.ReactNode> = {
  AREA_RURAL:       <FolderTree className="w-3.5 h-3.5" />,
  GLEBA:            <Map className="w-3.5 h-3.5" />,
  TALHAO:           <Sprout className="w-3.5 h-3.5" />,
  AREA_AMBIENTAL:   <ShieldCheck className="w-3.5 h-3.5" />,
  AREA_OPERACIONAL: <LayoutGrid className="w-3.5 h-3.5" />,
  PIQUETE:          <Fence className="w-3.5 h-3.5" />,
  ZONA_MANEJO:      <Layers className="w-3.5 h-3.5" />,
  SUBTALHAO:        <Sprout className="w-3.5 h-3.5" />,
  APP:              <Droplets className="w-3.5 h-3.5" />,
  RESERVA_LEGAL:    <Trees className="w-3.5 h-3.5" />,
  INFRAESTRUTURA:   <Building2 className="w-3.5 h-3.5" />,
  SEDE:             <Building2 className="w-3.5 h-3.5" />,
  ARMAZEM:          <Warehouse className="w-3.5 h-3.5" />,
  CURRAL:           <Fence className="w-3.5 h-3.5" />,
  OUTROS:           <FolderTree className="w-3.5 h-3.5" />,
};

// Cores por tipo de área
const AREA_COLORS: Record<string, string> = {
  AREA_RURAL:       "bg-green-600",
  GLEBA:            "bg-purple-500",
  TALHAO:           "bg-emerald-500",
  AREA_AMBIENTAL:   "bg-blue-400",
  AREA_OPERACIONAL: "bg-teal-500",
  PIQUETE:          "bg-cyan-500",
  ZONA_MANEJO:      "bg-teal-600",
  SUBTALHAO:        "bg-emerald-600",
  APP:              "bg-blue-500",
  RESERVA_LEGAL:    "bg-green-700",
  INFRAESTRUTURA:   "bg-slate-500",
  SEDE:             "bg-slate-600",
  ARMAZEM:          "bg-amber-600",
  CURRAL:           "bg-orange-600",
  OUTROS:           "bg-gray-500",
};

// Labels por tipo
const AREA_LABELS: Record<string, string> = {
  AREA_RURAL:       "Área Rural",
  GLEBA:            "Gleba",
  TALHAO:           "Talhão",
  AREA_AMBIENTAL:   "Área Ambiental",
  AREA_OPERACIONAL: "Área Operacional",
  PIQUETE:          "Piquete",
  ZONA_MANEJO:      "Zona de Manejo",
  SUBTALHAO:        "Subtalhão",
  APP:              "APP",
  RESERVA_LEGAL:    "Reserva Legal",
  INFRAESTRUTURA:   "Infraestrutura",
  SEDE:             "Sede",
  ARMAZEM:          "Armazém",
  CURRAL:           "Curral",
  OUTROS:           "Outros",
};

// Descrições explicativas por tipo
const AREA_DESCRICOES: Record<string, string> = {
  AREA_RURAL:       "Contêiner principal que agrupa todas as áreas da propriedade",
  GLEBA:            "Parcela de terra com matrícula cartorial própria",
  TALHAO:           "Unidade básica de plantio com polígono definido",
  AREA_AMBIENTAL:   "Agrupamento de áreas de preservação ambiental",
  AREA_OPERACIONAL: "Subdivisão operacional para gerenciamento de talhões",
  PIQUETE:          "Subdivisão de pastagem para rotação de gado",
  ZONA_MANEJO:      "Zona de manejo para agricultura de precisão",
  SUBTALHAO:        "Subdivisão administrativa de talhão",
  APP:              "Área de Preservação Permanente (margens de rios, nascentes, encostas)",
  RESERVA_LEGAL:    "Vegetação nativa obrigatória por lei (Código Florestal)",
  INFRAESTRUTURA:   "Agrupamento de benfeitorias físicas da propriedade",
  SEDE:             "Sede administrativa ou moradia",
  ARMAZEM:          "Armazém, silo ou galpão de armazenamento",
  CURRAL:           "Curral, mangueira ou brete para manejo de animais",
  OUTROS:           "Outras benfeitorias não classificadas acima",
};

interface HierarquiaNode {
  tipo: string;
  filhos?: HierarquiaNode[];
}

// Estrutura hierárquica completa para exibição
const HIERARQUIA_COMPLETA: HierarquiaNode[] = [
  {
    tipo: "AREA_RURAL",
    filhos: [
      {
        tipo: "GLEBA",
        filhos: [
          {
            tipo: "TALHAO",
            filhos: [
              {
                tipo: "AREA_OPERACIONAL",
                filhos: [
                  { tipo: "PIQUETE" },
                  { tipo: "ZONA_MANEJO" },
                  { tipo: "SUBTALHAO" },
                ],
              },
            ],
          },
          {
            tipo: "AREA_AMBIENTAL",
            filhos: [
              { tipo: "APP" },
              { tipo: "RESERVA_LEGAL" },
            ],
          },
        ],
      },
    ],
  },
  {
    tipo: "INFRAESTRUTURA",
    filhos: [
      { tipo: "SEDE" },
      { tipo: "ARMAZEM" },
      { tipo: "CURRAL" },
      { tipo: "OUTROS" },
    ],
  },
];

function HierarquiaItem({ node, level = 0 }: { node: HierarquiaNode; level?: number }) {
  const [isExpanded, setIsExpanded] = useState(level < 2);
  const hasChildren = node.filhos && node.filhos.length > 0;

  return (
    <div className="select-none">
      <div
        className={cn(
          "flex items-center gap-2 py-1.5 px-2 rounded-md hover:bg-accent/50 transition-all cursor-pointer group"
        )}
        style={{ paddingLeft: `${level * 20 + 8}px` }}
        onClick={() => hasChildren && setIsExpanded(!isExpanded)}
      >
        {/* Toggle */}
        <button
          className={cn(
            "w-4 h-4 flex items-center justify-center rounded shrink-0",
            hasChildren ? "opacity-100" : "opacity-0 pointer-events-none"
          )}
        >
          {isExpanded ? (
            <ChevronDown className="w-3 h-3 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-3 h-3 text-muted-foreground" />
          )}
        </button>

        {/* Ícone */}
        <div
          className={cn(
            "w-6 h-6 rounded flex items-center justify-center text-white shrink-0",
            AREA_COLORS[node.tipo] || "bg-gray-500"
          )}
        >
          {AREA_ICONS[node.tipo] || <FolderTree className="w-3.5 h-3.5" />}
        </div>

        {/* Informações */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">{AREA_LABELS[node.tipo]}</span>
            <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4">
              {node.tipo}
            </Badge>
          </div>
        </div>
      </div>

      {/* Descrição */}
      {level === 0 && (
        <p className="text-xs text-muted-foreground ml-10 -mt-1 mb-1">
          {AREA_DESCRICOES[node.tipo]}
        </p>
      )}

      {/* Filhos (recursivo) */}
      {hasChildren && isExpanded && (
        <div className="transition-all border-l border-border/50 ml-4">
          {node.filhos.map((filho, idx) => (
            <HierarquiaItem
              key={`${filho.tipo}-${idx}`}
              node={filho}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function EstruturaHierarquia({
  className,
  propriedadeNome,
}: {
  className?: string;
  propriedadeNome?: string;
}) {
  const nomePropriedade = propriedadeNome ?? "esta propriedade";
  return (
    <Card className={cn("border-dashed", className)}>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <FolderTree className="w-4 h-4 text-primary" />
          Estrutura de Áreas da Propriedade
        </CardTitle>
        <CardDescription className="text-xs">
          {`A estrutura abaixo ilustra como organizar ${nomePropriedade} em glebas, talhões e infraestrutura.`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Árvore hierárquica */}
        <div className="rounded-lg border bg-muted/30 p-3 space-y-2">
          {HIERARQUIA_COMPLETA.map((node, idx) => (
            <HierarquiaItem key={`${node.tipo}-${idx}`} node={node} />
          ))}
        </div>

        {/* Legenda */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">Legenda:</p>
          <div className="flex flex-wrap gap-2">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded bg-green-600" />
              <span className="text-xs">Territorial</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded bg-blue-400" />
              <span className="text-xs">Ambiental</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded bg-slate-500" />
              <span className="text-xs">Infraestrutura</span>
            </div>
          </div>
        </div>

        {/* Exemplo de uso */}
        <div className="rounded-md bg-primary/5 border border-primary/10 p-3">
          <p className="text-xs font-medium text-primary mb-1">Exemplo de uso:</p>
          <p className="text-xs text-muted-foreground leading-relaxed">
            <strong>{propriedadeNome ?? "A propriedade atual"}</strong> → Gleba Norte → Talhão 01 → Área Operacional → Piquete A, Piquete B
            <br />
            <strong>{propriedadeNome ?? "A propriedade atual"}</strong> → Gleba Sul → Área Ambiental → APP (margem do rio), Reserva Legal
            <br />
            <strong>{propriedadeNome ?? "A propriedade atual"}</strong> → Infraestrutura → Sede, Armazém, Curral
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
