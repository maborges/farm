import { apiFetchServer } from "@/lib/api-server";
import { DepartamentosClient, Departamento } from "./DepartamentosClient";
import { PageHeader } from "@/components/shared/page-header";
import { Landmark } from "lucide-react";

export default async function DepartamentosPage() {
    // Busca no servidor antes de enviar HTML ao cliente
    const departamentos = await apiFetchServer<Departamento[]>("/rh/departamentos");
    return (
        <DepartamentosClient initialData={departamentos} />
    );
}
