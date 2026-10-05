import re

with open("apps/web/src/components/layout/app-sidebar.tsx", "r") as f:
    content = f.read()

# Add import
import_stmt = "import { useVisibleNavigation } from \"@/hooks/use-visible-navigation\";\n"
content = content.replace("import { ModuleGate } from \"../shared/module-gate\";", import_stmt + "import { ModuleGate } from \"../shared/module-gate\";")

# Replace active module/section hooks
content = re.sub(
    r"const activePlanTier = useAppStore\(\(state\) => state.activePlanTier\(\)\);\s*// ── Unified toggle state ───────────────────────────────────────────────",
    """const activePlanTier = useAppStore((state) => state.activePlanTier());
    
    const { moduleGroups, coreSections, backofficeSections, activeModule, activeSection, activeBackofficeSection } = useVisibleNavigation();

    // ── Unified toggle state ───────────────────────────────────────────────""",
    content
)

# Remove old canSeeTenantItem and canSeeBackofficeItem and searchGroups and filteredSearchGroups and old uses.
# Actually it's easier to just do it via sed or Python regex.

# We will just replace searchGroups implementation
search_groups_regex = r"const searchGroups = useMemo\(\(\) => \{.*?\n    \}, \[activePlanTier, accessItems, canSeeBackofficeItem, settingsItems, user\]\);"

new_search_groups = """const searchGroups = useMemo(() => {
        const coreItems = coreSections.flatMap((section) =>
            section.items.map((item) => ({
                ...item,
                group: "Cadastros",
                section: section.label,
            }))
        );

        const modGroups = moduleGroups.map((moduleGroup) => ({
            moduleId: moduleGroup.moduleId,
            key: moduleGroup.key,
            label: moduleGroup.label,
            items: moduleGroup.sections.flatMap((section) =>
                section.items.map((item) => ({
                    ...item,
                    group: moduleGroup.label,
                    section: section.label,
                    moduleId: section.moduleId ?? moduleGroup.moduleId,
                    activeClassName: moduleActive[moduleGroup.key as keyof typeof moduleActive],
                }))
            ),
        }));

        const backofficeItems = backofficeSections.flatMap((section) =>
            section.items.map((item) => ({
                ...item,
                group: "Administração SaaS",
                section: section.label,
                activeClassName: backofficeActive,
            }))
        );

        return {
            coreItems,
            moduleGroups: modGroups,
            backofficeItems,
            accessItems: accessItems.map((item) => ({
                ...item,
                group: "Gestão de Acessos",
            })) satisfies SearchableItem[],
            settingsItems: settingsItems.map((item) => ({
                ...item,
                group: "Configurações",
            })) satisfies SearchableItem[],
        };
    }, [coreSections, moduleGroups, backofficeSections, accessItems, settingsItems]);"""

content = re.sub(search_groups_regex, new_search_groups, content, flags=re.DOTALL)

# Now remove canSeeBackofficeItem declaration
content = re.sub(r"const canSeeBackofficeItem = useCallback\(\(permission\?: string\) => \{.*?\}, \[user\?\.is_superuser, user\?\.role\]\);\n\n", "", content, flags=re.DOTALL)

# Now remove canSeeTenantItem function declaration at module level
content = re.sub(r"function canSeeTenantItem\(.*?\}\n\nexport function AppSidebar", "export function AppSidebar", content, flags=re.DOTALL)

# Replace CORE_CADASTROS map
content = re.sub(r"\{\/\* CORE — Cadastros e Tabelas Compartilhadas \(visível se sobrar ao menos 1 item liberado\) \*\/.*?\{CORE_CADASTROS\.some\(\(section\) =>.*?\&\& \(", "{/* CORE — Cadastros e Tabelas Compartilhadas */}\n                                        {coreSections.length > 0 && (", content, flags=re.DOTALL)

# Replace CORE_CADASTROS.map inside
content = content.replace("CORE_CADASTROS.map((section)", "coreSections.map((section)")
content = re.sub(r"\{section\.items\s*\.filter\(\(item\) =>\s*\(!item\.minimumTier \|\| tierAtLeast\(activePlanTier, item\.minimumTier\)\) &&\s*canSeeTenantItem\(user, item\.permission\)\s*\)\s*\.map\(\(item\) => \(", "{section.items.map((item) => (", content, flags=re.DOTALL)

# Replace MODULOS_OPERACIONAIS
content = re.sub(r"\{\/\* Módulos Operacionais — renderizados do sidebar-config \*\/.*?MODULOS_OPERACIONAIS\.filter\(\(moduleGroup\) =>.*?canSeeTenantItem\(user, item\.permission\).*?\)\s*\)\s*\)\s*\.map\(\(moduleGroup\) => \{", "{/* Módulos Operacionais */}\n                                        {moduleGroups.map((moduleGroup) => {", content, flags=re.DOTALL)

# Replace section.items.filter inside modules
content = re.sub(r"\{section\.items\s*\.filter\(\(item\) =>\s*\(!item\.minimumTier \|\| tierAtLeast\(activePlanTier, item\.minimumTier\)\) &&\s*canSeeTenantItem\(user, item\.permission\)\s*\)\s*\.map\(\(item\) => \(", "{section.items.map((item) => (", content, flags=re.DOTALL)


with open("apps/web/src/components/layout/app-sidebar.tsx", "w") as f:
    f.write(content)
