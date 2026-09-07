import { apiFetchServer } from "@/lib/api-server";
import { ListaCarClient, RegistroCAR } from "./ListaCarClient";

export default async function ListaCarPage() {
    const cars = await apiFetchServer<RegistroCAR[]>("/ambiental/car");
    return <ListaCarClient initialData={cars} />;
}
