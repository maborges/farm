import { redirect } from "next/navigation";

export default async function ContasPagarPage() {
    redirect("/dashboard/financeiro/despesas");
}
