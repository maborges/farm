import type { Metadata } from "next";

import { AuthLayout } from "@/components/auth/auth-layout";
import { DemoRequestForm } from "@/components/auth/demo-request-form";

export const metadata: Metadata = {
    title: "Demonstração | DeepFarms Gestão",
    description:
        "Solicite acesso ao ambiente de demonstração do DeepFarms Gestão para explorar módulos agrícolas, pecuários, estoque e financeiro.",
};

const DEMO_STEPS = [
    {
        step: "01",
        title: "Informe seus dados",
        desc: "Preencha seu nome e e-mail para liberar o acesso de visitante",
    },
    {
        step: "02",
        title: "Confirme pelo e-mail",
        desc: "Receba o link de acesso ou confirmação caso já tenha conta na plataforma",
    },
    {
        step: "03",
        title: "Explore por 15 dias",
        desc: "Navegue pelos dashboards e relatórios em modo somente consulta",
    },
];

export default function DemonstracaoPage() {
    return (
        <AuthLayout
            badgeLabel="Ambiente de Demonstração"
            title={
                <>
                    Veja o DeepFarms{" "}
                    <span className="font-semibold text-primary">funcionando na prática.</span>
                </>
            }
            description="Explore uma fazenda modelo com safra, estoque, frota e financeiro integrados antes de iniciar sua assinatura."
            steps={DEMO_STEPS}
            guaranteeText="Sem cartão de crédito · Acesso imediato por 15 dias · Modo somente consulta"
            contentMaxWidthClassName="max-w-[520px]"
        >
            <DemoRequestForm />
        </AuthLayout>
    );
}
