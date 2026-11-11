"use client";

import { useState, useRef, useTransition } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import {
    ArrowLeft, ArrowRight, Check, ChevronRight,
    Loader2, Star, Shield, Mail, User, Building2, CreditCard,
    Camera, Tractor, Users, Smartphone, Sparkles, Calculator, Leaf, Layers, HelpCircle,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input, PasswordInput } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import {
    Avatar,
    AvatarFallback,
    AvatarImage,
} from "@/components/ui/avatar";
import { toast } from "sonner";
import {
    FATORES_VOCACAO_HEQ,
    getPacotes,
    calcularOrcamentoLocal,
    obterPacotePorNome,
    filtrarModulosAtivos,
    mesclarStatusExtensoes,
    type CatalogoModulosStatus,
} from "@/lib/constants/pacotes";

interface Plano {
    id: string;
    nome: string;
    descricao: string | null;
    preco_mensal: number;
    preco_anual: number;
    limite_usuarios_minimo?: number;
    limite_usuarios_maximo?: number | null;
    limite_hectares?: number | null;
    max_fazendas?: number;
    plan_tier: string;
    is_free: boolean;
    tem_trial: boolean;
    dias_trial: number;
    destaque: boolean;
    modulos_inclusos: string[];
    descricao_marketing: string | null;
}

const PLANOS_FALLBACK_LOCAL: Plano[] = getPacotes().map((pacote) => ({
    id: `local-${pacote.id}`,
    nome: pacote.nome,
    descricao: pacote.descricao,
    preco_mensal: pacote.precoMensal,
    preco_anual: pacote.precoAnual,
    limite_usuarios_minimo: pacote.usuariosInclusos,
    limite_usuarios_maximo: pacote.limiteUsuarios,
    limite_hectares: pacote.limiteHectares,
    max_fazendas: pacote.maxFazendas,
    plan_tier: pacote.tier,
    is_free: false,
    tem_trial: true,
    dias_trial: 14,
    destaque: Boolean(pacote.destaque),
    modulos_inclusos: pacote.modulos,
    descricao_marketing: pacote.descricaoMarketing,
}));

/* ─── Máscaras ─── */

function formatCpf(value: string): string {
    const digits = value.replace(/\D/g, "").slice(0, 11);
    if (digits.length <= 3) return digits;
    if (digits.length <= 6) return `${digits.slice(0, 3)}.${digits.slice(3)}`;
    if (digits.length <= 9) return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`;
    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`;
}

function formatPhone(value: string): string {
    const digits = value.replace(/\D/g, "").slice(0, 11);
    if (digits.length <= 2) return digits;
    if (digits.length <= 7) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
}

