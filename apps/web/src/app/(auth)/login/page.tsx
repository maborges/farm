import { LoginForm } from "@/components/auth/login-form";
import { AuthLayout } from "@/components/auth/auth-layout";

export default function LoginPage() {
    return (
        <AuthLayout
            badgeLabel="Conformidade & Rastreabilidade"
            title="Rastreabilidade e conformidade digital."
            description="Comprove polígonos GeoJSON de desmatamento zero (EUDR), controle calibrações técnicas e registre entregas de EPI com assinatura offline diretamente no passaporte do lote comercial."
            stats={[
                { value: "100%", label: "Conformidade EUDR" },
                { value: "Offline", label: "Assinaturas Canvas" },
                { value: "SHA-256", label: "Passaporte Seguro" },
            ]}
        >
            <LoginForm />
        </AuthLayout>
    );
}
