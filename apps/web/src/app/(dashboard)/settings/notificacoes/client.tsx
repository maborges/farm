"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { toast } from "sonner"
import { Bell, Mail, ShieldAlert, Zap, MessageSquare, Clock, CloudRain, Satellite, Users, Beef, ClipboardList, TriangleAlert, Lightbulb } from "lucide-react"
import { Input } from "@/components/ui/input"

interface Preferencia {
    tipo: string;
    email_ativo: boolean;
    sistema_ativo: boolean;
    whatsapp_ativo: boolean;
    horario_envio: string;
    nivel_sensibilidade: string;
}

const TIPOS_NOTIFICACAO = [
    { 
        id: "PLANO_ACAO", 
        titulo: "Planos de Ação", 
        desc: "Avisos sobre tarefas pendentes e execução do plano",
        icon: <Zap className="w-5 h-5 text-blue-500" />
    },
    { 
        id: "ALERTA_FINANCEIRO", 
        titulo: "Alertas Financeiros", 
        desc: "Avisos sobre margens negativas e custos excessivos",
        icon: <ShieldAlert className="w-5 h-5 text-red-500" />
    },
    { 
        id: "OPORTUNIDADE", 
        titulo: "Oportunidades IA", 
        desc: "Insights proativos sobre economia e ganhos de eficiência",
        icon: <Zap className="w-5 h-5 text-amber-500" />
    },
    {
        id: "RESUMO_DIARIO",
        titulo: "Resumo Inteligente Diário",
        desc: "Briefing consolidado com saúde financeira e alertas do dia",
        icon: <Zap className="w-5 h-5 text-emerald-500" />
    },
    {
        id: "PREVISAO_CHUVA",
        titulo: "Clima",
        desc: "Previsão de chuva com risco para aplicações programadas",
        icon: <CloudRain className="w-5 h-5 text-blue-500" />
    },
    {
        id: "NDVI_BAIXO",
        titulo: "NDVI",
        desc: "Queda no índice de vegetação abaixo do limiar esperado",
        icon: <Satellite className="w-5 h-5 text-orange-500" />
    },
    {
        id: "VENCIMENTO_APLICACAO",
        titulo: "Carência de Aplicação",
        desc: "Prazo de carência de defensivo vencendo em breve",
        icon: <Clock className="w-5 h-5 text-red-500" />
    },
    {
        id: "DIARIA_PENDENTE",
        titulo: "RH — Diárias Pendentes",
        desc: "Colaboradores com diárias não pagas há muito tempo",
        icon: <Users className="w-5 h-5 text-yellow-500" />
    },
    {
        id: "EMPREITADA_VENCENDO",
        titulo: "Empreitada",
        desc: "Contratos de empreitada próximos do vencimento",
        icon: <Beef className="w-5 h-5 text-purple-500" />
    },
    {
        id: "MANEJO_PENDENTE",
        titulo: "Pecuária — Manejo Pendente",
        desc: "Manejos programados aguardando execução",
        icon: <ShieldAlert className="w-5 h-5 text-green-500" />
    },
    {
        id: "RECOMENDACAO",
        titulo: "Recomendações",
        desc: "Sugestões operacionais de alta prioridade geradas pela IA",
        icon: <Lightbulb className="w-5 h-5 text-amber-500" />
    },
    {
        id: "WORKFLOW_OPERACIONAL",
        titulo: "Workflow Operacional",
        desc: "Pendências de aprovação e etapas de workflow",
        icon: <TriangleAlert className="w-5 h-5 text-rose-500" />
    },
]

const SENSITIVITY_LEVELS = [
    { value: "ALTO", label: "Máximo", desc: "Receba todos os avisos e alertas." },
    { value: "MEDIO", label: "Equilibrado", desc: "Apenas alertas importantes e críticos." },
    { value: "BAIXO", label: "Mínimo", desc: "Apenas alertas críticos de alto risco." },
]

