// Redirecionamento para nova rota canônica de propriedades
import { redirect } from "next/navigation";

export default function FazendasRedirectPage() {
    redirect("/dashboard/settings/propriedades");
}
