import { redirect } from "next/navigation";

/**
 * Grupos de Fazendas foram removidos do sistema.
 * Redireciona para a página de Propriedades.
 */
export default function GruposPage() {
    redirect("/dashboard/settings/propriedades");
}
