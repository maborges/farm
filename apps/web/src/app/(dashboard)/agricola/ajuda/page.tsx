"use client";

import { useState, useMemo } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Search, Database, HelpCircle, Sprout, Calendar, MapPin, BookOpen, AlertCircle, Lightbulb } from "lucide-react";

// ---------------------------------------------------------------------------
// Dicionário de Dados
// ---------------------------------------------------------------------------

const dicionario = [
    {
        termo: "Safra",
        categoria: "Conceito Central",
        definicao: "Representa o período produtivo (tempo). Não ocupa espaço físico. É o contexto que agrupa cultivos de uma mesma campanha agrícola.",
        exemplo: "Safra 2025 | Safra 2025/26",
        regras: ["Formato: AAAA ou AAAA/AA", "Uma safra pode ter múltiplos cultivos", "Safras podem se sobrepor no tempo"],
    },
    {
        termo: "Talhão",
        categoria: "Espaço Físico",
        definicao: "Representa o espaço físico produtivo dentro de uma fazenda. É uma subdivisão geográfica da propriedade. Não controla tempo.",
        exemplo: "Talhão A1 — 50 ha | Talhão B2 — 30 ha",
        regras: ["Área medida em hectares (ha)", "Pode ser utilizado por múltiplas safras ao longo do tempo", "Não pode ser sobreocupado no mesmo período (exceto consórcio)"],
    },
    {
        termo: "Cultivo",
        categoria: "Conceito Central",
        definicao: "Representa a ocupação real — a interseção entre espaço (talhão) e tempo (safra). É a unidade central de negócio do sistema. Toda operação, custo e produção pertence ao cultivo.",
        exemplo: "Cultivo: Café Bourbon — Talhão A1 — 40 ha — Safra 2025",
        regras: [
            "Associado a uma safra e um ou mais talhões",
            "Controla área ocupada (ha) por talhão",
            "Possui período de ocupação (data_inicio → data_fim)",
            "Pode ser consorciado com outros cultivos",
        ],
    },
    {
        termo: "Consorciado",
        categoria: "Ocupação",
        definicao: "Indica que dois ou mais cultivos compartilham o mesmo espaço físico (talhão) no mesmo período. Permite sobreposição de área sem gerar conflito de validação.",
        exemplo: "Café (40 ha) + Milho Safrinha (30 ha) no mesmo talhão de 50 ha — ambos marcados como consorciados",
        regras: [
            "Ambos os cultivos devem ser marcados como consorciados",
            "Custos e produções são rastreados separadamente por cultivo",
            "Não confundir com rotação (cultivos em períodos diferentes)",
        ],
    },
    {
        termo: "Rotação de Culturas",
        categoria: "Estratégia Agrícola",
        definicao: "Prática de alternar diferentes culturas no mesmo talhão ao longo do tempo (safras diferentes). Os períodos não se sobrepõem.",
        exemplo: "Talhão A1: Soja (2024) → Milho (2025) → Braquiária (2026)",
        regras: [
            "Use os campos 'Início da ocupação' e 'Fim da ocupação' no cultivo",
            "Não é necessário marcar como consorciado",
            "Permite análise de histórico por talhão",
        ],
    },
    {
        termo: "Pousio",
        categoria: "Estratégia Agrícola",
        definicao: "Período de descanso do solo sem cultivo produtivo. Deve ser registrado como um cultivo técnico para manter o histórico completo do talhão.",
        exemplo: "Cultivo: POUSIO — Talhão A1 — período: mar/2025 a ago/2025",
        regras: [
            "Registrar com cultura = 'POUSIO' ou 'COBERTURA VEGETAL'",
            "Define datas de início e fim",
            "Permite registrar custos de manejo do solo (controle de ervas, etc.)",
        ],
    },
    {
        termo: "CultivoArea",
        categoria: "Modelo de Dados",
        definicao: "Entidade que vincula um cultivo a um talhão específico com uma área definida. Um cultivo pode ocupar múltiplos talhões, cada um com sua área.",
        exemplo: "Cultivo Café → Talhão A1: 40 ha | Talhão A2: 20 ha",
        regras: [
            "area_ha deve ser maior que 0",
            "area_ha não pode ultrapassar a área cadastrada do talhão",
            "A soma de cultivos não-consorciados não pode ultrapassar a área do talhão no mesmo período",
        ],
    },
    {
        termo: "Romaneio de Colheita",
        categoria: "Produção",
        definicao: "Registro de uma colheita — documenta peso bruto, umidade, impurezas, sacas colhidas e produtividade por hectare. Vinculado ao cultivo específico.",
        exemplo: "Romaneio #001 — Café Bourbon — Talhão A1 — 1.200 kg bruto — 20 sacas",
        regras: [
            "Sempre associar ao cultivo para rastreamento de produção por cultura",
            "Produtividade calculada automaticamente (sc/ha)",
            "Rastreável até o lote de beneficiamento",
        ],
    },
    {
        termo: "Lote de Beneficiamento",
        categoria: "Pós-Colheita",
        definicao: "Processo de transformação do café colhido em produto final (café beneficiado). Rastreia o método de processamento e rendimento.",
        exemplo: "Lote #001 — Natural — 1.000 kg cereja → 200 kg beneficiado (rendimento 20%)",
        regras: [
            "Métodos: NATURAL, LAVADO, HONEY, DESCASCADO",
            "Vinculado ao romaneio de origem e ao cultivo",
            "Gera lote de estoque para comercialização",
        ],
    },
    {
        termo: "Orçamento de Safra",
        categoria: "Financeiro",
        definicao: "Planejamento financeiro de custos e receitas esperadas para uma safra. Itens podem ser vinculados a cultivos específicos para análise por cultura.",
        exemplo: "Fertilizante — Café Bourbon — 500 kg × R$ 4,00 = R$ 2.000",
        regras: [
            "Categorias: SEMENTE, FERTILIZANTE, DEFENSIVO, COMBUSTIVEL, MAO_DE_OBRA, SERVICO, OUTROS",
            "Pode ser vinculado a cultivo específico ou aplicado a toda a safra",
            "Comparável ao custo realizado no fechamento",
        ],
    },
    {
        termo: "Operação Agrícola",
        categoria: "Campo",
        definicao: "Registro de operação realizada no campo: plantio, pulverização, adubação, colheita. Vinculada ao cultivo para rastreamento de custo operacional por cultura.",
        exemplo: "Adubação — Café Bourbon — 15/03/2025 — 2 ha aplicados — R$ 500",
        regras: [
            "Tipos: PLANTIO, PULVERIZACAO, ADUBACAO, COLHEITA, CAPINA, PODA",
            "Insumos aplicados são registrados com dose e custo",
            "Sempre vincular ao cultivo para custo real por cultura",
        ],
    },
    {
        termo: "Fenologia",
        categoria: "Monitoramento",
        definicao: "Registro dos estágios de desenvolvimento da planta ao longo da safra. Permite acompanhar a evolução do cultivo por talhão.",
        exemplo: "Café — Talhão A1 — Florada: 15/08 — Frutificação: out/2025",
        regras: [
            "Estágios variam por cultura",
            "Pode ser agrupado por grupos de talhões para controle mais eficiente",
            "Base para alertas e recomendações agronômicas",
        ],
    },
];

