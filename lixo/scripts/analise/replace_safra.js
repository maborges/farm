const fs = require('fs');
const file = 'apps/web/src/app/(dashboard)/agricola/safras/[id]/page.tsx';
let content = fs.readFileSync(file, 'utf8');

content = content.replace(
    /import \{\s*ClipboardList,\s*Bug,\s*Leaf,\s*CheckSquare,\s*FlaskConical,\s*Wheat,\s*Coffee,\s*Calculator,\s*Satellite,\s*BookOpen,\s*Sprout,\s*Pencil,\s*ChevronDown,\s*History,\s*ListTodo,\s*BarChart2,\s*ArrowRight,\s*Layers,\s*Gauge,\s*Package,\s*DollarSign,\s*\}/s,
    `import {
    ClipboardList, Bug, Leaf, CheckSquare, FlaskConical, Wheat, Coffee,
    Calculator, Satellite, BookOpen, Sprout, Pencil,
    ChevronDown, History, ListTodo, BarChart2, ArrowRight, Layers, Gauge,
    Package, DollarSign, AlertTriangle, Rocket,
}`
);

const returnStr = `    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <PageHeader
                title={titulo}
                icon={<ClipboardList className="text-primary" size={22} />}
                description={
                    initialCultivos.length === 1
                        ? (initialCultivos[0].cultivar_nome ?? "")
                        : initialCultivos.length > 1
                            ? \`\${initialCultivos.length} cultivos\`
                            : "Nenhum cultivo cadastrado"
                }
                breadcrumbs={[
                    { label: "Agrícola", href: "/agricola" },
                    { label: "Safras", href: "/agricola/safras" },
                    { label: safraLabel },
                ]}
                actions={
                    <div className="flex items-center gap-2 flex-wrap justify-end">
                        <span className={cn("text-xs font-medium px-2.5 py-1 rounded-full border", faseColorClass)}>
                            {FASE_LABEL[safra.status] ?? safra.status}
                        </span>
                        {safra.status === "PLANEJADA" && (
                            <Button size="sm" variant="outline" onClick={() => setIsEditOpen(true)} disabled={isLoadingCultivos}>
                                <Pencil className="size-3.5 mr-1.5" /> Editar
                            </Button>
                        )}
                    </div>
                }
            />

            {/* Resumo - KPIs Compactos */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <Card className="rounded-sm shadow-sm bg-card p-3.5 flex items-center justify-between gap-3">
                    <div className="min-w-0">
                        <p className="text-xs font-medium text-muted-foreground">Cultivos</p>
                        <p className="mt-1 text-xl font-bold leading-tight">{initialCultivos.length}</p>
                    </div>
                    <div className="size-9 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                        <Sprout className="size-4.5 text-primary" />
                    </div>
                </Card>

                <Card className="rounded-sm shadow-sm bg-card p-3.5 flex items-center justify-between gap-3">
                    <div className="min-w-0">
                        <p className="text-xs font-medium text-muted-foreground">Área total</p>
                        <p className="mt-1 text-xl font-bold leading-tight">
                            {areaTotal > 0 ? \`\${areaTotal.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ha\` : "—"}
                        </p>
                    </div>
                    <div className="size-9 rounded-sm bg-emerald-500/10 flex items-center justify-center shrink-0">
                        <Layers className="size-4.5 text-emerald-600" />
                    </div>
                </Card>

                <Card className="rounded-sm shadow-sm bg-card p-3.5 flex items-center justify-between gap-3">
                    <div className="min-w-0">
                        <p className="text-xs font-medium text-muted-foreground">Fase atual</p>
                        <p className="mt-1 text-base font-bold leading-tight truncate text-amber-600">
                            {FASE_LABEL[safra.status] ?? safra.status}
                        </p>
                    </div>
                    <div className="size-9 rounded-sm bg-amber-500/10 flex items-center justify-center shrink-0">
                        <ClipboardList className="size-4.5 text-amber-600" />
                    </div>
                </Card>

                <Card className="rounded-sm shadow-sm bg-card p-3.5 flex items-center justify-between gap-3">
                    <div className="min-w-0">
                        <p className="text-xs font-medium text-muted-foreground">Atualização</p>
                        <p className="mt-1 text-base font-bold leading-tight truncate">
                            {fmt(safra.updated_at)}
                        </p>
                    </div>
                    <div className="size-9 rounded-sm bg-slate-500/10 flex items-center justify-center shrink-0">
                        <History className="size-4.5 text-slate-600" />
                    </div>
                </Card>
            </div>



            {/* KPI Strip — cenário BASE */}
            {cenarioBase && (
                <CenarioBaseStrip cenario={cenarioBase} safraId={id} />
            )}

            {/* Timeline */}
            <SafraTimeline
                safraId={id}
                statusAtual={safra.status}
                queryKey={queryKey}
            />

            {/* Cultivos */}
            {initialCultivos.length > 0 && (
                <div className="space-y-2">
                    <div className="flex items-center gap-2">
                        <Sprout className="size-4 text-muted-foreground" />
                        <h2 className="text-sm font-semibold">
                            {initialCultivos.length === 1 ? "Cultivo" : \`Cultivos (\${initialCultivos.length})\`}
                        </h2>
                    </div>
                    <div className={cn("grid gap-3", initialCultivos.length === 1 ? "grid-cols-1" : "sm:grid-cols-2")}>
                        {initialCultivos.map((c) => (
                            <CultivoCard
                                key={c.id}
                                cultivo={c}
                                areas={todasAreas}
                                readOnly
                                cultivoAreaCorrecaoStatus={cultivoAreaCorrecaoStatus}
                                onAnaliseSolo={(area) => setAnaliseDrawerArea({
                                    id: area.id,
                                    area_id: area.area_id,
                                    area_ha: areaRuralMap.get(area.area_id)?.area_hectares ?? areaRuralMap.get(area.area_id)?.area_hectares_manual ?? area.area_ha,
                                    area_nome: todasAreas.find(a => a.id === area.area_id)?.nome,
                                    analise_solo_id: area.analise_solo_id,
                                    analise_status: area.analise_status ?? "NAO_SELECIONADA",
                                    regiao_analise: area.regiao_analise,
                                    cultivo_id: c.id,
                                    safra_id: id,
                                    cultivar_id: c.cultivar_id ?? null,
                                    cultura: c.cultura,
                                })}
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* Checklist da fase atual */}
            {!["ENCERRADA", "CANCELADA"].includes(safra.status) && culturaAtual && (
                <Card>
                    <CardContent className="px-4 pb-4 pt-4">
                        <SafraChecklist
                            safraId={id}
                            cultura={culturaAtual}
                            fase={safra.status}
                        />
                    </CardContent>
                </Card>
            )}

            {/* Tarefas */}
            <Card>
                <CardContent className="px-4 pb-4 pt-4">
                    <SafraTarefas 
                        safraId={id} 
                        fase={safra.status} 
                        cultura={culturaAtual || ""} 
                    />
                </CardContent>
            </Card>

            {/* Fenologia */}
            {!["CANCELADA"].includes(safra.status) && culturaAtual && (
                <Card>
                    <CardHeader className="pb-2 pt-4 px-4">
                        <div className="flex items-center gap-2">
                            <Leaf className="size-4 text-muted-foreground" />
                            <CardTitle className="text-sm font-medium text-muted-foreground">Fenologia</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="px-4 pb-4 pt-1">
                        <SafraFenologia safraId={id} cultura={culturaAtual} grupos={gruposFenologia} talhoes={talhoesDaSafra} />
                    </CardContent>
                </Card>
            )}

            {/* Histórico de fases — colapsível */}
            {historico && historico.length > 0 && (
                <Collapsible open={historicoOpen} onOpenChange={setHistoricoOpen}>
                    <Card>
                        <CardHeader className="pb-3 pt-4 px-4">
                            <CollapsibleTrigger className="w-full">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <History className="size-4 text-muted-foreground" />
                                        <CardTitle className="text-sm font-medium text-muted-foreground">
                                            Histórico de Fases
                                        </CardTitle>
                                        <Badge variant="secondary" className="text-xs">{historico.length}</Badge>
                                    </div>
                                    <ChevronDown className={cn("size-4 text-muted-foreground transition-transform", historicoOpen && "rotate-180")} />
                                </div>
                            </CollapsibleTrigger>
                        </CardHeader>
                        <CollapsibleContent>
                            <CardContent className="px-4 pb-4 pt-0">
                                <ol className="relative border-l border-border ml-3 space-y-4 py-2">
                                    {historico.map((h) => (
                                        <li key={h.id} className="ml-4">
                                            <div className="absolute -left-1.5 mt-1 size-3 rounded-full bg-primary" />
                                            <div className="flex items-center gap-2 flex-wrap">
                                                {h.fase_anterior && (
                                                    <>
                                                        <Badge variant="outline" className="text-xs">{FASE_LABEL[h.fase_anterior] ?? h.fase_anterior}</Badge>
                                                        <span className="text-muted-foreground text-xs">→</span>
                                                    </>
                                                )}
                                                <Badge className="text-xs">{FASE_LABEL[h.fase_nova] ?? h.fase_nova}</Badge>
                                                <span className="text-xs text-muted-foreground ml-auto">{fmt(h.created_at)}</span>
                                            </div>
                                            {h.observacao && (
                                                <p className="text-sm text-muted-foreground mt-1">{h.observacao}</p>
                                            )}
                                        </li>
                                    ))}
                                </ol>
                            </CardContent>
                        </CollapsibleContent>
                    </Card>
                </Collapsible>
            )}

            {/* Observações */}
            {safra.observacoes && (
                <Card>
                    <CardContent className="p-4">
                        <p className="text-xs font-medium text-muted-foreground mb-1.5">Observações</p>
                        <p className="text-sm">{safra.observacoes}</p>
                    </CardContent>
                </Card>
            )}

            {isEditOpen && (
                <SafraCreateDialog
                    open={isEditOpen}
                    onOpenChange={setIsEditOpen}
                    safraId={id}
                    initialSafra={{ ano_safra: safra.ano_safra }}
                    initialCultivos={initialCultivos}
                />
            )}

            {analiseDrawerArea && (
                <CultivoAnaliseSoloDrawer
                    area={analiseDrawerArea}
                    open={!!analiseDrawerArea}
                    onClose={() => setAnaliseDrawerArea(null)}
                    onSuccess={() => {
                        setAnaliseDrawerArea(null);
                    }}
                />
            )}
        </div>
    );`;

