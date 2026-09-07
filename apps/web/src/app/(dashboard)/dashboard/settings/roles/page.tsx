import { apiFetchServer } from "@/lib/api-server";
import { RolesClient } from "./RolesClient";
import type { TenantRoleProfile } from "@/types/global";

export default async function RolesPage() {
    let initialRoles: TenantRoleProfile[] = [];

    try {
        initialRoles = await apiFetchServer<TenantRoleProfile[]>("/team/roles");
    } catch (e) {
        // ignora
    }

    return <RolesClient initialRoles={initialRoles} />;
}