export function RegisterForm() {
    const router = useRouter();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [step, setStep] = useState(1);
    const [isLoading, setIsLoading] = useState(false);
    const [isUploading] = useState(false);
    const [isPending, startTransition] = useTransition();

    // Step 1 — Simulador Transparente da Assinatura (Antes do Cadastro)
    const [nomePlanoManual, setNomePlanoManual] = useState<string | null>(null);
    const [escolhaManualPlano, setEscolhaManualPlano] = useState(false);
    const [ciclo, setCiclo] = useState<"MENSAL" | "ANUAL">("ANUAL");
    const [areaEstimadaHa, setAreaEstimadaHa] = useState<string>("250");
    const [areaAmbientalHa, setAreaAmbientalHa] = useState<string>("50");
    const [vocacaoPredominante, setVocacaoPredominante] = useState<string>("GRAOS");
    const [cabecasPecuaria, setCabecasPecuaria] = useState<string>("0");
    const [usuariosContratados, setUsuariosContratados] = useState<number>(2);
    const [extensoesSelecionadas, setExtensoesSelecionadas] = useState<string[]>([]);

    const { data: catalogoModulos } = useQuery<CatalogoModulosStatus>({
        queryKey: ["billing-modules-catalog"],
        queryFn: async ({ signal }) =>
            await apiFetch("/billing/modules/catalog", { signal, suppressErrorLog: true }),
        staleTime: 300_000,
        retry: 1,
    });
    const extensoesDisponiveis = mesclarStatusExtensoes(catalogoModulos);
    const modulosInativos = catalogoModulos?.modulos_inativos ?? [];
    // Extensões inativas nunca entram no cálculo nem no cadastro, mesmo se marcadas antes da desativação
    const extensoesEfetivas = extensoesSelecionadas.filter((id) =>
        extensoesDisponiveis.some((ext) => ext.id === id && ext.ativo !== false)
    );
    const nomesExtensoesEfetivas = extensoesDisponiveis
        .filter((ext) => extensoesEfetivas.includes(ext.id))
        .map((ext) => ext.nome);

    const alternarExtensao = (extensaoId: string) => {
        const extensao = extensoesDisponiveis.find((ext) => ext.id === extensaoId);
        if (!extensao || extensao.ativo === false) {
            toast.error("Esta extensão está indisponível no momento e não pode ser selecionada.");
            return;
        }
        setExtensoesSelecionadas((atuais) =>
            atuais.includes(extensaoId)
                ? atuais.filter((id) => id !== extensaoId)
                : [...atuais, extensaoId]
        );
    };

    // Step 2 — Dados do Produtor e Credenciais de Acesso
    const [nomeProdutor, setNomeProdutor] = useState("");
    const [cnpjCpf, setCnpjCpf] = useState("");
    const [nomeCompleto, setNomeCompleto] = useState("");
    const [apelido, setApelido] = useState("");
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [cpf, setCpf] = useState("");
    const [telefone, setTelefone] = useState("");
    const [senha, setSenha] = useState("");
    const [confirmarSenha, setConfirmarSenha] = useState("");
    const [fotoUrl, setFotoUrl] = useState("");

    const { data: planosApi = [], isLoading: loadingPlanos } = useQuery<Plano[]>({
        queryKey: ["billing-plans"],
        queryFn: async ({ signal }) => {
            return await apiFetch("/billing/plans", {
                signal,
                suppressErrorLog: true,
            });
        },
        staleTime: 300_000,
        retry: 1,
    });

    // Garante sempre a exibição dos 5 perfis oficiais (Familiar, Pequeno Produtor, Médio Produtor, Grande Produtor, Grupo),
    // vinculando o UUID real do banco quando retornado pela API (inclusive se o banco ainda tiver nomes legados).
    const planos: Plano[] = PLANOS_FALLBACK_LOCAL.map((oficial) => {
        const matchApi = planosApi.find((apiPlan) => {
            const pacApi = obterPacotePorNome(apiPlan.nome);
            return (
                apiPlan.nome.trim().toLowerCase() === oficial.nome.trim().toLowerCase() ||
                (pacApi && pacApi.nome.toLowerCase() === oficial.nome.toLowerCase())
            );
        });
        if (!matchApi) {
            return { ...oficial, modulos_inclusos: filtrarModulosAtivos(oficial.modulos_inclusos, modulosInativos) };
        }
        return {
            ...oficial,
            id: matchApi.id,
            tem_trial: matchApi.tem_trial ?? oficial.tem_trial,
            dias_trial: matchApi.dias_trial ?? oficial.dias_trial,
            modulos_inclusos: filtrarModulosAtivos(
                matchApi.modulos_inclusos?.length ? matchApi.modulos_inclusos : oficial.modulos_inclusos,
                modulosInativos
            ),
        };
    });

    // Cálculo Agronômico Justo de Hectares Equivalentes (HEq)
    const areaTotalNum = Math.max(0, Number(areaEstimadaHa) || 0);
    const areaAmbientalNum = Math.min(areaTotalNum, Math.max(0, Number(areaAmbientalHa) || 0));
    const areaProdutivaLiquida = Math.max(0, areaTotalNum - areaAmbientalNum);
    const fatorVocacao = FATORES_VOCACAO_HEQ[vocacaoPredominante]?.fator ?? 1.0;

    // Teto de proteção para culturas intensivas (Café/Perenes/HF) em pequenas áreas
    const heqAgricolaBruto = areaProdutivaLiquida * fatorVocacao;
    const tetoProtecaoFamiliar =
        areaProdutivaLiquida <= 25 && fatorVocacao > 1.0 ? Math.min(heqAgricolaBruto, 100) : heqAgricolaBruto;
    const tetoProtecaoPequeno =
        areaProdutivaLiquida > 25 && areaProdutivaLiquida <= 120 && fatorVocacao > 1.0
            ? Math.min(tetoProtecaoFamiliar, 500)
            : tetoProtecaoFamiliar;

    // Integração Lavoura-Pecuária (ILP): até 2 cabeças/ha inclusas na área; excedente: 2 cab = 1 HEq
    const cabecasNum = Math.max(0, Math.floor(Number(cabecasPecuaria) || 0));
    const lotacaoInclusaCabecas = Math.floor(areaProdutivaLiquida * 2);
    const cabecasExcedentes = Math.max(0, cabecasNum - lotacaoInclusaCabecas);
    const heqPecuariaExcedente = cabecasExcedentes * 0.5;

    const hectaresEquivalentes = Math.round((tetoProtecaoPequeno + heqPecuariaExcedente) * 100) / 100;

    // Recomendação automática do pacote ideal conforme HEq e Acessos Simultâneos
    const planosOrdenados = [...planos].sort((a, b) => a.preco_mensal - b.preco_mensal);
    const planoRecomendado =
        planosOrdenados.find((p) => {
            const atendeArea =
                p.limite_hectares === null ||
                p.limite_hectares === undefined ||
                p.limite_hectares >= hectaresEquivalentes;
            const atendeUsers =
                p.limite_usuarios_maximo === null ||
                p.limite_usuarios_maximo === undefined ||
                p.limite_usuarios_maximo >= usuariosContratados;
            return atendeArea && atendeUsers;
        }) ??
        planosOrdenados[planosOrdenados.length - 1] ??
        null;

    const planoSelecionado: Plano | null =
        (escolhaManualPlano && nomePlanoManual
            ? planos.find((p) => p.nome.toLowerCase() === nomePlanoManual.toLowerCase())
            : null) ?? planoRecomendado;

    const calcularOrcamentoPlano = (plano: Plano, cicloAlvo: "MENSAL" | "ANUAL" = ciclo) => {
        const pacoteDef = obterPacotePorNome(plano.nome);
        const minUsers = plano.limite_usuarios_minimo ?? pacoteDef?.usuariosInclusos ?? 1;
        const maxUsers = plano.limite_usuarios_maximo ?? pacoteDef?.limiteUsuarios ?? 999;
        const usersEfetivos = Math.min(maxUsers, Math.max(minUsers, usuariosContratados));
        if (pacoteDef) {
            return calcularOrcamentoLocal(pacoteDef, usersEfetivos, cicloAlvo, extensoesEfetivas, extensoesDisponiveis);
        }
        const base = cicloAlvo === "ANUAL" ? plano.preco_anual : plano.preco_mensal;
        return {
            valorPacoteBase: base,
            valorUsuariosAdicionais: 0,
            valorExtensoes: 0,
            extensoesSelecionadas: [],
            valorTotal: base,
            equivalenteMensal: cicloAlvo === "ANUAL" ? base / 12 : base,
            usuariosInclusos: minUsers,
            usuariosAdicionais: Math.max(0, usersEfetivos - minUsers),
            economiaAnualTotal: plano.preco_mensal * 12 - plano.preco_anual,
        };
    };

    const step1Valido = !!planoSelecionado && areaTotalNum > 0;

    const step2Valido =
        nomeProdutor.trim().length >= 2 &&
        nomeCompleto.trim().length >= 3 &&
        username.trim().length >= 3 &&
        email.includes("@") &&
        senha.length >= 6 &&
        senha === confirmarSenha;

    const irParaEtapa2 = () => {
        if (!step1Valido) {
            toast.error("Informe a área da propriedade e selecione um pacote para continuar.");
            return;
        }
        startTransition(() => setStep(2));
    };

    const irParaEtapa3 = () => {
        if (!step2Valido) {
            toast.error("Preencha os dados do produtor e suas credenciais de acesso corretamente.");
            return;
        }
        startTransition(() => setStep(3));
    };

    const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        if (!file.type.startsWith("image/")) {
            toast.error("Selecione um arquivo de imagem.");
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            toast.error("A imagem deve ter no máximo 5MB.");
            return;
        }

        setFotoUrl(URL.createObjectURL(file));
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    const handleSubmit = async () => {
        if (!planoSelecionado) return;
        setIsLoading(true);
        try {
            if (cnpjCpf.trim()) {
                const check = await apiFetch<{ disponivel: boolean; mensagem: string | null }>(
                    `/onboarding/verificar-documento/${encodeURIComponent(cnpjCpf.trim())}`
                );
                if (!check.disponivel) {
                    toast.error(check.mensagem || "CPF ou CNPJ já cadastrado.");
                    setIsLoading(false);
                    return;
                }
            }

            let planoIdFinal = planoSelecionado.id;
            if (planoIdFinal.startsWith("local-")) {
                const listaReal = await apiFetch<Plano[]>("/billing/plans");
                const encontrado =
                    listaReal.find((p) => p.nome.toLowerCase() === planoSelecionado.nome.toLowerCase()) ??
                    listaReal[0];
                if (!encontrado) {
                    toast.error("Não foi possível localizar o pacote selecionado no servidor.");
                    setIsLoading(false);
                    return;
                }
                planoIdFinal = encontrado.id;
            }

            await apiFetch<{ access_token: string }>("/onboarding/assinante", {
                method: "POST",
                body: {
                    email,
                    username,
                    nome_completo: nomeCompleto,
                    apelido: apelido.trim(),
                    senha,
                    cpf: cpf.replace(/\D/g, "") || undefined,
                    telefone: telefone.replace(/\D/g, "") || undefined,
                    nome_produtor: nomeProdutor,
                    cnpj_tenant: cnpjCpf || undefined,
                    plano_id: planoIdFinal,
                    ciclo,
                    usuarios_contratados: Math.max(
                        planoSelecionado.limite_usuarios_minimo ?? 1,
                        usuariosContratados
                    ),
                    extensoes_contratadas: extensoesEfetivas,
                },
            });

            toast.success("Conta criada com sucesso. Enviamos um e-mail para confirmar seu cadastro.");
            router.push("/login");
        } catch (error: unknown) {
            toast.error(error instanceof Error ? error.message : "Erro ao criar conta. Tente novamente.");
        } finally {
            setIsLoading(false);
        }
    };

    const userInitial = nomeCompleto.trim().charAt(0).toUpperCase() || "U";
    const orcamentoAtual = planoSelecionado ? calcularOrcamentoPlano(planoSelecionado, ciclo) : null;
    const orcamentoMensalRef = planoSelecionado ? calcularOrcamentoPlano(planoSelecionado, "MENSAL") : null;
    const orcamentoAnualRef = planoSelecionado ? calcularOrcamentoPlano(planoSelecionado, "ANUAL") : null;
    const percentualReducaoAnual =
        orcamentoMensalRef && orcamentoAnualRef && orcamentoMensalRef.equivalenteMensal > 0
            ? Math.round(
                  ((orcamentoMensalRef.equivalenteMensal - orcamentoAnualRef.equivalenteMensal) /
                      orcamentoMensalRef.equivalenteMensal) *
                      100
              )
            : 17;

    return (
        <div className="space-y-4">
            {/* Barra Superior: Título + Stepper Translúcido */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-900/10 dark:border-white/10">
                <div className="flex items-center gap-3">
                    <div className="inline-flex items-center justify-center size-10 rounded-sm bg-primary border border-primary/20 shadow-md shadow-primary/20 shrink-0">
                        <Shield className="size-5 text-primary-foreground" />
                    </div>
                    <div>
                        <h2 className="text-lg font-light tracking-tight text-foreground uppercase italic leading-none">
                            {step === 1
                                ? "Simulador Transparente de Assinatura"
                                : step === 2
                                    ? "Cadastro do Produtor e Credenciais"
                                    : "Confirmação da Assinatura"}
                        </h2>
                        <p className="text-xs text-muted-foreground mt-1">
                            {step === 1
                                ? "Entenda como calculamos o valor e simule sua mensalidade ou anuidade antes do cadastro."
                                : step === 2
                                    ? "Informe os dados da sua propriedade e crie suas credenciais de acesso."
                                    : "Confira os dados e o extrato transparente para iniciar seus 14 dias grátis."}
                        </p>
                    </div>
                </div>

                {/* Stepper Horizontal Translúcido */}
                <div className="flex items-center gap-3 shrink-0">
                    <div className="flex items-center gap-2 rounded-sm border border-slate-900/10 bg-white/30 px-3 py-1.5 backdrop-blur-sm dark:border-white/10 dark:bg-white/5">
                        {[
                            { num: 1, icon: Calculator, label: "1. Simular" },
                            { num: 2, icon: User, label: "2. Cadastro" },
                            { num: 3, icon: Check, label: "3. Confirmar" },
                        ].map((s, idx) => (
                            <div key={s.num} className="flex items-center gap-1.5">
                                <div
                                    className={`size-6 rounded-sm flex items-center justify-center text-[10px] font-semibold transition-all ${
                                        s.num < step
                                            ? "bg-primary text-primary-foreground shadow-sm"
                                            : s.num === step
                                                ? "bg-primary/15 text-primary border border-primary/40"
                                                : "bg-white/30 text-muted-foreground/50 dark:bg-white/5"
                                    }`}
                                >
                                    {s.num < step ? <Check size={11} /> : <s.icon size={11} />}
                                </div>
                                <span
                                    className={`text-[11px] font-semibold uppercase tracking-wider ${
                                        s.num === step ? "text-primary" : "text-muted-foreground/50"
                                    }`}
                                >
                                    {s.label}
                                </span>
                                {idx < 2 && <span className="text-muted-foreground/30 text-xs mx-0.5">›</span>}
                            </div>
                        ))}
                    </div>

                    <Link
                        href="/login"
                        className="text-xs font-semibold uppercase text-primary hover:underline whitespace-nowrap"
                    >
                        Entrar
                    </Link>
                </div>
            </div>

            {/* ── Step 1: Simulador Transparente Aproveitando 100% da Largura e Altura ── */}
            {step === 1 && (
                <div className="space-y-4">
                    {/* Faixa 1: Os 3 Pilares Transparentes de Cálculo */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div className="rounded-sm border border-slate-900/10 bg-white/30 p-3 backdrop-blur-sm dark:border-white/10 dark:bg-white/5">
                            <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground mb-1">
                                <Layers size={14} className="text-primary shrink-0" />
                                <span>1. 100% dos Módulos</span>
                            </div>
                            <p className="text-[11px] leading-relaxed text-muted-foreground">
                                Todos os pacotes liberam a plataforma completa (Agrícola, Pecuária, Financeiro, Estoque, ESG e IA).{" "}
                                <strong>As extensões IoT e ERP são contratadas à parte.</strong>
                            </p>
                        </div>

                        <div className="rounded-sm border border-slate-900/10 bg-white/30 p-3 backdrop-blur-sm dark:border-white/10 dark:bg-white/5">
                            <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground mb-1">
                                <Leaf size={14} className="text-emerald-600 shrink-0" />
                                <span>2. Área Produtiva (HEq)</span>
                            </div>
                            <p className="text-[11px] leading-relaxed text-muted-foreground">
                                <strong>Reserva Legal e APP são 100% isentas (R$ 0)</strong> e <em>Safra + Safrinha</em> no mesmo talhão não pagam em dobro.
                            </p>
                        </div>

                        <div className="rounded-sm border border-slate-900/10 bg-white/30 p-3 backdrop-blur-sm dark:border-white/10 dark:bg-white/5">
                            <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground mb-1">
                                <Smartphone size={14} className="text-emerald-600 shrink-0" />
                                <span>3. App Campo Grátis</span>
                            </div>
                            <p className="text-[11px] leading-relaxed text-muted-foreground">
                                Só conta acesso simultâneo no Painel Web. <strong>O App Campo (celular offline) é 100% isento.</strong>
                            </p>
                        </div>
                    </div>

                    {/* Faixa 2: Área de Inputs Bem Distribuída e Translúcida */}
                    <div className="rounded-sm border border-slate-900/10 bg-white/25 p-4 space-y-3.5 backdrop-blur-sm dark:border-white/10 dark:bg-white/5">
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                            <div className="flex items-center gap-2">
                                <Calculator className="size-4 text-primary" />
                                <span className="text-xs font-semibold uppercase tracking-wider text-foreground">
                                    Informe os dados da sua operação para calcular a assinatura
                                </span>
                            </div>
                            <div className="flex items-center gap-3 text-xs">
                                <span className="text-muted-foreground">
                                    Área Produtiva Líquida:{" "}
                                    <strong className="text-foreground">{areaProdutivaLiquida} ha</strong>{" "}
                                    <span className="text-emerald-600 font-medium">
                                        ({areaAmbientalNum} ha APP/RL isentos)
                                    </span>
                                </span>
                                <span className="text-muted-foreground">·</span>
                                <span className="text-muted-foreground">
                                    Capacidade Equivalente:{" "}
                                    <strong className="text-primary">{hectaresEquivalentes} HEq</strong>
                                </span>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 items-end">
                            <div className="space-y-1.5 min-w-0">
                                <Label className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground gap-1 whitespace-nowrap">
                                    <Tractor size={12} className="text-primary shrink-0" />
                                    <span>Área Total (ha)</span>
                                    <FieldHelp text="Soma da área física total (em hectares) de todas as propriedades rurais que serão gerenciadas na assinatura." />
                                </Label>
                                <Input
                                    type="number"
                                    min={1}
                                    value={areaEstimadaHa}
                                    onChange={(e) => {
                                        setAreaEstimadaHa(e.target.value);
                                        setEscolhaManualPlano(false);
                                    }}
                                    className="font-semibold"
                                />
                            </div>

                            <div className="space-y-1.5 min-w-0">
                                <Label className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground gap-1 whitespace-nowrap">
                                    <span>APP / Reserva Legal (ha)</span>
                                    <FieldHelp text="Áreas de Preservação Permanente (APP) e Reserva Legal. São 100% isentas (R$ 0) e descontadas automaticamente da Área Total." />
                                </Label>
                                <Input
                                    type="number"
                                    min={0}
                                    value={areaAmbientalHa}
                                    onChange={(e) => {
                                        setAreaAmbientalHa(e.target.value);
                                        setEscolhaManualPlano(false);
                                    }}
                                />
                            </div>

                            <div className="space-y-1.5 min-w-0">
                                <Label className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground gap-1 whitespace-nowrap">
                                    <span>Rebanho (cabeças)</span>
                                    <FieldHelp text="Total de bovinos ativos. O plano já inclui gratuitamente até 2 cabeças por hectare produtivo (ILP); apenas o excedente é convertido (2 cabeças = 1 HEq)." />
                                </Label>
                                <Input
                                    type="number"
                                    min={0}
                                    value={cabecasPecuaria}
                                    onChange={(e) => {
                                        setCabecasPecuaria(e.target.value);
                                        setEscolhaManualPlano(false);
                                    }}
                                    placeholder="0 (até 2 cab/ha isentas)"
                                />
                            </div>

                            <div className="space-y-1.5 min-w-0">
                                <Label className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground gap-1 whitespace-nowrap">
                                    <Users size={12} className="text-primary shrink-0" />
                                    <span>Acessos Simultâneos Web</span>
                                    <FieldHelp text="Quantidade de pessoas conectadas ao mesmo tempo no Painel Web. O cadastro de membros na equipe é ilimitado e o uso do App Campo no celular é 100% livre." />
                                </Label>
                                <Input
                                    type="number"
                                    min={1}
                                    max={100}
                                    value={usuariosContratados}
                                    onChange={(e) =>
                                        setUsuariosContratados(Math.max(1, Number(e.target.value) || 1))
                                    }
                                    className="font-semibold"
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
                            <div className="sm:col-span-6 space-y-1.5">
                                <Label className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground gap-1 whitespace-nowrap">
                                    <span>Cultura / Atividade Predominante</span>
                                    <FieldHelp text="Define o fator agronômico de intensidade operacional para cálculo dos Hectares Equivalentes (HEq). Safra + Safrinha ou consórcio no mesmo talhão não cobram em dobro." />
                                </Label>
                                <Select
                                    value={vocacaoPredominante}
                                    onValueChange={(val) => {
                                        setVocacaoPredominante(val);
                                        setEscolhaManualPlano(false);
                                    }}
                                >
                                    <SelectTrigger className="text-xs">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {Object.entries(FATORES_VOCACAO_HEQ).map(([key, item]) => (
                                            <SelectItem key={key} value={key}>
                                                {item.label}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="sm:col-span-6 space-y-1.5">
                                <Label className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground gap-1 whitespace-nowrap">
                                    <span>Modalidade de Pagamento</span>
                                    <FieldHelp text="Escolha entre cobrança Mensal ou Anual. No plano Anual o valor mensal baixa (2 meses grátis no pacote base + 20% de desconto nos acessos extras e extensões)." />
                                </Label>
                                <div className="flex items-center gap-1.5">
                                    <Button
                                        type="button"
                                        size="default"
                                        variant={ciclo === "MENSAL" ? "default" : "outline"}
                                        onClick={() => setCiclo("MENSAL")}
                                        className="px-3 text-xs font-semibold shrink-0"
                                    >
                                        Mensal
                                        {orcamentoMensalRef && (
                                            <span className="ml-1 text-[10px] font-normal opacity-90">
                                                (R$ {orcamentoMensalRef.equivalenteMensal.toFixed(0)}/mês)
                                            </span>
                                        )}
                                    </Button>
                                    <Button
                                        type="button"
                                        size="default"
                                        variant={ciclo === "ANUAL" ? "default" : "outline"}
                                        onClick={() => setCiclo("ANUAL")}
                                        className="flex-1 px-2.5 text-xs font-semibold"
                                    >
                                        <span>Anual</span>
                                        <span className="text-[10px] font-medium opacity-95">
                                            {orcamentoAnualRef
                                                ? `(baixa ${percentualReducaoAnual}% → R$ ${orcamentoAnualRef.equivalenteMensal.toFixed(2).replace(".", ",")}/mês)`
                                                : `(baixa ${percentualReducaoAnual}% no valor mensal)`}
                                        </span>
                                    </Button>
                                </div>
                            </div>
                        </div>

                        {/* Seleção de Extensões Contratadas à Parte (IoT e ERP) */}
                        <div className="pt-2 border-t border-slate-900/10 dark:border-white/10 space-y-1.5">
                            <div className="flex items-center justify-between gap-2 flex-wrap">
                                <Label className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground gap-1">
                                    <span>Extensões Opcionais Contratadas à Parte (selecione para incluir na mensalidade):</span>
                                    <FieldHelp text="Módulos corporativos opcionais (Integração IoT para sensores/telemetria e Bridge ERP para integração com SAP, TOTVS, Senior e Sankhya) que podem ser adicionados à assinatura." />
                                </Label>
                                {ciclo === "ANUAL" && (
                                    <span className="text-[10px] font-semibold text-emerald-700 dark:text-emerald-400">
                                        20% de desconto aplicado nas extensões no plano Anual
                                    </span>
                                )}
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                                {extensoesDisponiveis.map((ext) => {
                                    const indisponivel = ext.ativo === false;
                                    const selecionada = !indisponivel && extensoesEfetivas.includes(ext.id);
                                    const precoExibido =
                                        ciclo === "ANUAL" ? ext.precoMensalEquivalenteAnual : ext.precoMensal;
                                    return (
                                        <div
                                            key={ext.id}
                                            role="button"
                                            tabIndex={indisponivel ? -1 : 0}
                                            aria-disabled={indisponivel}
                                            title={indisponivel ? "Extensão indisponível no momento" : undefined}
                                            onClick={() => {
                                                if (!indisponivel) alternarExtensao(ext.id);
                                            }}
                                            onKeyDown={(e) => {
                                                if (indisponivel) return;
                                                if (e.key === "Enter" || e.key === " ") {
                                                    e.preventDefault();
                                                    alternarExtensao(ext.id);
                                                }
                                            }}
                                            className={`flex items-center justify-between gap-3 p-2.5 rounded-sm border text-left transition-all select-none ${
                                                indisponivel
                                                    ? "cursor-not-allowed opacity-55 border-dashed border-slate-400/40 bg-muted/30 dark:border-white/15"
                                                    : selecionada
                                                        ? "cursor-pointer border-primary bg-primary/15 shadow-sm ring-1 ring-primary/30"
                                                        : "cursor-pointer border-slate-400/40 bg-white/35 hover:border-primary/40 dark:border-white/15 dark:bg-white/5"
                                            }`}
                                        >
                                            <div className="flex items-center gap-2.5 min-w-0">
                                                <Checkbox
                                                    checked={selecionada}
                                                    disabled={indisponivel}
                                                    onCheckedChange={() => alternarExtensao(ext.id)}
                                                    onClick={(e) => e.stopPropagation()}
                                                />
                                                <div className="min-w-0">
                                                    <p className="text-xs font-bold text-foreground truncate flex items-center gap-1.5">
                                                        {ext.nome}
                                                        {indisponivel && (
                                                            <Badge variant="outline" className="text-[9px] h-4 px-1.5 rounded-sm">
                                                                Indisponível
                                                            </Badge>
                                                        )}
                                                    </p>
                                                    <p className="text-[10px] text-muted-foreground truncate">
                                                        {ext.descricaoCurta}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="text-right shrink-0 whitespace-nowrap">
                                                <span className="text-xs font-bold text-foreground">
                                                    +R$ {precoExibido.toFixed(2).replace(".", ",")}
                                                </span>
                                                <span className="text-[10px] text-muted-foreground">/mês</span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>

                    {/* Faixa 3: Os 5 Pacotes Distribuídos em Largura Total */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                                Pacotes disponíveis (todos com 100% dos módulos — clique se desejar alterar):
                            </span>
                            {escolhaManualPlano ? (
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    className="h-6 px-2 text-[11px] text-primary"
                                    onClick={() => {
                                        setEscolhaManualPlano(false);
                                        setNomePlanoManual(null);
                                    }}
                                >
                                    Voltar ao pacote recomendado
                                </Button>
                            ) : loadingPlanos ? (
                                <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                                    <Loader2 size={11} className="animate-spin" /> Sincronizando...
                                </span>
                            ) : null}
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
                            {planosOrdenados.map((plano) => {
                                const orc = calcularOrcamentoPlano(plano, ciclo);
                                const isRecomendado = planoRecomendado?.nome === plano.nome;
                                const isSelecionado = planoSelecionado?.nome === plano.nome;

                                return (
                                    <button
                                        key={plano.id}
                                        type="button"
                                        onClick={() => {
                                            setEscolhaManualPlano(true);
                                            setNomePlanoManual(plano.nome);
                                            if (
                                                plano.limite_usuarios_minimo &&
                                                usuariosContratados < plano.limite_usuarios_minimo
                                            ) {
                                                setUsuariosContratados(plano.limite_usuarios_minimo);
                                            }
                                        }}
                                        className={`text-left p-3 rounded-sm border transition-all flex flex-col justify-between backdrop-blur-sm ${
                                            isSelecionado
                                                ? "border-primary bg-primary/15 shadow-md shadow-primary/10 ring-1 ring-primary/30"
                                                : "border-slate-900/10 bg-white/30 hover:border-primary/40 dark:border-white/10 dark:bg-white/5"
                                        }`}
                                    >
                                        <div>
                                            <div className="flex items-center justify-between gap-1">
                                                <span className="font-bold text-xs text-foreground truncate">
                                                    {plano.nome}
                                                </span>
                                                {isRecomendado && (
                                                    <Badge className="text-[9px] h-4 px-1.5 rounded-sm bg-primary text-primary-foreground shrink-0">
                                                        Ideal
                                                    </Badge>
                                                )}
                                            </div>
                                            <p className="text-[10px] text-muted-foreground mt-1">
                                                {plano.limite_hectares
                                                    ? `Até ${plano.limite_hectares.toLocaleString("pt-BR")} HEq`
                                                    : "HEq ilimitado"}
                                            </p>
                                            <p className="text-[10px] text-muted-foreground">
                                                {orc.usuariosInclusos} acesso(s) incluso(s)
                                            </p>
                                        </div>
                                        <div className="mt-2 pt-1.5 border-t border-slate-900/10 dark:border-white/10">
                                            <span className="text-sm font-bold text-foreground">
                                                R$ {orc.equivalenteMensal.toFixed(0)}
                                            </span>
                                            <span className="text-[10px] text-muted-foreground">/mês</span>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Faixa 4: Extrato Transparente + Ação de Avançar */}
                    {planoSelecionado && orcamentoAtual && (
                        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center rounded-sm border border-primary/30 bg-primary/10 p-4 backdrop-blur-sm">
                            <div className="md:col-span-8 space-y-1.5">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <Badge className="text-[10px] rounded-sm bg-primary text-primary-foreground">
                                        Extrato Transparente · Pacote {planoSelecionado.nome}
                                    </Badge>
                                    {orcamentoAtual.economiaAnualTotal > 0 && (
                                        <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 flex items-center gap-1">
                                            <Sparkles size={12} />
                                            {ciclo === "ANUAL" ? "Economia garantida no Anual:" : "Economize no Anual:"}{" "}
                                            R$ {orcamentoAtual.economiaAnualTotal.toFixed(2).replace(".", ",")}/ano
                                        </span>
                                    )}
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-5 gap-y-1.5 text-xs pt-1">
                                    <div className="flex items-center justify-between gap-2 text-muted-foreground">
                                        <span className="truncate">Pacote Base ({orcamentoAtual.usuariosInclusos} acesso(s) Web):</span>
                                        <strong className="text-foreground whitespace-nowrap shrink-0">
                                            R$ {orcamentoAtual.valorPacoteBase.toFixed(2).replace(".", ",")}/{ciclo === "ANUAL" ? "ano" : "mês"}
                                        </strong>
                                    </div>
                                    <div className="flex items-center justify-between gap-2 text-muted-foreground">
                                        <span className="truncate">
                                            {orcamentoAtual.usuariosAdicionais > 0
                                                ? `+${orcamentoAtual.usuariosAdicionais} acesso(s) extra(s) Web:`
                                                : "Acessos extras Web:"}
                                        </span>
                                        <strong className="text-foreground whitespace-nowrap shrink-0">
                                            R$ {orcamentoAtual.valorUsuariosAdicionais.toFixed(2).replace(".", ",")}/{ciclo === "ANUAL" ? "ano" : "mês"}
                                        </strong>
                                    </div>
                                    {orcamentoAtual.valorExtensoes > 0 && (
                                        <div className="flex items-center justify-between gap-2 text-muted-foreground">
                                            <span className="truncate">
                                                Extensões ({nomesExtensoesEfetivas.join(" + ")}):
                                            </span>
                                            <strong className="text-foreground whitespace-nowrap shrink-0">
                                                R$ {orcamentoAtual.valorExtensoes.toFixed(2).replace(".", ",")}/{ciclo === "ANUAL" ? "ano" : "mês"}
                                            </strong>
                                        </div>
                                    )}
                                    <div className="flex items-center justify-between gap-2 text-emerald-700 dark:text-emerald-400 font-medium">
                                        <span className="truncate">App Campo (offline no celular):</span>
                                        <span className="whitespace-nowrap shrink-0">Isento (R$ 0,00)</span>
                                    </div>
                                    <div className="flex items-center justify-between gap-2 font-semibold text-foreground">
                                        <span className="truncate">Total {ciclo === "ANUAL" ? "Anual" : "Mensal"} (após 14d grátis):</span>
                                        <span className="whitespace-nowrap shrink-0">R$ {orcamentoAtual.valorTotal.toFixed(2).replace(".", ",")}</span>
                                    </div>
                                </div>
                            </div>

                            <div className="md:col-span-4 flex flex-col sm:flex-row md:flex-col items-stretch sm:items-center md:items-end justify-between gap-2.5 md:border-l md:border-primary/20 md:pl-4">
                                <div className="text-left md:text-right">
                                    <div className="text-2xl font-bold text-foreground leading-none">
                                        R$ {orcamentoAtual.equivalenteMensal.toFixed(2).replace(".", ",")}
                                        <span className="text-xs font-normal text-muted-foreground">/mês</span>
                                    </div>
                                    <p className="text-[11px] text-muted-foreground mt-0.5">
                                        14 dias grátis · Sem cobrança hoje
                                    </p>
                                </div>
                                <Button
                                    onClick={irParaEtapa2}
                                    disabled={!step1Valido || isPending}
                                    size="sm"
                                    variant="default"
                                    className="w-full h-9 font-semibold uppercase tracking-wider text-xs"
                                >
                                    Avançar para Cadastro <ChevronRight size={14} className="ml-1" />
                                </Button>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ── Step 2: Dados do Produtor + Credenciais de Acesso com Aproveitamento Total e Translúcido ── */}
            {step === 2 && (
                <div className="space-y-4">
                    {/* Faixa Resumo do Valor Simulado no Passo 1 */}
                    {planoSelecionado && orcamentoAtual && (
                        <div className="flex items-center justify-between gap-3 p-3 rounded-sm bg-primary/10 border border-primary/25 backdrop-blur-sm">
                            <div>
                                <p className="text-[10px] uppercase tracking-wider font-bold text-primary">
                                    Pacote Simulado: {planoSelecionado.nome} ({ciclo === "ANUAL" ? "Anual" : "Mensal"})
                                </p>
                                <p className="text-xs font-bold text-foreground">
                                    R$ {orcamentoAtual.equivalenteMensal.toFixed(2).replace(".", ",")}/mês{" "}
                                    <span className="text-[11px] font-normal text-muted-foreground">
                                        ({orcamentoAtual.usuariosInclusos + orcamentoAtual.usuariosAdicionais} acesso(s) Web ·{" "}
                                        {hectaresEquivalentes} HEq · App Campo Isento
                                        {nomesExtensoesEfetivas.length > 0
                                            ? ` · +${nomesExtensoesEfetivas.join(", ")}`
                                            : ""}
                                        )
                                    </span>
                                </p>
                            </div>
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="h-8 text-xs rounded-sm shrink-0"
                                onClick={() => startTransition(() => setStep(1))}
                            >
                                Editar Simulação
                            </Button>
                        </div>
                    )}

                    {/* Bloco 1: Dados do Produtor + Foto em Linha */}
                    <div className="rounded-sm border border-slate-900/10 bg-white/25 p-4 space-y-3 backdrop-blur-sm dark:border-white/10 dark:bg-white/5">
                        <div className="flex items-center gap-2">
                            <Building2 className="size-4 text-primary" />
                            <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">
                                Dados do Produtor / Propriedade
                            </h3>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center">
                            <div className="sm:col-span-5">
                                <Field
                                    label="Nome do Produtor / Fazenda *"
                                    placeholder="Ex: Fazenda São José ou João Silva"
                                    value={nomeProdutor}
                                    onChange={setNomeProdutor}
                                    icon={Building2}
                                    help="Nome comercial da propriedade rural, grupo agrícola ou nome do produtor titular da assinatura."
                                />
                            </div>
                            <div className="sm:col-span-4">
                                <Field
                                    label="CNPJ / CPF do Produtor (opcional)"
                                    placeholder="000.000.000-00 ou 00.000.000/0000-00"
                                    value={cnpjCpf}
                                    onChange={setCnpjCpf}
                                    help="CPF ou CNPJ principal vinculado à operação rural para identificação fiscal e faturamento."
                                />
                            </div>
                            <div className="sm:col-span-3 flex items-center gap-3 pt-2 sm:pt-4">
                                <div className="relative group shrink-0">
                                    <Avatar className="size-10 border border-slate-400/40 shadow-inner">
                                        <AvatarImage src={fotoUrl || undefined} alt={userInitial} />
                                        <AvatarFallback className="bg-primary/10 text-primary text-sm font-semibold italic">
                                            {userInitial}
                                        </AvatarFallback>
                                    </Avatar>
                                    <Button
                                        type="button"
                                        onClick={() => fileInputRef.current?.click()}
                                        disabled={isUploading}
                                        variant="default"
                                        size="icon-xs"
                                        className="absolute -bottom-1 -right-1 rounded-sm shadow-lg"
                                        aria-label="Enviar foto"
                                    >
                                        {isUploading ? (
                                            <Loader2 className="size-2.5 animate-spin" />
                                        ) : (
                                            <Camera className="size-2.5" />
                                        )}
                                    </Button>
                                    <input
                                        ref={fileInputRef}
                                        type="file"
                                        accept="image/jpeg,image/png,image/webp"
                                        onChange={handleAvatarUpload}
                                        className="hidden"
                                    />
                                </div>
                                <div className="min-w-0">
                                    <p className="text-[11px] font-semibold text-foreground uppercase leading-tight">
                                        Foto (Opcional)
                                    </p>
                                    <p className="text-[10px] text-muted-foreground leading-tight">
                                        Perfil visual
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Bloco 2: Credenciais de Acesso Bem Distribuídas */}
                    <div className="rounded-sm border border-slate-900/10 bg-white/25 p-4 space-y-3.5 backdrop-blur-sm dark:border-white/10 dark:bg-white/5">
                        <div className="flex items-center gap-2">
                            <User className="size-4 text-primary" />
                            <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">
                                Suas Credenciais de Acesso
                            </h3>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <Field
                                label="Nome completo *"
                                placeholder="Seu nome"
                                value={nomeCompleto}
                                onChange={setNomeCompleto}
                                icon={User}
                                help="Nome completo do administrador principal responsável pela conta."
                            />
                            <Field
                                label="Apelido"
                                placeholder="Como quer ser chamado"
                                value={apelido}
                                onChange={(value) => setApelido(value.slice(0, 20))}
                                icon={User}
                                help="Nome curto pelo qual você prefere ser identificado nas telas da plataforma."
                            />
                            <Field
                                label="Usuário (login) *"
                                placeholder="ex: joaosilva"
                                value={username}
                                onChange={setUsername}
                                icon={User}
                                help="Identificador único sem espaços usado para entrar no sistema (além do seu e-mail)."
                            />
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <Field
                                label="E-mail *"
                                type="email"
                                placeholder="contato@fazenda.com"
                                value={email}
                                onChange={setEmail}
                                icon={Mail}
                                help="E-mail principal para confirmação do cadastro, alertas operacionais e recuperação de senha."
                            />
                            <Field
                                label="CPF"
                                placeholder="000.000.000-00"
                                value={cpf}
                                onChange={(v) => setCpf(formatCpf(v))}
                                help="CPF individual do usuário administrador responsável pelo acesso."
                            />
                            <Field
                                label="Telefone / WhatsApp"
                                placeholder="(00) 00000-0000"
                                value={telefone}
                                onChange={(v) => setTelefone(formatPhone(v))}
                                help="Número com DDD para suporte técnico, alertas críticos e notificações importantes."
                            />
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <Field
                                label="Senha (mín. 6 caracteres) *"
                                type="password"
                                placeholder="••••••••"
                                value={senha}
                                onChange={setSenha}
                                help="Crie uma senha segura com pelo menos 6 caracteres para proteger o acesso à sua fazenda."
                            />
                            <Field
                                label="Confirmar senha *"
                                type="password"
                                placeholder="••••••••"
                                value={confirmarSenha}
                                onChange={setConfirmarSenha}
                                help="Repita exatamente a senha digitada ao lado para confirmar."
                            />
                        </div>

                        {confirmarSenha && senha !== confirmarSenha && (
                            <div className="flex items-center gap-2 p-2 rounded-sm bg-destructive/10 border border-destructive/20">
                                <p className="text-xs text-destructive">As senhas não coincidem.</p>
                            </div>
                        )}

                        {senha.length >= 6 && senha === confirmarSenha && (
                            <div className="flex items-center gap-2 p-2 rounded-sm bg-primary/10 border border-primary/20">
                                <Check size={12} className="text-primary" />
                                <p className="text-xs text-primary">Senha válida</p>
                            </div>
                        )}

                        <div className="flex items-center justify-between pt-2 border-t border-slate-900/10 dark:border-white/10">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => startTransition(() => setStep(1))}
                                className="text-muted-foreground hover:text-foreground h-9"
                            >
                                <ArrowLeft size={14} className="mr-1" /> Voltar ao Simulador
                            </Button>
                            <Button
                                onClick={irParaEtapa3}
                                disabled={!step2Valido || isPending}
                                size="sm"
                                variant="default"
                                className="h-9 px-5"
                            >
                                Revisar e Confirmar <ChevronRight size={14} className="ml-1" />
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* ── Step 3: Confirmação Final em 2 Colunas Translúcidas ── */}
            {step === 3 && planoSelecionado && orcamentoAtual && (
                <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-stretch">
                    {/* Coluna Esquerda (6 cols): Resumo dos Dados Cadastrais */}
                    <div className="md:col-span-6 rounded-sm border border-slate-900/10 bg-white/30 p-4 space-y-3 backdrop-blur-sm dark:border-white/10 dark:bg-white/5">
                        <div className="flex items-center gap-2 pb-2 border-b border-slate-900/10 dark:border-white/10">
                            <User className="size-4 text-primary" />
                            <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">
                                Dados do Produtor e Responsável
                            </h3>
                        </div>
                        <SummaryRow label="Produtor / Fazenda" value={nomeProdutor} icon={Building2} />
                        {cnpjCpf && <SummaryRow label="CNPJ/CPF Produtor" value={cnpjCpf} />}
                        <SummaryRow label="Responsável" value={nomeCompleto} icon={User} />
                        <SummaryRow label="Usuário" value={username} />
                        <SummaryRow label="E-mail" value={email} icon={Mail} />
                        {telefone && <SummaryRow label="Telefone" value={telefone} />}
                        <Separator className="bg-slate-900/10 dark:bg-white/10" />
                        <SummaryRow
                            label="Área Total Informada"
                            value={`${areaTotalNum} ha (${areaAmbientalNum} ha APP/RL isentos)`}
                            icon={Tractor}
                        />
                        <SummaryRow label="Capacidade Equivalente" value={`${hectaresEquivalentes} HEq`} />
                        <SummaryRow
                            label="Acessos Simultâneos Web"
                            value={`${orcamentoAtual.usuariosInclusos + orcamentoAtual.usuariosAdicionais} acesso(s) simultâneo(s)`}
                            icon={Users}
                        />
                    </div>

                    {/* Coluna Direita (6 cols): Extrato Transparente e Botão Criar Conta */}
                    <div className="md:col-span-6 flex flex-col justify-between space-y-4 rounded-sm border border-primary/30 bg-primary/10 p-4 backdrop-blur-sm">
                        <div className="space-y-3">
                            <div className="flex items-center justify-between gap-2">
                                <div className="flex items-center gap-2">
                                    <CreditCard className="size-4 text-primary" />
                                    <div>
                                        <p className="text-[10px] text-muted-foreground uppercase font-semibold">
                                            Pacote Selecionado (100% dos Módulos)
                                        </p>
                                        <p className="text-base font-bold text-foreground">
                                            {planoSelecionado.nome} ({ciclo === "ANUAL" ? "Anual" : "Mensal"})
                                        </p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <span className="text-xl font-bold text-foreground">
                                        R$ {orcamentoAtual.equivalenteMensal.toFixed(2).replace(".", ",")}
                                    </span>
                                    <span className="text-[10px] text-muted-foreground">/mês</span>
                                </div>
                            </div>

                            <div className="space-y-1.5 pt-2.5 border-t border-primary/20 text-xs">
                                <div className="flex justify-between text-muted-foreground">
                                    <span>
                                        Pacote Base ({orcamentoAtual.usuariosInclusos} acesso(s) simultâneo(s) incluso(s))
                                    </span>
                                    <span className="font-semibold text-foreground">
                                        R$ {orcamentoAtual.valorPacoteBase.toFixed(2).replace(".", ",")}/
                                        {ciclo === "ANUAL" ? "ano" : "mês"}
                                    </span>
                                </div>
                                {orcamentoAtual.usuariosAdicionais > 0 && (
                                    <div className="flex justify-between text-muted-foreground">
                                        <span>
                                            +{orcamentoAtual.usuariosAdicionais} licença(s) adicional(is) Web{" "}
                                            {ciclo === "ANUAL" ? "(20% OFF)" : ""}
                                        </span>
                                        <span className="font-semibold text-foreground whitespace-nowrap">
                                            R$ {orcamentoAtual.valorUsuariosAdicionais.toFixed(2).replace(".", ",")}/
                                            {ciclo === "ANUAL" ? "ano" : "mês"}
                                        </span>
                                    </div>
                                )}
                                {orcamentoAtual.valorExtensoes > 0 && (
                                    <div className="flex justify-between text-muted-foreground">
                                        <span>
                                            Extensões ({nomesExtensoesEfetivas.join(" + ")})
                                        </span>
                                        <span className="font-semibold text-foreground whitespace-nowrap">
                                            R$ {orcamentoAtual.valorExtensoes.toFixed(2).replace(".", ",")}/
                                            {ciclo === "ANUAL" ? "ano" : "mês"}
                                        </span>
                                    </div>
                                )}
                                <div className="flex justify-between text-emerald-700 dark:text-emerald-400 font-medium">
                                    <span>Aplicativo Campo (offline-first)</span>
                                    <span>Isento (R$ 0,00)</span>
                                </div>
                                <div className="flex justify-between pt-2 border-t border-primary/20 font-bold text-foreground text-sm">
                                    <span>Total {ciclo === "ANUAL" ? "Anual" : "Mensal"}</span>
                                    <span>R$ {orcamentoAtual.valorTotal.toFixed(2).replace(".", ",")}</span>
                                </div>
                            </div>

                            {planoSelecionado.tem_trial && planoSelecionado.dias_trial > 0 && (
                                <div className="flex items-center gap-2 p-2.5 rounded-sm bg-white/40 dark:bg-white/5 border border-primary/20">
                                    <Star size={13} className="text-primary shrink-0" />
                                    <p className="text-xs text-primary font-medium">
                                        {planoSelecionado.dias_trial} dias grátis para testar — nenhuma cobrança hoje.
                                    </p>
                                </div>
                            )}
                        </div>

                        <div className="flex items-center justify-between gap-2 pt-3 border-t border-primary/20">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => startTransition(() => setStep(2))}
                                className="text-muted-foreground hover:text-foreground h-9"
                            >
                                <ArrowLeft size={14} className="mr-1" /> Voltar aos Dados
                            </Button>
                            <Button
                                onClick={handleSubmit}
                                disabled={isLoading}
                                size="sm"
                                variant="default"
                                className="min-w-[180px] h-9 font-semibold uppercase tracking-widest text-xs"
                            >
                                {isLoading ? (
                                    <>
                                        <Loader2 size={14} className="mr-2 animate-spin" />
                                        Finalizando...
                                    </>
                                ) : (
                                    <>
                                        Criar minha conta <ArrowRight size={14} className="ml-2" />
                                    </>
                                )}
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// ── Helpers ───────────────────────────────────────────────
function FieldHelp({ text }: { text: string }) {
    return (
        <TooltipProvider delay={150}>
            <Tooltip>
                <TooltipTrigger tabIndex={-1} className="outline-none inline-flex items-center">
                    <HelpCircle className="size-3.5 text-primary/80 hover:text-primary cursor-help shrink-0" aria-hidden />
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs text-xs font-normal normal-case tracking-normal z-[100]">
                    {text}
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>
    );
}

function Field({
    label,
    placeholder,
    value,
    onChange,
    type = "text",
    icon: Icon,
    help,
}: {
    label: string;
    placeholder: string;
    value: string;
    onChange: (v: string) => void;
    type?: string;
    icon?: React.ComponentType<{ size?: number; className?: string }>;
    help?: string;
}) {
    return (
        <div className="space-y-1.5 min-w-0">
            <Label className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground gap-1 whitespace-nowrap">
                <span>{label}</span>
                {help && <FieldHelp text={help} />}
            </Label>
            <div className="relative">
                {Icon && (
                    <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none z-10">
                        <Icon size={14} className="text-primary/70" />
                    </div>
                )}
                {type === "password" ? (
                    <PasswordInput
                        placeholder={placeholder}
                        value={value}
                        onChange={(e) => onChange(e.target.value)}
                        className={Icon ? "pl-9" : ""}
                    />
                ) : (
                    <Input
                        type={type}
                        placeholder={placeholder}
                        value={value}
                        onChange={(e) => onChange(e.target.value)}
                        className={Icon ? "pl-9" : ""}
                    />
                )}
            </div>
        </div>
    );
}

function SummaryRow({
    label,
    value,
    icon: Icon,
}: {
    label: string;
    value: string;
    icon?: React.ComponentType<{ size?: number; className?: string }>;
}) {
    return (
        <div className="flex items-center justify-between text-xs font-medium py-0.5 gap-2">
            <div className="flex items-center gap-2 shrink-0">
                {Icon && <Icon size={13} className="text-primary/60" />}
                <span className="text-muted-foreground uppercase tracking-wider">{label}</span>
            </div>
            <span className="font-semibold text-foreground text-right">{value}</span>
        </div>
    );
}
