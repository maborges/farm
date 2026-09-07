"use client";

import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/stores/app-store";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { CheckCircle2, List, RotateCcw, Search, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const UFS = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"];

type CarImportForm = {
    fazenda_nome: string; codigo_car: string; uf: string; municipio: string;
    area_total_ha: string; area_app_ha: string; area_rl_ha: string;
    area_vegetacao_nativa_ha: string; data_inscricao: string; status: string;
};
type CarImportPayload = Omit<CarImportForm, "area_total_ha" | "area_app_ha" | "area_rl_ha" | "area_vegetacao_nativa_ha" | "municipio" | "data_inscricao"> & {
    unidade_produtiva_id: string;
    imovel_rural_id: string;
    area_total_ha?: number; area_app_ha?: number; area_rl_ha?: number; area_vegetacao_nativa_ha?: number;
    municipio?: string; data_inscricao?: string;
};
type CarAreaKey = "area_total_ha" | "area_app_ha" | "area_rl_ha" | "area_vegetacao_nativa_ha";
type ContextoFundiario = {
    imovel_rural_id: string;
    nome: string;
    car_numero?: string | null;
    ccir_numero?: string | null;
    nirf?: string | null;
    numero_matricula?: string | null;
    sigef_codigo?: string | null;
};
const CONTEXTO_FUNDIARIO_VAZIO: ContextoFundiario[] = [];
const CAR_AREA_FIELDS: Array<{ key: CarAreaKey; label: string }> = [
    { key: "area_total_ha", label: "Área Total (ha)" },
    { key: "area_app_ha", label: "Área de APP (ha)" },
    { key: "area_rl_ha", label: "Reserva Legal (ha)" },
    { key: "area_vegetacao_nativa_ha", label: "Vegetação Nativa (ha)" },
];

