"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { AlertTriangle, ArrowLeft, Map, MapPinned, FileText, LandPlot, Building2, ShieldCheck, Layers, Trees, Database, RefreshCw, CircleDashed, ArrowUpRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import {
  useVisaoTerritorial,
  useVisaoFundiaria,
  type DocumentoFundiarioResumo,
  type ImovelFundiarioResumo,
  type MatriculaFundiariaResumo,
  type VinculoTerritorialResumo,
} from "@/lib/hooks/use-territorial-visao";

function fmtArea(value?: string | number | null) {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? `${n.toLocaleString("pt-BR", { maximumFractionDigits: 4 })} ha` : "—";
}

function fmtPercent(value?: string | number | null) {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? `${n.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%` : "—";
}

const TIPO_AREA_MAP: Record<string, string> = {
  "AREA_RURAL": "Área Rural",
  "INFRAESTRUTURA": "Infraestrutura",
  "GLEBA": "Gleba",
  "TALHAO": "Talhão",
  "AREA_AMBIENTAL": "Área Ambiental",
  "AREA_OPERACIONAL": "Área Operacional",
  "PIQUETE": "Piquete",
  "ZONA_MANEJO": "Zona de Manejo",
  "SUBTALHAO": "Subtalhão",
  "APP": "Área de Preservação (APP)",
  "RESERVA_LEGAL": "Reserva Legal",
  "SEDE": "Sede",
  "ARMAZEM": "Armazém",
  "CURRAL": "Curral",
  "OUTROS": "Outros",
  // Legado
  "FAZENDA": "Fazenda",
  "RETIRO": "Retiro",
  "PASTO": "Pasto",
  "RESERVA": "Reserva Legal",
};

function formatEnumLabel(value: string | undefined | null) {
  if (!value) return "—";
  return value
    .split("_")
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

function formatTipoArea(tipo: string | undefined | null) {
  if (!tipo) return "—";
  const upper = tipo.toUpperCase();
  return TIPO_AREA_MAP[upper] || formatEnumLabel(tipo);
}


function fmtDate(value?: string | null) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString("pt-BR");
}

function SourceBadge({ label }: { label: string }) {
  return <Badge variant="outline" className="rounded-sm text-[10px] uppercase tracking-wide">{label}</Badge>;
}

function RelationBadge({ children }: { children: ReactNode }) {
  return <Badge variant="secondary" className="rounded-sm text-[10px] uppercase">{children}</Badge>;
}

function RelationMeta({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-sm border bg-muted/20 p-2">
      <p className="text-[10px] font-semibold uppercase text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm">{value}</p>
    </div>
  );
}

function SectionCard({
  icon,
  title,
  description,
  children,
}: {
  icon: ReactNode;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <Card className="rounded-sm shadow-sm">
      <CardHeader className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-primary">{icon}</span>
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  );
}

function LoadingState() {
  return (
    <div className="space-y-6 p-6">
      <Skeleton className="h-10 w-72 rounded-sm" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-sm" />)}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-72 rounded-sm" />
        <Skeleton className="h-72 rounded-sm" />
      </div>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="space-y-6 p-6">
      <Alert variant="destructive" className="rounded-sm">
        <AlertTriangle className="size-4" />
        <AlertDescription>{message}</AlertDescription>
      </Alert>
      <Button variant="outline" size="sm" className="rounded-sm gap-2" onClick={onRetry}>
        <RefreshCw className="size-4" /> Tentar novamente
      </Button>
    </div>
  );
}