const categorias = ["Todas", ...Array.from(new Set(dicionario.map(d => d.categoria)))];

// ---------------------------------------------------------------------------
// Guia Passo-a-Passo (baseado no manual)
// ---------------------------------------------------------------------------

const guias = [
    {
        titulo: "🎬 PASSO 1: Criar a Safra",
        conteudo: (
            <div className="space-y-4">
                <div>
                    <h4 className="font-semibold text-sm mb-2">Onde encontrar?</h4>
                    <p className="text-sm text-muted-foreground">Menu: Agricultura → ⑥ Resultados → Resumo de Safras</p>
                </div>
                <Alert variant="info">
                    <AlertDescription>
                        <strong>O que é um Cultivo?</strong> Uma safra pode ter um ou mais cultivos. Cada cultivo representa uma cultura específica plantada em determinados talhões durante aquela safra. Isso permite rastrear custos, operações e orçamento separadamente por cultura.
                    </AlertDescription>
                </Alert>
                <div>
                    <h4 className="font-semibold text-sm mb-2">Como criar?</h4>
                    <ol className="space-y-2 text-sm text-muted-foreground">
                        <li>1. Clique em <strong>&quot;+ Nova Safra&quot;</strong> (botão no topo)</li>
                        <li>2. Preencha o <strong>Ano Agrícola</strong> (ex: &quot;2025&quot; ou &quot;2025/26&quot;)</li>
                        <li>3. Na seção <strong>Cultivos</strong>, clique <strong>&quot;+ Cultivo&quot;</strong></li>
                        <li>4. Preencha: Cultura, Cultivar (opcional), Talhões, Área a Plantar (ha)</li>
                        <li>5. Se houver consórcio, marque &quot;Consorciado&quot; e defina datas</li>
                        <li>6. Clique &quot;Criar Safra&quot;</li>
                    </ol>
                </div>
                <Alert variant="warning">
                    <AlertDescription>
                        <strong>⚠️ Validação:</strong> A área a plantar não pode ser maior que a área real do talhão.
                    </AlertDescription>
                </Alert>
            </div>
        ),
    },
    {
        titulo: "💰 PASSO 2: Planejar Custos (Orçamento)",
        conteudo: (
            <div className="space-y-4">
                <div>
                    <h4 className="font-semibold text-sm mb-2">O que é?</h4>
                    <p className="text-sm text-muted-foreground">Você define quanto vai gastar durante toda a safra para depois comparar com o que realmente gastou.</p>
                </div>
                <div>
                    <h4 className="font-semibold text-sm mb-2">Onde encontrar?</h4>
                    <p className="text-sm text-muted-foreground">Menu: Agricultura → ① Planejamento → Orçamento de Safra</p>
                </div>
                <div>
                    <h4 className="font-semibold text-sm mb-2">Categorias de custo:</h4>
                    <ul className="space-y-2 text-sm">
                        <li className="flex gap-2"><span className="font-semibold min-w-32">SEMENTE:</span> <span className="text-muted-foreground">Sementes ou mudas</span></li>
                        <li className="flex gap-2"><span className="font-semibold min-w-32">FERTILIZANTE:</span> <span className="text-muted-foreground">Adubo</span></li>
                        <li className="flex gap-2"><span className="font-semibold min-w-32">DEFENSIVO:</span> <span className="text-muted-foreground">Veneno/fungicida</span></li>
                        <li className="flex gap-2"><span className="font-semibold min-w-32">COMBUSTIVEL:</span> <span className="text-muted-foreground">Diesel/gasolina</span></li>
                        <li className="flex gap-2"><span className="font-semibold min-w-32">MAO_DE_OBRA:</span> <span className="text-muted-foreground">Salários</span></li>
                        <li className="flex gap-2"><span className="font-semibold min-w-32">SERVICO:</span> <span className="text-muted-foreground">Trabalhos de terceiros</span></li>
                        <li className="flex gap-2"><span className="font-semibold min-w-32">OUTROS:</span> <span className="text-muted-foreground">Imprevistos</span></li>
                    </ul>
                </div>
                <Alert variant="info">
                    <AlertDescription>
                        <strong>💡 Dica:</strong> Se sua safra tem múltiplos cultivos (Café + Milho), você pode vincular cada item de custo a um cultivo específico. Isso permite visualizar o orçamento separado por cultura.
                    </AlertDescription>
                </Alert>
            </div>
        ),
    },
    {
        titulo: "🚜 PASSO 3: Registrar Operações de Campo",
        conteudo: (
            <div className="space-y-4">
                <div>
                    <h4 className="font-semibold text-sm mb-2">O que é?</h4>
                    <p className="text-sm text-muted-foreground">Cada operação de campo, como plantar, adubar, pulverizar e colher, fica registrada aqui com seus custos.</p>
                </div>
                <div>
                    <h4 className="font-semibold text-sm mb-2">Tipos de Operações:</h4>
                    <ul className="space-y-2 text-sm">
                        <li className="flex gap-2"><span className="font-semibold min-w-20">PLANTIO:</span> <span className="text-muted-foreground">Primeira operação, após preparo do solo</span></li>
                        <li className="flex gap-2"><span className="font-semibold min-w-20">ADUBACAO:</span> <span className="text-muted-foreground">Normalmente 3-4 vezes ao ano</span></li>
                        <li className="flex gap-2"><span className="font-semibold min-w-20">PULVERIZACAO:</span> <span className="text-muted-foreground">Contra pragas/doenças conforme necessidade</span></li>
                        <li className="flex gap-2"><span className="font-semibold min-w-20">COLHEITA:</span> <span className="text-muted-foreground">A operação mais importante</span></li>
                        <li className="flex gap-2"><span className="font-semibold min-w-20">CAPINA:</span> <span className="text-muted-foreground">Controle de ervas daninhas</span></li>
                        <li className="flex gap-2"><span className="font-semibold min-w-20">PODA:</span> <span className="text-muted-foreground">Poda de manutenção</span></li>
                    </ul>
                </div>
                <Alert variant="info">
                    <AlertDescription>
                        <strong>💡 Dica:</strong> Sempre vincule operações ao cultivo específico para que os custos sejam atribuídos corretamente.
                    </AlertDescription>
                </Alert>
            </div>
        ),
    },
    {
        titulo: "🔬 PASSO 4: Monitorar a Saúde (Fenologia, Pragas, NDVI)",
        conteudo: (
            <div className="space-y-4">
                <div>
                    <h4 className="font-semibold text-sm mb-2">Fenologia - Estágios de Crescimento</h4>
                    <ul className="space-y-1 text-sm text-muted-foreground">
                        <li><strong>Brotação:</strong> Novas folhas saindo (jan-fev)</li>
                        <li><strong>Floração:</strong> Flores brancas aparecendo (set-out)</li>
                        <li><strong>Granação:</strong> Frutos pequenos formando (nov-dez)</li>
                        <li><strong>Maturação:</strong> Frutos ficando vermelhos/roxos (mai-jun)</li>
                    </ul>
                </div>
                <div>
                    <h4 className="font-semibold text-sm mb-2">Monitoramento de Pragas</h4>
                    <p className="text-sm text-muted-foreground mb-2">Registre cada vez que encontrar problema:</p>
                    <ul className="space-y-1 text-sm text-muted-foreground">
                        <li>🦗 <strong>Broca:</strong> Inseto que entra no fruto</li>
                        <li>🍂 <strong>Ferrugem:</strong> Manchas nas folhas</li>
                        <li>🕷️ <strong>Ácaro:</strong> Danifica folhas</li>
                        <li>🌪️ <strong>Oídio:</strong> Fungo branco nas folhas</li>
                    </ul>
                </div>
                <div>
                    <h4 className="font-semibold text-sm mb-2">NDVI - Imagem de Satélite</h4>
                    <p className="text-sm text-muted-foreground">Foto de satélite que mostra a saúde da plantação (verde escuro = saudável, amarelo = com problemas). Útil para identificar trechos com problemas de nutrição ou água.</p>
                </div>
            </div>
        ),
    },
    {
        titulo: "📝 PASSO 5: Registrar Colheita (Romaneios)",
        conteudo: (
            <div className="space-y-4">
                <div>
                    <h4 className="font-semibold text-sm mb-2">O que é?</h4>
                    <p className="text-sm text-muted-foreground">Enquanto colhe, você registra cada lote (romaneio rastreia aquele lote desde a colheita até o armazenamento).</p>
                </div>
                <div>
                    <h4 className="font-semibold text-sm mb-2">Onde encontrar?</h4>
                    <p className="text-sm text-muted-foreground">Menu: Agricultura → ③ Colheita → Romaneios (Colheita)</p>
                </div>
                <div>
                    <h4 className="font-semibold text-sm mb-2">O que registrar por romaneio?</h4>
                    <ul className="space-y-1 text-sm text-muted-foreground">
                        <li>Data da colheita</li>
                        <li>Talhão colhido</li>
                        <li>Tipo de cereja (vermelha, madura, etc)</li>
                        <li>Quantidade (sacas ou kg)</li>
                        <li>Local de armazenamento</li>
                        <li>Qualidade observada</li>
                        <li>Observações adicionais</li>
                    </ul>
                </div>
                <Alert variant="info">
                    <AlertDescription>
                        <strong>💡 Por que importa:</strong> Rastreia quem colheu, quando, quanto, e marca ponto de origem para café processado depois. Importante se vender para diferentes compradores.
                    </AlertDescription>
                </Alert>
            </div>
        ),
    },
    {
        titulo: "☕ PASSO 6: Processar o Café (Beneficiamento)",
        conteudo: (
            <div className="space-y-4">
                <div>
                    <h4 className="font-semibold text-sm mb-2">O que é Beneficiamento?</h4>
                    <p className="text-sm text-muted-foreground">Transformar café fresco em café pronto para vender. Inclui secagem, descascamento, classificação e embalagem.</p>
                </div>
                <div>
                    <h4 className="font-semibold text-sm mb-2">Etapas:</h4>
                    <ol className="space-y-2 text-sm">
                        <li><span className="font-semibold">1. Secagem:</span> <span className="text-muted-foreground">Reduzir água de ~60% para ~11%</span></li>
                        <li><span className="font-semibold">2. Descascamento:</span> <span className="text-muted-foreground">Tirar casca/polpa</span></li>
                        <li><span className="font-semibold">3. Classificação:</span> <span className="text-muted-foreground">Separar por tamanho/qualidade</span></li>
                        <li><span className="font-semibold">4. Embalagem:</span> <span className="text-muted-foreground">Colocar em sacos de 60 kg</span></li>
                    </ol>
                </div>
                <Alert variant="warning">
                    <AlertDescription>
                        <strong>📌 Importante:</strong> Toda etapa é registrada no sistema. A perda de peso é normal (café seca e perde água).
                    </AlertDescription>
                </Alert>
            </div>
        ),
    },
];

