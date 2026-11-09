import { RegisterForm } from "@/components/auth/register-form";
import { AuthLayout } from "@/components/auth/auth-layout";

const STEPS = [
    { step: "01", title: "Simule sua assinatura", desc: "Informe área e acessos para ver o valor exato na hora" },
    { step: "02", title: "Dados de cadastro", desc: "Identifique o produtor rural e crie seu acesso" },
    { step: "03", title: "Confirme e comece", desc: "100% dos módulos liberados com 14 dias grátis" },
];

export default function RegisterPage() {
    return (
        <AuthLayout
            badgeLabel="Solicitar Acesso"
            title={
                <>
                    A nova era da{" "}
                    <span className="text-primary font-semibold">produtividade</span>{" "}
                    rural.
                </>
            }
            description="Simule sua operação com transparência total e gerencie sua fazenda com dados reais, mapas precisos e 100% dos módulos liberados."
            steps={STEPS}
            highlightNotice={{
                title: "Política de Preço 100% Transparente",
                text: (
                    <>
                        Todos os pacotes incluem <strong>100% dos módulos nativos</strong> (as extensões IoT e ERP são opcionais e contratadas à parte). O valor é calculado pela sua{" "}
                        <strong>área produtiva equivalente</strong> (Reserva Legal e APP são 100% isentas) e pelos{" "}
                        <strong>acessos simultâneos Web</strong> (o App Campo no celular é gratuito e ilimitado).
                    </>
                ),
            }}
            guaranteeText="Sem cartão de crédito · 14 dias grátis · Cancele quando quiser"
            contentMaxWidthClassName="max-w-[820px] xl:max-w-[880px]"
            cardClassName="p-6 lg:p-7"
        >
            <RegisterForm />
        </AuthLayout>
    );
}