function StatGrid({ items }: { items: Array<{ label: string; value: string }> }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <Card key={item.label} className="rounded-sm shadow-sm">
          <CardContent className="pt-6">
            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">{item.label}</p>
            <p className="mt-2 text-lg font-semibold text-foreground">{item.value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function DocumentosList({ documentos }: { documentos: DocumentoFundiarioResumo[] }) {
  if (documentos.length === 0) {
    return (
      <EmptyState
        icon={<FileText />}
        title="Sem documentos disponíveis"
        description="Não há documentos resumidos vinculados a este imóvel."
      />
    );
  }

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {documentos.map((doc) => (
        <div key={doc.id} className="rounded-sm border bg-muted/20 p-3 space-y-2">
          <div className="flex items-center justify-between gap-3">
            <strong className="text-sm">{formatEnumLabel(doc.tipo)}</strong>
            <Badge variant="secondary" className="rounded-sm text-[10px] uppercase">{doc.status}</Badge>
          </div>
          <p className="text-sm text-muted-foreground">{doc.descricao || "Documento resumido"}</p>
          <div className="flex flex-wrap gap-2 text-[11px] text-muted-foreground">
            <span>Número: {doc.numero_documento || "—"}</span>
            <span>Versão: {doc.versao}</span>
            <span>Emissão: {fmtDate(doc.data_emissao)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function MatriculasList({ matriculas }: { matriculas: MatriculaFundiariaResumo[] }) {
  if (matriculas.length === 0) {
    return (
      <EmptyState
        icon={<Building2 />}
        title="Sem matrículas disponíveis"
        description="Nenhuma matrícula foi resumida para este imóvel."
      />
    );
  }

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {matriculas.map((matricula) => (
        <div key={matricula.id} className="rounded-sm border p-3 space-y-2">
          <div className="flex items-center justify-between">
            <strong className="text-sm">{matricula.numero_matricula}</strong>
            <Badge variant="outline" className="rounded-sm text-[10px] uppercase">Matricula</Badge>
          </div>
          <div className="text-sm text-muted-foreground space-y-1">
            <p>Cartório: {matricula.cartorio_nome || "—"}</p>
            <p>Área: {fmtArea(matricula.area_matricula_ha)}</p>
            <p>Transmissão: {fmtDate(matricula.data_transmissao)}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function VinculosList({ vinculos }: { vinculos: VinculoTerritorialResumo[] }) {
  if (vinculos.length === 0) {
    return (
      <EmptyState
        icon={<Layers />}
        title="Sem vínculos registrados"
        description="A visão consolidada não encontrou vínculos PropriedadeImovel para esta entidade."
      />
    );
  }

  return (
    <div className="grid gap-3">
      {vinculos.map((vinculo) => (
        <div key={vinculo.id} className="rounded-sm border p-4 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <strong className="text-sm">{vinculo.propriedade?.nome || vinculo.imovel_rural?.nome || "Vínculo"}</strong>
            <Badge variant="outline" className="rounded-sm text-[10px] uppercase">{vinculo.tipo_vinculo.replace(/_/g, " ")}</Badge>
            {vinculo.vinculo_principal && <Badge className="rounded-sm text-[10px] uppercase">Principal</Badge>}
            {!vinculo.ativo && <Badge variant="secondary" className="rounded-sm text-[10px] uppercase">Inativo</Badge>}
          </div>
          <div className="grid gap-2 md:grid-cols-4 text-sm text-muted-foreground">
            <p>Início: {fmtDate(vinculo.data_inicio)}</p>
            <p>Fim: {fmtDate(vinculo.data_fim)}</p>
            <p>Área: {fmtArea(vinculo.area_vinculada)}</p>
            <p>%: {fmtPercent(vinculo.percentual_vinculado)}</p>
          </div>
          <p className="text-sm text-muted-foreground">{vinculo.origem_documental}</p>
          {vinculo.origem_referencia && <p className="text-xs text-muted-foreground">Referência: {vinculo.origem_referencia}</p>}
        </div>
      ))}
    </div>
  );
}

export function VisaoTerritorialPropriedadeClient({ propriedadeId }: { propriedadeId: string }) {
  const query = useVisaoTerritorial(propriedadeId);

  if (query.isLoading) {
    return <LoadingState />;
  }

  if (query.isError) {
    return <ErrorState message={query.error instanceof Error ? query.error.message : "Erro ao carregar visão territorial."} onRetry={() => query.refetch()} />;
  }

  const data = query.data;
  if (!data) {
    return (
      <div className="p-6">
        <EmptyState
          icon={<CircleDashed />}
          title="Visão territorial indisponível"
          description="Não foi possível carregar a visão consolidada desta propriedade."
          action={{ label: "Recarregar", onClick: () => query.refetch() }}
        />
      </div>
    );
  }

  const vinculosPorImovel = new globalThis.Map<string, VinculoTerritorialResumo[]>();
  const vinculosPorPropriedade = new globalThis.Map<string, VinculoTerritorialResumo[]>();
  data.vinculos.forEach((vinculo) => {
    if (vinculo.imovel_rural) {
      const lista = vinculosPorImovel.get(vinculo.imovel_rural.id) ?? [];
      lista.push(vinculo);
      vinculosPorImovel.set(vinculo.imovel_rural.id, lista);
    }
    if (vinculo.propriedade) {
      const lista = vinculosPorPropriedade.get(vinculo.propriedade.id) ?? [];
      lista.push(vinculo);
      vinculosPorPropriedade.set(vinculo.propriedade.id, lista);
    }
  });

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title={`Visão Territorial — ${data.propriedade.nome}`}
        description="Leitura consolidada, somente leitura, da operação territorial da propriedade."
        icon={<Map className="size-5" />}
        breadcrumbs={[
          { label: "Cadastros", href: "/cadastros" },
          { label: "Propriedades", href: "/cadastros/propriedades" },
          { label: data.propriedade.nome },
        ]}
        actions={
          <Button asChild variant="outline" size="sm" className="rounded-sm gap-2">
            <Link href="/cadastros/propriedades">
              <ArrowLeft className="size-4" /> Voltar
            </Link>
          </Button>
        }
      />

      <StatGrid
        items={[
          { label: "Áreas operacionais", value: String(data.areas_operacionais.length) },
          { label: "Explorações rurais", value: String(data.exploracoes_rurais.length) },
          { label: "Imóveis vinculados", value: String(data.imoveis_rurais.length) },
          { label: "Vínculos oficiais", value: String(data.vinculos.length) },
        ]}
      />

      <SectionCard icon={<Trees className="size-4" />} title="Dados da Propriedade" description="Origem oficial: Propriedade">
        <div className="grid gap-3 md:grid-cols-3 text-sm">
          <div><span className="text-muted-foreground">Nome</span><p className="font-medium">{data.propriedade.nome}</p></div>
          <div><span className="text-muted-foreground">CPF/CNPJ</span><p className="font-medium">{data.propriedade.cpf_cnpj || "—"}</p></div>
          <div><span className="text-muted-foreground">Inscrição Estadual</span><p className="font-medium">{data.propriedade.inscricao_estadual || "—"}</p></div>
        </div>
      </SectionCard>

      <SectionCard icon={<LandPlot className="size-4" />} title="Áreas operacionais" description="Camada operacional e territorial da propriedade">
        {data.areas_operacionais.length === 0 ? (
          <EmptyState icon={<LandPlot />} title="Sem áreas operacionais" description="Não há áreas operacionais agregadas para esta propriedade." />
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {data.areas_operacionais.map((area) => (
              <div key={area.id} className="rounded-sm border p-3 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <strong className="text-sm">{area.nome}</strong>
                  <SourceBadge label="Propriedade" />
                </div>
                <div className="flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                  <span>Tipo: {formatTipoArea(area.tipo)}</span>
                  <span>Código: {area.codigo || "—"}</span>
                  <span>Área: {fmtArea(area.area_hectares)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard icon={<Layers className="size-4" />} title="Explorações rurais" description="Relações operacionais da propriedade">
        {data.exploracoes_rurais.length === 0 ? (
          <EmptyState icon={<Layers />} title="Sem explorações rurais" description="Nenhuma exploração foi vinculada a esta propriedade." />
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {data.exploracoes_rurais.map((exploracao) => (
              <div key={exploracao.id} className="rounded-sm border p-3 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <strong className="text-sm">{formatEnumLabel(exploracao.natureza)}</strong>
                  <SourceBadge label="Propriedade" />
                </div>
                <div className="grid gap-1 text-[11px] text-muted-foreground">
                  <span>Início: {fmtDate(exploracao.data_inicio)}</span>
                  <span>Fim: {fmtDate(exploracao.data_fim)}</span>
                  <span>Área explorada: {fmtArea(exploracao.area_explorada_ha)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard icon={<Building2 className="size-4" />} title="Imóveis rurais vinculados" description="Resumo fundiário/documental vindo do domínio Imóvel Rural">
        {data.imoveis_rurais.length === 0 ? (
          <EmptyState icon={<Building2 />} title="Sem imóveis rurais vinculados" description="Nenhum imóvel rural foi encontrado para esta propriedade." />
        ) : (
          <div className="grid gap-4">
            {data.imoveis_rurais.map((imovel) => {
              const vinculosDoImovel = vinculosPorImovel.get(imovel.id) ?? [];
              return (
                <div key={imovel.id} className="rounded-sm border p-4 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <strong className="text-sm">{imovel.nome}</strong>
                      <p className="text-xs text-muted-foreground">{imovel.municipio}/{imovel.uf}</p>
                    </div>
                    <Button asChild size="sm" variant="outline" className="rounded-sm gap-1.5">
                      <Link href={`/cadastros/imoveis/${imovel.id}/visao-fundiaria`}>
                        Abrir visão fundiária
                        <ArrowUpRight className="size-3.5" />
                      </Link>
                    </Button>
                  </div>
                  <div className="grid gap-2 md:grid-cols-4 text-sm">
                    <RelationMeta label="Área total" value={fmtArea(imovel.area_total_ha)} />
                    <RelationMeta label="NIRF" value={imovel.nirf || "—"} />
                    <RelationMeta label="CAR" value={imovel.car_numero || "—"} />
                    <RelationMeta label="CCIR" value={imovel.ccir_numero || "—"} />
                  </div>
                  <div className="grid gap-2 md:grid-cols-3">
                    <RelationMeta label="Matrícula" value={imovel.numero_matricula || "—"} />
                    <RelationMeta label="SIGEF" value={imovel.sigef_codigo || "—"} />
                    <RelationMeta label="Cartório" value={imovel.cartorio ? `${imovel.cartorio.nome} • ${imovel.cartorio.comarca}/${imovel.cartorio.uf}` : "Cartório não informado"} />
                  </div>
                  <div className="rounded-sm border bg-muted/20 p-3">
                    <p className="text-xs font-semibold uppercase text-muted-foreground">Documentos resumidos</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {imovel.documentos_resumo.length === 0 ? (
                        <span className="text-sm text-muted-foreground">Sem documentos disponíveis</span>
                      ) : (
                        imovel.documentos_resumo.map((doc) => (
                          <Badge key={doc.id} variant="secondary" className="rounded-sm text-[10px] uppercase">{doc.tipo.replace(/_/g, " ")}</Badge>
                        ))
                      )}
                    </div>
                  </div>
                  <div className="rounded-sm bg-muted/10 p-3">
                    <p className="text-xs font-semibold uppercase text-muted-foreground">Vínculos desta propriedade</p>
                    <div className="mt-2 grid gap-2">
                      {vinculosDoImovel.length === 0 ? (
                        <span className="text-sm text-muted-foreground">Sem vínculo oficial registrado para esta propriedade.</span>
                      ) : (
                        vinculosDoImovel.map((vinculo) => (
                          <div key={vinculo.id} className="rounded-sm border bg-background p-3 space-y-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <RelationBadge>{vinculo.tipo_vinculo}</RelationBadge>
                              {vinculo.vinculo_principal && <Badge className="rounded-sm text-[10px] uppercase">Principal</Badge>}
                              {!vinculo.ativo && <Badge variant="secondary" className="rounded-sm text-[10px] uppercase">Inativo</Badge>}
                            </div>
                            <div className="grid gap-2 md:grid-cols-4 text-sm">
                              <RelationMeta label="Início" value={fmtDate(vinculo.data_inicio)} />
                              <RelationMeta label="Fim" value={fmtDate(vinculo.data_fim)} />
                              <RelationMeta label="Área vinculada" value={fmtArea(vinculo.area_vinculada)} />
                              <RelationMeta label="Percentual" value={fmtPercent(vinculo.percentual_vinculado)} />
                            </div>
                            <p className="text-xs text-muted-foreground">{vinculo.origem_documental}</p>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </SectionCard>

      <SectionCard icon={<ShieldCheck className="size-4" />} title="Vínculos PropriedadeImovel" description="Relação oficial entre operação e fundiário">
        <VinculosList vinculos={data.vinculos} />
      </SectionCard>
    </div>
  );
}

export function VisaoFundiariaImovelClient({ imovelId }: { imovelId: string }) {
  const query = useVisaoFundiaria(imovelId);

  if (query.isLoading) {
    return <LoadingState />;
  }

  if (query.isError) {
    return <ErrorState message={query.error instanceof Error ? query.error.message : "Erro ao carregar visão fundiária."} onRetry={() => query.refetch()} />;
  }

  const data = query.data;
  if (!data) {
    return (
      <div className="p-6">
        <EmptyState
          icon={<CircleDashed />}
          title="Visão fundiária indisponível"
          description="Não foi possível carregar a visão consolidada deste imóvel rural."
          action={{ label: "Recarregar", onClick: () => query.refetch() }}
        />
      </div>
    );
  }

  const imovel = data.imovel_rural;
  const vinculosPorPropriedade = new globalThis.Map<string, VinculoTerritorialResumo[]>();
  data.vinculos.forEach((vinculo) => {
    if (vinculo.propriedade) {
      const lista = vinculosPorPropriedade.get(vinculo.propriedade.id) ?? [];
      lista.push(vinculo);
      vinculosPorPropriedade.set(vinculo.propriedade.id, lista);
    }
  });

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title={`Visão Fundiária — ${imovel.nome}`}
        description="Leitura consolidada, somente leitura, dos dados fundiários do imóvel rural."
        icon={<MapPinned className="size-5" />}
        breadcrumbs={[
          { label: "Cadastros", href: "/cadastros" },
          { label: "Imóveis Rurais", href: "/cadastros/imoveis" },
          { label: imovel.nome },
        ]}
        actions={
          <Button asChild variant="outline" size="sm" className="rounded-sm gap-2">
            <Link href="/cadastros/imoveis">
              <ArrowLeft className="size-4" /> Voltar
            </Link>
          </Button>
        }
      />

      <StatGrid
        items={[
          { label: "Propriedades vinculadas", value: String(data.propriedades_vinculadas.length) },
          { label: "Documentos resumidos", value: String(imovel.documentos_resumo.length) },
          { label: "Matrículas", value: String(imovel.matriculas_resumo.length) },
          { label: "Vínculos oficiais", value: String(data.vinculos.length) },
        ]}
      />

      <SectionCard icon={<Database className="size-4" />} title="Dados do Imóvel Rural" description="Origem oficial: Imóvel Rural">
        <div className="grid gap-3 md:grid-cols-3">
          <div><span className="text-xs text-muted-foreground">Nome</span><p className="font-medium">{imovel.nome}</p></div>
          <div><span className="text-xs text-muted-foreground">Município/UF</span><p className="font-medium">{imovel.municipio}/{imovel.uf}</p></div>
          <div><span className="text-xs text-muted-foreground">Área total</span><p className="font-medium">{fmtArea(imovel.area_total_ha)}</p></div>
          <div><span className="text-xs text-muted-foreground">CAR</span><p className="font-medium">{imovel.car_numero || "—"}</p></div>
          <div><span className="text-xs text-muted-foreground">CCIR</span><p className="font-medium">{imovel.ccir_numero || "—"}</p></div>
          <div><span className="text-xs text-muted-foreground">NIRF</span><p className="font-medium">{imovel.nirf || "—"}</p></div>
          <div><span className="text-xs text-muted-foreground">Matrícula</span><p className="font-medium">{imovel.numero_matricula || "—"}</p></div>
          <div><span className="text-xs text-muted-foreground">SIGEF</span><p className="font-medium">{imovel.sigef_codigo || "—"}</p></div>
        </div>
      </SectionCard>

      <SectionCard icon={<FileText className="size-4" />} title="Documentos fundiários" description="Resumo documental do domínio fundiário">
        <DocumentosList documentos={imovel.documentos_resumo} />
      </SectionCard>

      <SectionCard icon={<Building2 className="size-4" />} title="Matrículas e cartório" description="Referências registrárias resumidas">
        <MatriculasList matriculas={imovel.matriculas_resumo} />
      </SectionCard>

      <SectionCard icon={<Trees className="size-4" />} title="Propriedades vinculadas" description="Operações vinculadas ao imóvel rural">
        {data.propriedades_vinculadas.length === 0 ? (
          <EmptyState
            icon={<Trees />}
            title="Sem propriedades vinculadas"
            description="Não há propriedades associadas a este imóvel rural."
          />
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {data.propriedades_vinculadas.map((propriedade) => {
              const vinculosDaPropriedade = vinculosPorPropriedade.get(propriedade.id) ?? [];
              return (
                <div key={propriedade.id} className="rounded-sm border p-3 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <strong className="text-sm">{propriedade.nome}</strong>
                      <p className="text-xs text-muted-foreground">{propriedade.cpf_cnpj || "CPF/CNPJ não informado"}</p>
                    </div>
                    <Button asChild size="sm" variant="outline" className="rounded-sm gap-1.5">
                      <Link href={`/cadastros/propriedades/${propriedade.id}/visao-territorial`}>
                        Abrir visão territorial
                        <ArrowUpRight className="size-3.5" />
                      </Link>
                    </Button>
                  </div>
                  <div className="grid gap-2">
                    {vinculosDaPropriedade.length === 0 ? (
                      <span className="text-sm text-muted-foreground">Sem vínculo oficial registrado para esta propriedade.</span>
                    ) : (
                      vinculosDaPropriedade.map((vinculo) => (
                        <div key={vinculo.id} className="rounded-sm border bg-muted/20 p-3 space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <RelationBadge>{vinculo.tipo_vinculo}</RelationBadge>
                            {vinculo.vinculo_principal && <Badge className="rounded-sm text-[10px] uppercase">Principal</Badge>}
                            {!vinculo.ativo && <Badge variant="secondary" className="rounded-sm text-[10px] uppercase">Inativo</Badge>}
                          </div>
                          <div className="grid gap-2 md:grid-cols-4 text-sm">
                            <RelationMeta label="Início" value={fmtDate(vinculo.data_inicio)} />
                            <RelationMeta label="Fim" value={fmtDate(vinculo.data_fim)} />
                            <RelationMeta label="Área vinculada" value={fmtArea(vinculo.area_vinculada)} />
                            <RelationMeta label="Percentual" value={fmtPercent(vinculo.percentual_vinculado)} />
                          </div>
                          <p className="text-xs text-muted-foreground">{vinculo.origem_documental}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </SectionCard>

      <SectionCard icon={<ShieldCheck className="size-4" />} title="Vínculos PropriedadeImovel" description="Relação oficial entre fundiário e operacional">
        <VinculosList vinculos={data.vinculos} />
      </SectionCard>
    </div>
  );
}
