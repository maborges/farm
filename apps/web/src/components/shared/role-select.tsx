// components/shared/role-select.tsx
// Seletor de perfis de acesso reutilizável

"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import {
    Select, SelectContent, SelectItem,
    SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import type { TenantRoleProfile } from "@/types/global";
import { apiFetch } from "@/lib/api";

interface RoleSelectProps {
    /** Valor selecionado (role ID) */
    value?: string;
    /** Callback chamado quando a seleção muda */
    onChange?: (roleId: string) => void;
    /** Se deve desabilitar o select */
    disabled?: boolean;
    /** Placeholder personalizado */
    placeholder?: string;
    /** Se deve incluir apenas roles customizadas */
    customOnly?: boolean;
}

/**
 * Componente de seleção de perfis de acesso.
 * Carrega dinamicamente a lista de roles disponíveis.
 */
export function RoleSelect({
    value,
    onChange,
    disabled,
    placeholder = "Selecione um perfil...",
    customOnly = false,
}: RoleSelectProps) {
    const [roles, setRoles] = useState<TenantRoleProfile[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchRoles = async () => {
            try {
                const data = await apiFetch<TenantRoleProfile[]>("/team/roles");
                const filtered = customOnly ? data.filter((r) => r.is_custom) : data;
                setRoles(filtered);
            } finally {
                setLoading(false);
            }
        };

        fetchRoles();
    }, [customOnly]);

    if (loading) {
        return (
            <Select disabled={true}>
                <SelectTrigger>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Carregando perfis...
                </SelectTrigger>
            </Select>
        );
    }

    return (
        <Select value={value} onValueChange={onChange} disabled={disabled}>
            <SelectTrigger>
                <SelectValue placeholder={placeholder} />
            </SelectTrigger>
            <SelectContent>
                {roles.map((role) => (
                    <SelectItem key={role.id} value={role.id}>
                        <div className="flex items-center gap-2">
                            <span>{role.nome}</span>
                            {role.is_custom && (
                                <Badge variant="outline" className="text-[9px] ml-1">
                                    Customizado
                                </Badge>
                            )}
                        </div>
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}