// ---------------------------------------------------------------------------
// FAQ
// ---------------------------------------------------------------------------

const faqs = [
    {
        pergunta: "Qual a diferença entre Safra, Talhão e Cultivo?",
        resposta: "Safra = tempo (período agrícola). Talhão = espaço (área física). Cultivo = ocupação real, a interseção entre os dois. Todo custo, operação e produção pertence ao cultivo.",
    },
    {
        pergunta: "Posso usar o mesmo talhão em duas safras diferentes?",
        resposta: "Sim. Um talhão pode ser usado por múltiplas safras ao longo do tempo. Isso é a base da rotação de culturas. Basta criar cultivos com períodos diferentes no mesmo talhão.",
    },
    {
        pergunta: "O que acontece se eu tentar ocupar mais área do que o talhão possui?",
        resposta: "O sistema bloqueia e mostra mensagem de erro informando a capacidade do talhão. A solução é reduzir a área ou marcar os cultivos como consorciados (se realmente compartilham espaço).",
    },
    {
        pergunta: "Quando devo marcar um cultivo como Consorciado?",
        resposta: "Quando dois cultivos ocupam fisicamente o mesmo espaço ao mesmo tempo — por exemplo, café com milho safrinha no mesmo talhão. Ambos devem ser marcados como consorciados.",
    },
    {
        pergunta: "Como registro um período de pousio?",
        resposta: "Crie um cultivo com a cultura 'POUSIO' ou 'COBERTURA VEGETAL', defina o período de ocupação (data início e fim) e o talhão. Isso mantém o histórico completo do talhão.",
    },
    {
        pergunta: "O campo 'Início/Fim da ocupação' é obrigatório?",
        resposta: "Não. Se deixado vazio, o sistema considera o cultivo como 'sempre ativo' durante a safra. Para suporte a rotação e pousio com validação temporal, preencher as datas é recomendado.",
    },
    {
        pergunta: "Como ver o custo real por cultura dentro de uma safra?",
        resposta: "Sempre vincule operações, despesas e romaneios ao cultivo específico. Com esses vínculos preenchidos, o sistema calcula custo total, produção e resultado financeiro por cultivo independentemente.",
    },
    {
        pergunta: "Quanto tempo uma safra de café leva?",
        resposta: "De 2 a 3 anos da primeira safra viável após plantio. Depois, todo ano você colhe.",
    },
];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AjudaPage() {
    const [busca, setBusca] = useState("");
    const [categoriaAtiva, setCategoriaAtiva] = useState("Todas");

    const resultados = useMemo(() => {
        return dicionario.filter(item => {
            const matchCategoria = categoriaAtiva === "Todas" || item.categoria === categoriaAtiva;
            const matchBusca = busca.length === 0 || (
                item.termo.toLowerCase().includes(busca.toLowerCase()) ||
                item.definicao.toLowerCase().includes(busca.toLowerCase()) ||
                item.categoria.toLowerCase().includes(busca.toLowerCase())
            );
            return matchCategoria && matchBusca;
        });
    }, [busca, categoriaAtiva]);

    const faqsFiltrados = useMemo(() => {
        if (!busca) return faqs;
        return faqs.filter(f =>
            f.pergunta.toLowerCase().includes(busca.toLowerCase()) ||
            f.resposta.toLowerCase().includes(busca.toLowerCase())
        );
    }, [busca]);

    const guiasFiltrados = useMemo(() => {
        if (!busca) return guias;
        return guias.filter(g => g.titulo.toLowerCase().includes(busca.toLowerCase()));
    }, [busca]);

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Central de Ajuda"
                description="Dicionário de dados, guias passo-a-passo e perguntas frequentes do módulo Agrícola"
                breadcrumbs={[
                    { label: "Agrícola", href: "/agricola" },
                    { label: "Central de Ajuda" },
                ]}
            />

            {/* Barra de pesquisa */}
            <div className="relative max-w-xl">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
                <Input
                    placeholder="Pesquisar termos, conceitos, guias ou perguntas..."
                    value={busca}
                    onChange={e => setBusca(e.target.value)}
                    className="pl-9 h-8 text-xs rounded-sm border-2"
                    autoFocus
                />
            </div>

            {/* Regra de Ouro */}
            {!busca && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {[
                        { icon: MapPin, label: "Talhão", desc: "= Espaço físico", color: "text-emerald-600 bg-emerald-50" },
                        { icon: Calendar, label: "Safra", desc: "= Período de tempo", color: "text-blue-600 bg-blue-50" },
                        { icon: Sprout, label: "Cultivo", desc: "= Ocupação real (espaço + tempo)", color: "text-amber-600 bg-amber-50" },
                    ].map(c => (
                        <Card key={c.label} className="rounded-sm border bg-card shadow-sm transition-all hover:border-primary/20">
                            <CardContent className="flex items-center gap-3 py-4">
                                <div className={`size-10 rounded-sm flex items-center justify-center shrink-0 ${c.color}`}>
                                    <c.icon className="size-5" />
                                </div>
                                <div>
                                    <p className="font-bold text-sm">{c.label}</p>
                                    <p className="text-xs text-muted-foreground">{c.desc}</p>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            <Tabs defaultValue="dicionario">
                <TabsList className="bg-transparent p-0 gap-4 h-auto border-b rounded-none w-full justify-start">
                    <TabsTrigger value="dicionario" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent shadow-none px-1 pb-2">
                        <Database className="size-3.5 mr-2" /> Dicionário de Dados
                    </TabsTrigger>
                    <TabsTrigger value="guias" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent shadow-none px-1 pb-2">
                        <BookOpen className="size-3.5 mr-2" /> Guia Completo
                    </TabsTrigger>
                    <TabsTrigger value="faq" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent shadow-none px-1 pb-2">
                        <HelpCircle className="size-3.5 mr-2" /> Perguntas Frequentes
                    </TabsTrigger>
                </TabsList>

                {/* ── Dicionário ── */}
                <TabsContent value="dicionario" className="mt-4 space-y-4">
                    {/* Filtros de categoria */}
                    <div className="flex flex-wrap gap-2">
                        {categorias.map(cat => (
                            <Button
                                key={cat}
                                size="sm"
                                variant={categoriaAtiva === cat ? "default" : "outline"}
                                onClick={() => setCategoriaAtiva(cat)}
                                className="rounded-sm text-[10px] h-7 px-3 font-bold uppercase tracking-wider"
                            >
                                {cat}
                            </Button>
                        ))}
                    </div>

                    {resultados.length === 0 ? (
                        <p className="text-sm text-muted-foreground py-8 text-center">Nenhum termo encontrado para &quot;{busca}&quot;.</p>
                    ) : (
                        <div className="grid gap-3">
                            {resultados.map(item => (
                                <Card key={item.termo} className="rounded-sm border bg-card shadow-sm transition-all hover:border-primary/30">
                                    <CardHeader className="pb-2 pt-4 px-5">
                                        <div className="flex items-center justify-between gap-2">
                                            <CardTitle className="text-base font-bold text-primary">{item.termo}</CardTitle>
                                            <Badge variant="outline" className="text-[10px] rounded-sm uppercase tracking-wider font-bold shrink-0">{item.categoria}</Badge>
                                        </div>
                                    </CardHeader>
                                    <CardContent className="px-5 pb-4 space-y-3">
                                        <p className="text-sm text-muted-foreground leading-relaxed italic border-l-2 border-primary/20 pl-4">{item.definicao}</p>


                                        {item.exemplo && (
                                            <div className="rounded bg-muted/50 px-3 py-2">
                                                <p className="text-xs font-medium text-muted-foreground mb-0.5">Exemplo</p>
                                                <p className="text-xs">{item.exemplo}</p>
                                            </div>
                                        )}

                                        {item.regras?.length > 0 && (
                                            <ul className="space-y-1">
                                                {item.regras.map((r, i) => (
                                                    <li key={i} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                                                        <span className="mt-0.5 size-1.5 rounded-full bg-primary/60 shrink-0" />
                                                        {r}
                                                    </li>
                                                ))}
                                            </ul>
                                        )}
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    )}
                </TabsContent>

                {/* ── Guias ── */}
                <TabsContent value="guias" className="mt-4">
                    {guiasFiltrados.length === 0 ? (
                        <p className="text-sm text-muted-foreground py-8 text-center">Nenhum guia encontrado para &quot;{busca}&quot;.</p>
                    ) : (
                        <Accordion type="single" collapsible className="space-y-2">
                            {guiasFiltrados.map((guia, i) => (
                                <AccordionItem
                                    key={i}
                                    value={`guia-${i}`}
                                    className="border rounded-sm px-4 shadow-sm bg-card mb-3 overflow-hidden data-[state=open]:border-primary/30"
                                >
                                    <AccordionTrigger className="text-sm font-bold text-left hover:no-underline py-4 transition-all">
                                        {guia.titulo}
                                    </AccordionTrigger>
                                    <AccordionContent className="text-sm pb-4 border-t pt-4">
                                        {guia.conteudo}
                                    </AccordionContent>
                                </AccordionItem>
                            ))}
                        </Accordion>
                    )}
                </TabsContent>

                {/* ── FAQ ── */}
                <TabsContent value="faq" className="mt-4">
                    {faqsFiltrados.length === 0 ? (
                        <p className="text-sm text-muted-foreground py-8 text-center">Nenhuma pergunta encontrada para &quot;{busca}&quot;.</p>
                    ) : (
                        <Accordion type="single" collapsible className="space-y-2">
                            {faqsFiltrados.map((faq, i) => (
                                <AccordionItem
                                    key={i}
                                    value={`faq-${i}`}
                                    className="border rounded-sm px-4 shadow-sm bg-card mb-2 data-[state=open]:border-primary/20"
                                >
                                    <AccordionTrigger className="text-sm font-bold text-left hover:no-underline py-4">
                                        {faq.pergunta}
                                    </AccordionTrigger>
                                    <AccordionContent className="text-sm text-muted-foreground pb-4 leading-relaxed border-t pt-2 mt-2">
                                        {faq.resposta}
                                    </AccordionContent>
                                </AccordionItem>
                            ))}
                        </Accordion>
                    )}
                </TabsContent>
            </Tabs>
        </div>
    );
}
