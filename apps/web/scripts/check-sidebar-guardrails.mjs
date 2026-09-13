import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const sidebarPath = resolve("src/components/layout/app-sidebar.tsx");
const source = await readFile(sidebarPath, "utf8");

const checks = [
  ["itens do menu preservam o tooltip contextual", (text) => (text.match(/title=\{item\.tip\}/g) ?? []).length >= 3],
  ["itens do menu preservam a rota ativa", (text) => text.includes("isItemActive(item.href, pathname, searchParams, item.exact)")],
  ["itens do menu usam Link para navegação", (text) => text.includes("render={<Link href={item.href} onClick={handleNavigation} />}")],
  ["não reintroduz o toggle independente de subseções", (text) => !text.includes("sectionToggle") && !text.includes("handleSectionToggle")],
];

const failures = checks.filter(([, check]) => !check(source)).map(([description]) => description);

if (failures.length > 0) {
  console.error("Sidebar guardrails failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`Sidebar guardrails passed (${checks.length} checks).`);