export default function NotificacaoPreferenciasClient() {
    const queryClient = useQueryClient()
    
    const { data: preferencias, isLoading } = useQuery<Preferencia[]>({
        queryKey: ["notificacoes", "preferencias"],
        queryFn: async () => {
            return await apiFetch("/notificacoes/preferencias")
        }
    })

    const mutation = useMutation({
        mutationFn: async ({ tipo, dados }: { tipo: string, dados: Partial<Preferencia> }) => {
            return await apiFetch(`/notificacoes/preferencias/${tipo}`, {
                method: "PATCH",
                body: JSON.stringify(dados)
            })
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["notificacoes", "preferencias"] })
            toast.success("Preferências atualizadas")
        },
        onError: () => {
            toast.error("Erro ao atualizar preferências")
        }
    })

    const getPref = (tipo: string) => {
        return preferencias?.find(p => p.tipo === tipo) || { 
            email_ativo: true, 
            sistema_ativo: true, 
            whatsapp_ativo: false, 
            horario_envio: "07:00", 
            nivel_sensibilidade: "ALTO" 
        }
    }

    const handleChange = (tipo: string, campo: keyof Preferencia, value: any) => {
        const atual = getPref(tipo)
        mutation.mutate({
            tipo,
            dados: {
                ...atual,
                [campo]: value
            }
        })
    }

    if (isLoading) {
        return (
            <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                    <Card key={i} className="opacity-50 animate-pulse">
                        <CardHeader className="h-20 bg-muted/50 rounded-t-lg" />
                        <CardContent className="h-24" />
                    </Card>
                ))}
            </div>
        )
    }

    return (
        <div className="space-y-6 max-w-4xl">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 gap-6">
                {TIPOS_NOTIFICACAO.map(tipo => {
                    const pref = getPref(tipo.id)
                    return (
                        <Card key={tipo.id} className="border-border shadow-sm overflow-hidden">
                            <CardHeader className="flex flex-row items-center space-x-4 space-y-0 pb-4 border-b bg-muted/30">
                                <div className="p-2 bg-background rounded-lg shadow-sm">
                                    {tipo.icon}
                                </div>
                                <div className="flex-1">
                                    <CardTitle className="text-lg">{tipo.titulo}</CardTitle>
                                    <CardDescription>{tipo.desc}</CardDescription>
                                </div>
                            </CardHeader>
                            <CardContent className="pt-6 space-y-8">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                    <div className="space-y-6">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-3">
                                                <Bell className="w-5 h-5 text-muted-foreground" />
                                                <Label htmlFor={`${tipo.id}-sistema`} className="flex flex-col space-y-1 cursor-pointer">
                                                    <span className="font-medium">No sistema</span>
                                                    <span className="text-xs text-muted-foreground">Sino e central de notificações</span>
                                                </Label>
                                            </div>
                                            <Switch
                                                id={`${tipo.id}-sistema`}
                                                checked={pref.sistema_ativo}
                                                onCheckedChange={(c) => handleChange(tipo.id, "sistema_ativo", c)}
                                                disabled={mutation.isPending}
                                            />
                                        </div>

                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-3">
                                                <Mail className="w-5 h-5 text-muted-foreground" />
                                                <Label htmlFor={`${tipo.id}-email`} className="flex flex-col space-y-1 cursor-pointer">
                                                    <span className="font-medium">E-mail</span>
                                                    <span className="text-xs text-muted-foreground">Alertas externos</span>
                                                </Label>
                                            </div>
                                            <Switch
                                                id={`${tipo.id}-email`}
                                                checked={pref.email_ativo}
                                                onCheckedChange={(c) => handleChange(tipo.id, "email_ativo", c)}
                                                disabled={mutation.isPending}
                                            />
                                        </div>
                                        
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-3">
                                                <MessageSquare className="w-5 h-5 text-muted-foreground" />
                                                <Label htmlFor={`${tipo.id}-whatsapp`} className="flex flex-col space-y-1 cursor-pointer">
                                                    <span className="font-medium">WhatsApp</span>
                                                    <span className="text-xs text-muted-foreground">Envio direto (Beta)</span>
                                                </Label>
                                            </div>
                                            <Switch
                                                id={`${tipo.id}-whatsapp`}
                                                checked={pref.whatsapp_ativo}
                                                onCheckedChange={(c) => handleChange(tipo.id, "whatsapp_ativo", c)}
                                                disabled={mutation.isPending}
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-6">
                                        {tipo.id === "RESUMO_DIARIO" && (
                                            <div className="space-y-3">
                                                <Label className="text-sm font-semibold flex items-center gap-2">
                                                    <Clock className="w-4 h-4" /> Horário de Envio
                                                </Label>
                                                <Input 
                                                    type="time" 
                                                    className="w-32 h-10"
                                                    value={pref.horario_envio}
                                                    onChange={(e) => handleChange(tipo.id, "horario_envio", e.target.value)}
                                                    disabled={mutation.isPending}
                                                />
                                                <p className="text-[10px] text-muted-foreground italic">
                                                    Defina o horário preferencial para receber seu briefing diário.
                                                </p>
                                            </div>
                                        )}
                                        <Label className="text-sm font-semibold flex items-center gap-2">
                                            Nível de Sensibilidade
                                        </Label>
                                        <Tabs 
                                            value={pref.nivel_sensibilidade} 
                                            onValueChange={(v) => handleChange(tipo.id, "nivel_sensibilidade", v)}
                                            className="w-full"
                                        >
                                            <TabsList className="grid w-full grid-cols-3 h-10">
                                                {SENSITIVITY_LEVELS.map(level => (
                                                    <TabsTrigger key={level.value} value={level.value} className="text-xs">
                                                        {level.label}
                                                    </TabsTrigger>
                                                ))}
                                            </TabsList>
                                        </Tabs>
                                        <p className="text-[10px] text-muted-foreground italic">
                                            {SENSITIVITY_LEVELS.find(l => l.value === pref.nivel_sensibilidade)?.desc}
                                        </p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    )
                })}
            </div>
        </div>
    )
}
