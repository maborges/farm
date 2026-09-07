import NotificacaoPreferenciasClient from "./client";

export default function NotificacoesPreferenciasPage() {
    return (
        <div className="flex flex-col gap-6 p-6">
            <div>
                <h1 className="text-2xl font-bold tracking-tight">Preferências de Notificação</h1>
                <p className="text-muted-foreground">
                    Escolha como deseja ser notificado sobre eventos importantes da sua safra.
                </p>
            </div>
            <NotificacaoPreferenciasClient />
        </div>
    );
}
