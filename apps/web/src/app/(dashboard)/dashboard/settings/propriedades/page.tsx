// Redirecionamento: /dashboard/settings/propriedades → /cadastros/propriedades
// O cadastro de propriedades rurais foi movido para Cadastros.
import { redirect } from "next/navigation";

export default function PropriedadesRedirectPage() {
    redirect("/cadastros/propriedades");
}