export default function ImportarCarPage() {
    const activeFazendaId = useAppStore((state) => state.activeFazendaId);
    const unidadeSelecionada = useAppStore((state) => state.unidadesProdutivasAutorizadas.find((item) => item.id === state.activeFazendaId));
    const qc = useQueryClient();
    const [step, setStep] = useState<"form" | "success">("form");
    const [imovelSelecionadoId, setImovelSelecionadoId] = useState("");
    const [form, setForm] = useState({
        fazenda_nome: "", codigo_car: "", uf: "", municipio: "",
        area_total_ha: "", area_app_ha: "", area_rl_ha: "", area_vegetacao_nativa_ha: "",
        data_inscricao: "", status: "PENDENTE",
    });

    const { data: contextoFundiarioData, isLoading: carregandoContexto } = useQuery<ContextoFundiario[]>({
        queryKey: ["ambiental", "contexto-fundiario", activeFazendaId],
        queryFn: () => apiFetch(`/ambiental/unidades/${activeFazendaId}/contexto-fundiario`),
        enabled: !!activeFazendaId,
    });
    const contextoFundiario = contextoFundiarioData ?? CONTEXTO_FUNDIARIO_VAZIO;

    const imovelIdAtual = imovelSelecionadoId || contextoFundiario[0]?.imovel_rural_id || "";
    const imovelSelecionado = contextoFundiario.find((item) => item.imovel_rural_id === imovelIdAtual) ?? contextoFundiario[0];

    useEffect(() => {
        if (!activeFazendaId) return;
        const imovel = contextoFundiario[0];
        // Sincroniza o formulário com a unidade e o imóvel carregados do cadastro.
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setForm((current) => ({
            ...current,
            fazenda_nome: unidadeSelecionada?.nome ?? current.fazenda_nome,
            uf: unidadeSelecionada?.uf ?? current.uf,
            municipio: unidadeSelecionada?.municipio ?? current.municipio,
            codigo_car: imovel?.car_numero ?? "",
            area_total_ha: unidadeSelecionada?.area_total_ha != null ? String(unidadeSelecionada.area_total_ha) : "",
            area_app_ha: unidadeSelecionada?.area_app_ha != null ? String(unidadeSelecionada.area_app_ha) : "",
            area_rl_ha: unidadeSelecionada?.area_rl_ha != null ? String(unidadeSelecionada.area_rl_ha) : "",
        }));
    }, [activeFazendaId, contextoFundiario, unidadeSelecionada]);

    const importarMut = useMutation({
        mutationFn: (d: CarImportPayload) => apiFetch("/ambiental/car", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["ambiental"] });
            setStep("success");
            toast.success("CAR importado com sucesso.");
        },
        onError: (e: Error) => toast.error(e.message || "Erro ao importar CAR."),
    });

    function importar() {
        if (!activeFazendaId) {
            toast.error("Selecione uma fazenda antes de cadastrar o CAR."); return;
        }
        if (!imovelSelecionado?.imovel_rural_id) {
            toast.error("Selecione ou cadastre um imóvel rural antes de registrar o CAR."); return;
        }
        if (!form.fazenda_nome || !form.codigo_car || !form.uf) {
            toast.error("Nome, código CAR e UF são obrigatórios."); return;
        }
        const p: CarImportPayload = {
            unidade_produtiva_id: activeFazendaId,
            imovel_rural_id: imovelSelecionado.imovel_rural_id,
            fazenda_nome: form.fazenda_nome, codigo_car: form.codigo_car, uf: form.uf,
            status: form.status,
            ...(form.municipio ? { municipio: form.municipio } : {}),
            ...(form.data_inscricao ? { data_inscricao: form.data_inscricao } : {}),
            ...(form.area_total_ha ? { area_total_ha: parseFloat(form.area_total_ha) } : {}),
            ...(form.area_app_ha ? { area_app_ha: parseFloat(form.area_app_ha) } : {}),
            ...(form.area_rl_ha ? { area_rl_ha: parseFloat(form.area_rl_ha) } : {}),
            ...(form.area_vegetacao_nativa_ha ? { area_vegetacao_nativa_ha: parseFloat(form.area_vegetacao_nativa_ha) } : {}),
        };
        importarMut.mutate(p);
    }

    if (step === "success") {
        return (
            <div className="w-full p-6 flex flex-col gap-6">
                <PageHeader
                    title="Importar CAR"
                    description="Importação do Cadastro Ambiental Rural."
                    breadcrumbs={[
                        { label: "Dashboard", href: "/dashboard" },
                        { label: "Ambiental", href: "/dashboard/ambiental" },
                        { label: "CAR", href: "/dashboard/ambiental/car/lista" },
                        { label: "Importar" },
                    ]}
                    icon={<UploadCloud />}
                />
                <Card className="w-full max-w-md">
                    <CardContent className="flex flex-col items-center gap-4 px-6 py-8 text-center">
                        <CheckCircle2 className="text-green-500" />
                        <div className="flex flex-col gap-1">
                            <h3 className="text-lg font-semibold">CAR registrado com sucesso!</h3>
                            <p className="text-sm text-muted-foreground">O registro foi adicionado à lista de CARs.</p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            <Button variant="outline" onClick={() => {
                                setStep("form");
                                setImovelSelecionadoId("");
                                setForm({
                                    fazenda_nome: "",
                                    codigo_car: "",
                                    uf: "",
                                    municipio: "",
                                    area_total_ha: "",
                                    area_app_ha: "",
                                    area_rl_ha: "",
                                    area_vegetacao_nativa_ha: "",
                                    data_inscricao: "",
                                    status: "PENDENTE",
                                });
                            }}>
                                <RotateCcw data-icon="inline-start" />
                                Importar outro
                            </Button>
                            <Button asChild>
                                <Link href="/dashboard/ambiental/car/lista">
                                    <List data-icon="inline-start" />
                                    Ver lista de CARs
                                </Link>
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="w-full p-6 flex flex-col gap-6">
            <PageHeader
                title="Importar CAR"
                description="Registre manualmente os dados do Cadastro Ambiental Rural."
                breadcrumbs={[
                    { label: "Dashboard", href: "/dashboard" },
                    { label: "Ambiental", href: "/dashboard/ambiental" },
                    { label: "CAR", href: "/dashboard/ambiental/car/lista" },
                    { label: "Importar" },
                ]}
                icon={<UploadCloud />}
            />

            <div className="grid gap-6 lg:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base"><Search /> Dados do CAR</CardTitle>
                        <CardDescription>Os dados da unidade e do imóvel rural são carregados do cadastro existente. Confirme os dados conforme o recibo do SICAR/SNA.</CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-4">
                        {carregandoContexto && (
                            <p className="rounded-sm border border-blue-500/20 bg-blue-500/10 px-3 py-2 text-sm text-blue-800 dark:text-blue-200">
                                Carregando os imóveis vinculados à unidade produtiva...
                            </p>
                        )}
                        {contextoFundiario.length > 1 && (
                            <div className="flex flex-col gap-2">
                                <Label>Imóvel rural de referência</Label>
                                <Select value={imovelIdAtual} onValueChange={(value) => {
                                    setImovelSelecionadoId(value);
                                    const imovel = contextoFundiario.find((item) => item.imovel_rural_id === value);
                                    setForm((current) => ({ ...current, codigo_car: imovel?.car_numero ?? "" }));
                                }}>
                                    <SelectTrigger><SelectValue placeholder="Selecione o imóvel rural" /></SelectTrigger>
                                    <SelectContent>
                                        {contextoFundiario.map((imovel) => (
                                            <SelectItem key={imovel.imovel_rural_id} value={imovel.imovel_rural_id}>{imovel.nome}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}
                        {imovelSelecionado && (
                            <div className="rounded-sm border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                                <p className="font-medium text-foreground">Referências fundiárias cadastradas: {imovelSelecionado.nome}</p>
                                <p className="mt-1">
                                    CAR: {imovelSelecionado.car_numero ?? "não informado"} • CCIR: {imovelSelecionado.ccir_numero ?? "não informado"} • NIRF: {imovelSelecionado.nirf ?? "não informado"} • Matrícula: {imovelSelecionado.numero_matricula ?? "não informado"} • SIGEF: {imovelSelecionado.sigef_codigo ?? "não informado"}
                                </p>
                            </div>
                        )}
                        <div className="flex flex-col gap-2">
                            <Label>Nome da Fazenda <span className="text-destructive">*</span></Label>
                            <Input placeholder="ex: Fazenda Santa Maria" value={form.fazenda_nome} readOnly={!!unidadeSelecionada?.nome} onChange={e => setForm(f => ({ ...f, fazenda_nome: e.target.value }))} />
                        </div>
                        <div className="flex flex-col gap-2">
                            <Label>Código CAR <span className="text-destructive">*</span></Label>
                            <Input placeholder="ex: SP-3500000-XXXXXXXXXXXXXXXXXXXX" value={form.codigo_car} readOnly={!!imovelSelecionado?.car_numero} onChange={e => setForm(f => ({ ...f, codigo_car: e.target.value }))} className="font-mono text-sm" />
                        </div>
                        <div className="grid gap-3 sm:grid-cols-2">
                            <div className="flex flex-col gap-2">
                                <Label>UF <span className="text-destructive">*</span></Label>
                                <Select value={form.uf} disabled={!!unidadeSelecionada?.uf} onValueChange={v => setForm(f => ({ ...f, uf: v }))}>
                                    <SelectTrigger><SelectValue placeholder="UF" /></SelectTrigger>
                                    <SelectContent>{UFS.map(u => <SelectItem key={u} value={u}>{u}</SelectItem>)}</SelectContent>
                                </Select>
                            </div>
                            <div className="flex flex-col gap-2">
                                <Label>Município</Label>
                                <Input placeholder="Cidade" value={form.municipio} readOnly={!!unidadeSelecionada?.municipio} onChange={e => setForm(f => ({ ...f, municipio: e.target.value }))} />
                            </div>
                        </div>
                        <div className="grid gap-3 sm:grid-cols-2">
                            <div className="flex flex-col gap-2">
                                <Label>Status</Label>
                                <Select value={form.status} onValueChange={v => setForm(f => ({ ...f, status: v }))}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="ATIVO">Ativo</SelectItem>
                                        <SelectItem value="PENDENTE">Pendente</SelectItem>
                                        <SelectItem value="EM_ANALISE">Em Análise</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="flex flex-col gap-2">
                                <Label>Data de Inscrição</Label>
                                <Input type="date" value={form.data_inscricao} onChange={e => setForm(f => ({ ...f, data_inscricao: e.target.value }))} />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base"><UploadCloud /> Dados de Área</CardTitle>
                        <CardDescription>Áreas em hectares conforme o cadastro da unidade produtiva e, quando disponível, a fonte ambiental.</CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-4">
                        {CAR_AREA_FIELDS.map(({ key, label }) => (
                            <div key={key} className="flex flex-col gap-2">
                                <Label>{label}</Label>
                                <Input
                                    type="number"
                                    placeholder="0.00"
                                    value={form[key]}
                                    readOnly={
                                        (key === "area_total_ha" && unidadeSelecionada?.area_total_ha != null)
                                        || (key === "area_app_ha" && unidadeSelecionada?.area_app_ha != null)
                                        || (key === "area_rl_ha" && unidadeSelecionada?.area_rl_ha != null)
                                    }
                                    onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                                />
                            </div>
                        ))}

                        <Button className="w-full" onClick={importar} disabled={importarMut.isPending}>
                            <UploadCloud data-icon="inline-start" />
                                    {importarMut.isPending ? "Registrando..." : "Registrar CAR"}
                        </Button>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