const replacement = `    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <PageHeader
                title={titulo}
                icon={<ClipboardList className="text-primary" size={22} />}
                description={
                    initialCultivos.length === 1
                        ? (initialCultivos[0].cultivar_nome ?? "")
                        : initialCultivos.length > 1
                            ? \`\${initialCultivos.length} cultivos\`
                            : "Nenhum cultivo cadastrado"
                }
                breadcrumbs={[
                    { label: "Agrícola", href: "/agricola" },
                    { label: "Safras", href: "/agricola/safras" },
                    { label: safraLabel },
                ]}
                actions={
                    <div className="flex items-center gap-2 flex-wrap justify-end">
                        <span className={cn("text-xs font-medium px-2.5 py-1 rounded-full border", faseColorClass)}>
                            {FASE_LABEL[safra.status] ?? safra.status}
                        </span>
                        {safra.status === "PLANEJADA" && (
                            <Button size="sm" variant="outline" onClick={() => setIsEditOpen(true)} disabled={isLoadingCultivos}>
                                <Pencil className="size-3.5 mr-1.5" /> Editar
                            </Button>
                        )}
                    </div>
                }
            />

            <div className="grid gap-6 lg:grid-cols-3">
                <div className="lg:col-span-2 flex flex-col gap-6">
                    {/* Resumo - KPIs Compactos */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                        <Card className="rounded-sm shadow-sm bg-card p-3.5 flex items-center justify-between gap-3">
                            <div className="min-w-0">
                                <p className="text-xs font-medium text-muted-foreground">Cultivos</p>
                                <p className="mt-1 text-xl font-bold leading-tight">{initialCultivos.length}</p>
                            </div>
                            <div className="size-9 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                                <Sprout className="size-4.5 text-primary" />
                            </div>
                        </Card>

                        <Card className="rounded-sm shadow-sm bg-card p-3.5 flex items-center justify-between gap-3">
                            <div className="min-w-0">
                                <p className="text-xs font-medium text-muted-foreground">Área total</p>
                                <p className="mt-1 text-xl font-bold leading-tight">
                                    {areaTotal > 0 ? \`\${areaTotal.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ha\` : "—"}
                                </p>
                            </div>
                            <div className="size-9 rounded-sm bg-emerald-500/10 flex items-center justify-center shrink-0">
                                <Layers className="size-4.5 text-emerald-600" />
                            </div>
                        </Card>

                        <Card className="rounded-sm shadow-sm bg-card p-3.5 flex items-center justify-between gap-3">
                            <div className="min-w-0">
                                <p className="text-xs font-medium text-muted-foreground">Fase atual</p>
                                <p className="mt-1 text-base font-bold leading-tight truncate text-amber-600">
                                    {FASE_LABEL[safra.status] ?? safra.status}
                                </p>
                            </div>
                            <div className="size-9 rounded-sm bg-amber-500/10 flex items-center justify-center shrink-0">
                                <ClipboardList className="size-4.5 text-amber-600" />
                            </div>
                        </Card>

                        <Card className="rounded-sm shadow-sm bg-card p-3.5 flex items-center justify-between gap-3">
                            <div className="min-w-0">
                                <p className="text-xs font-medium text-muted-foreground">Atualização</p>
                                <p className="mt-1 text-base font-bold leading-tight truncate">
                                    {fmt(safra.updated_at)}
                                </p>
                            </div>
                            <div className="size-9 rounded-sm bg-slate-500/10 flex items-center justify-center shrink-0">
                                <History className="size-4.5 text-slate-600" />
                            </div>
                        </Card>
                    </div>

                    {/* Checklist da fase atual */}
                    {!["ENCERRADA", "CANCELADA"].includes(safra.status) && culturaAtual && (
                        <Card className="border-amber-200/60 shadow-sm">
                            <CardHeader className="pb-0 pt-4 px-4">
                                <CardTitle className="text-sm font-medium flex items-center gap-2 text-amber-700">
                                    <AlertTriangle className="size-4" />
                                    Precisa de atenção
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="px-4 pb-4 pt-4">
                                <SafraChecklist
                                    safraId={id}
                                    cultura={culturaAtual}
                                    fase={safra.status}
                                />
                            </CardContent>
                        </Card>
                    )}

                    {/* Tarefas */}
                    <Card className="shadow-sm">
                        <CardHeader className="pb-0 pt-4 px-4">
                            <CardTitle className="text-sm font-medium flex items-center gap-2 text-foreground">
                                <ListTodo className="size-4 text-muted-foreground" />
                                Próximas atividades
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="px-4 pb-4 pt-4">
                            <SafraTarefas 
                                safraId={id} 
                                fase={safra.status} 
                                cultura={culturaAtual || ""} 
                            />
                        </CardContent>
                    </Card>
                </div>

                {/* AÇÕES RÁPIDAS & ECONOMIA */}
                <div className="flex flex-col gap-6">
                    <Card className="shadow-sm bg-muted/20 border-border/60">
                        <CardHeader className="pb-3 pt-4 px-4 border-b bg-card">
                            <CardTitle className="text-sm font-semibold flex items-center gap-2">
                                <Rocket className="size-4 text-primary" />
                                Ações Rápidas
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-3 flex flex-col gap-2">
                            <Button asChild variant="outline" className="justify-start gap-3 h-10 w-full text-left bg-card hover:bg-primary/5 hover:text-primary rounded-sm shadow-sm">
                                <Link href={\`/agricola/safras/\${id}/operacoes\`}>Registrar Operação</Link>
                            </Button>
                            <Button asChild variant="outline" className="justify-start gap-3 h-10 w-full text-left bg-card hover:bg-primary/5 hover:text-primary rounded-sm shadow-sm">
                                <Link href={\`/agricola/safras/\${id}/planejamento-operacional\`}>Abrir Planejamento</Link>
                            </Button>
                            <Button asChild variant="outline" className="justify-start gap-3 h-10 w-full text-left bg-card hover:bg-primary/5 hover:text-primary rounded-sm shadow-sm">
                                <Link href={\`/agricola/safras/\${id}/orcamento\`}>Consultar Orçamento</Link>
                            </Button>
                            {hasProfessionalTier && (
                                <Button asChild variant="outline" className="justify-start gap-3 h-10 w-full text-left bg-card hover:bg-primary/5 hover:text-primary rounded-sm shadow-sm border-emerald-200 text-emerald-700 hover:bg-emerald-50">
                                    <Link href={\`/agricola/safras/\${id}/dashboard\`}>Abrir Dashboard da Safra</Link>
                                </Button>
                            )}
                        </CardContent>
                    </Card>

                    {/* KPI Strip — cenário BASE */}
                    {cenarioBase && (
                        <div className="shadow-sm rounded-sm">
                            <CenarioBaseStrip cenario={cenarioBase} safraId={id} />
                        </div>
                    )}
                </div>
            </div>

            {/* JORNADA & CONTEXTO COMPLEMENTAR */}
            <div className="mt-8 border-t pt-8 space-y-6">
                <h3 className="text-lg font-semibold tracking-tight">Andamento da Safra</h3>
                
                {/* Timeline */}
                <SafraTimeline
                    safraId={id}
                    statusAtual={safra.status}
                    queryKey={queryKey}
                />

                {/* Cultivos */}
                {initialCultivos.length > 0 && (
                    <div className="space-y-2 mt-4">
                        <div className="flex items-center gap-2">
                            <Sprout className="size-4 text-muted-foreground" />
                            <h2 className="text-sm font-semibold">
                                {initialCultivos.length === 1 ? "Cultivo" : \`Cultivos (\${initialCultivos.length})\`}
                            </h2>
                        </div>
                        <div className={cn("grid gap-3", initialCultivos.length === 1 ? "grid-cols-1" : "sm:grid-cols-2")}>
                            {initialCultivos.map((c) => (
                                <CultivoCard
                                    key={c.id}
                                    cultivo={c}
                                    areas={todasAreas}
                                    readOnly
                                    cultivoAreaCorrecaoStatus={cultivoAreaCorrecaoStatus}
                                    onAnaliseSolo={(area) => setAnaliseDrawerArea({
                                        id: area.id,
                                        area_id: area.area_id,
                                        area_ha: areaRuralMap.get(area.area_id)?.area_hectares ?? areaRuralMap.get(area.area_id)?.area_hectares_manual ?? area.area_ha,
                                        area_nome: todasAreas.find(a => a.id === area.area_id)?.nome,
                                        analise_solo_id: area.analise_solo_id,
                                        analise_status: area.analise_status ?? "NAO_SELECIONADA",
                                        regiao_analise: area.regiao_analise,
                                        cultivo_id: c.id,
                                        safra_id: id,
                                        cultivar_id: c.cultivar_id ?? null,
                                        cultura: c.cultura,
                                    })}
                                />
                            ))}
                        </div>
                    </div>
                )}

                {/* Fenologia */}
                {!["CANCELADA"].includes(safra.status) && culturaAtual && (
                    <Card>
                        <CardHeader className="pb-2 pt-4 px-4">
                            <div className="flex items-center gap-2">
                                <Leaf className="size-4 text-muted-foreground" />
                                <CardTitle className="text-sm font-medium text-muted-foreground">Fenologia</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="px-4 pb-4 pt-1">
                            <SafraFenologia safraId={id} cultura={culturaAtual} grupos={gruposFenologia} talhoes={talhoesDaSafra} />
                        </CardContent>
                    </Card>
                )}

                {/* Histórico de fases — colapsível */}
                {historico && historico.length > 0 && (
                    <Collapsible open={historicoOpen} onOpenChange={setHistoricoOpen}>
                        <Card>
                            <CardHeader className="pb-3 pt-4 px-4">
                                <CollapsibleTrigger className="w-full">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <History className="size-4 text-muted-foreground" />
                                            <CardTitle className="text-sm font-medium text-muted-foreground">
                                                Histórico de Fases
                                            </CardTitle>
                                            <Badge variant="secondary" className="text-xs">{historico.length}</Badge>
                                        </div>
                                        <ChevronDown className={cn("size-4 text-muted-foreground transition-transform", historicoOpen && "rotate-180")} />
                                    </div>
                                </CollapsibleTrigger>
                            </CardHeader>
                            <CollapsibleContent>
                                <CardContent className="px-4 pb-4 pt-0">
                                    <ol className="relative border-l border-border ml-3 space-y-4 py-2">
                                        {historico.map((h) => (
                                            <li key={h.id} className="ml-4">
                                                <div className="absolute -left-1.5 mt-1 size-3 rounded-full bg-primary" />
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    {h.fase_anterior && (
                                                        <>
                                                            <Badge variant="outline" className="text-xs">{FASE_LABEL[h.fase_anterior] ?? h.fase_anterior}</Badge>
                                                            <span className="text-muted-foreground text-xs">→</span>
                                                        </>
                                                    )}
                                                    <Badge className="text-xs">{FASE_LABEL[h.fase_nova] ?? h.fase_nova}</Badge>
                                                    <span className="text-xs text-muted-foreground ml-auto">{fmt(h.created_at)}</span>
                                                </div>
                                                {h.observacao && (
                                                    <p className="text-sm text-muted-foreground mt-1">{h.observacao}</p>
                                                )}
                                            </li>
                                        ))}
                                    </ol>
                                </CardContent>
                            </CollapsibleContent>
                        </Card>
                    </Collapsible>
                )}

                {/* Observações */}
                {safra.observacoes && (
                    <Card>
                        <CardContent className="p-4">
                            <p className="text-xs font-medium text-muted-foreground mb-1.5">Observações</p>
                            <p className="text-sm">{safra.observacoes}</p>
                        </CardContent>
                    </Card>
                )}
            </div>

            {isEditOpen && (
                <SafraCreateDialog
                    open={isEditOpen}
                    onOpenChange={setIsEditOpen}
                    safraId={id}
                    initialSafra={{ ano_safra: safra.ano_safra }}
                    initialCultivos={initialCultivos}
                />
            )}

            {analiseDrawerArea && (
                <CultivoAnaliseSoloDrawer
                    area={analiseDrawerArea}
                    open={!!analiseDrawerArea}
                    onClose={() => setAnaliseDrawerArea(null)}
                    onSuccess={() => {
                        setAnaliseDrawerArea(null);
                    }}
                />
            )}
        </div>
    );`;

if (content.indexOf(returnStr) === -1) {
    console.log("Could not find old return string in safra page.tsx exactly.");
    // try removing spaces just in case
} else {
    content = content.replace(returnStr, replacement);
    fs.writeFileSync(file, content);
    console.log("Safra replaced successfully.");
}
