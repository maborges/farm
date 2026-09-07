import {
  MODULOS_OPERACIONAIS,
  BACKOFFICE_SECTIONS,
  type SidebarMenuItem,
} from "./sidebar-config";

// ─── Types ───────────────────────────────────────────────────────────────────

export type SidebarModuleKey =
  | "A1"
  | "P1"
  | "F1"
  | "O1"
  | "O1-FROTA"
  | "RH"
  | "RH2"
  | "AM1"
  | "I1"
  | "C1"
  | "IA1"
  | "CAMPO"
  | "CADASTROS"
  | "";

/**
 * Represents the toggle state of a sidebar node.
 * - "auto": no manual override — resolved by route matching
 * - "open": explicitly opened by the user
 * - "closed": explicitly closed by the user
 */
export type ToggleState = "auto" | "open" | "closed";

// ─── Module Path Mapping ─────────────────────────────────────────────────────

const MODULE_PATHS: ReadonlyArray<readonly [string, SidebarModuleKey]> = [
  ["/dashboard/operacional/campo", "CAMPO"],
  ["/dashboard/operacional/frota", "O1-FROTA"],
  ["/operacional", "O1-FROTA"],
  ["/suprimentos", "O1"],
  ["/dashboard/inteligencia-operacional", "IA1"],
  ["/dashboard/ia", "IA1"],
  ["/dashboard/pecuaria/clima", "C1"],
  ["/dashboard/pecuaria", "P1"],
  ["/dashboard/financeiro", "F1"],
  ["/dashboard/rh/seguranca", "RH2"],
  ["/dashboard/rh", "RH"],
  ["/dashboard/ambiental", "AM1"],
  ["/dashboard/certificacoes-esg", "AM1"],
  ["/cadastros/imoveis", "I1"],
  ["/cadastros", "CADASTROS"],
  ["/dashboard/agricola/clima", "C1"],
  ["/dashboard/agricola", "A1"],
  ["/agricola", "A1"],
];

/**
 * Returns the sidebar module key for a given pathname.
 * Ordered from most-specific to least-specific prefix so the first match wins.
 */
export function getSidebarModuleFromPath(pathname: string): SidebarModuleKey {
  return MODULE_PATHS.find(([prefix]) => pathname.startsWith(prefix))?.[1] ?? "";
}

export const SIDEBAR_MODULE_PATH_GUARDRAILS = MODULE_PATHS;

// ─── Route Specificity Resolver ──────────────────────────────────────────────

/**
 * Counts the number of segments in a pathname.
 * @example countSegments("/agricola/operacoes") // 2
 */
function countSegments(path: string): number {
  return path.split("/").filter(Boolean).length;
}

/**
 * Separates a href into pathname and search params.
 * @example splitHref("/agricola/safras?redirect=orcamento")
 *   // { path: "/agricola/safras", params: URLSearchParams { redirect: "orcamento" } }
 */
function splitHref(href: string): { path: string; params: URLSearchParams } {
  const questionMark = href.indexOf("?");
  if (questionMark === -1) {
    return { path: href, params: new URLSearchParams() };
  }
  return {
    path: href.slice(0, questionMark),
    params: new URLSearchParams(href.slice(questionMark + 1)),
  };
}

/**
 * Checks if a pathname matches a candidate href by prefix.
 *
 * A prefix match means the pathname starts with the candidate path AND
 * either equals it exactly or is followed by a "/" (segment boundary).
 * This prevents "/agricola" from matching "/agricola-xyz".
 */
function isPathPrefixMatch(pathname: string, candidatePath: string): boolean {
  if (pathname === candidatePath) return true;
  return (
    pathname.startsWith(candidatePath) &&
    (candidatePath.endsWith("/") || pathname[candidatePath.length] === "/")
  );
}

/**
 * Checks if search params from a candidate href match the current search params.
 * Only params present in the candidate are checked — extra params in the URL are ignored.
 */
function searchParamsMatch(
  candidateParams: URLSearchParams,
  currentParams: URLSearchParams
): boolean {
  for (const [key, value] of candidateParams.entries()) {
    if (currentParams.get(key) !== value) return false;
  }
  return true;
}

interface MatchCandidate {
  href: string;
  key: string;
}

/**
 * Resolves the most specific match from a list of candidates.
 *
 * Algorithm:
 * 1. For each candidate, split href into path + query params.
 * 2. Check prefix match on path.
 * 3. If candidate has query params, also check param match.
 * 4. Score by segment count (more segments = more specific).
 * 5. Prefer candidates with query param match over those without.
 * 6. Return the most specific candidate key, or null.
 *
 * @param pathname - Current pathname (from usePathname)
 * @param currentSearchParams - Current search params (from useSearchParams)
 * @param candidates - List of { href, key } pairs to match against
 * @returns The key of the most specific match, or null
 */
export function resolveMostSpecificMatch(
  pathname: string,
  currentSearchParams: URLSearchParams,
  candidates: ReadonlyArray<MatchCandidate>
): string | null {
  let bestKey: string | null = null;
  let bestScore = -1;
  let bestHasQueryMatch = false;

  for (const candidate of candidates) {
    const { path: candidatePath, params: candidateParams } = splitHref(candidate.href);

    if (!isPathPrefixMatch(pathname, candidatePath)) continue;

    const hasQueryParams = candidateParams.toString().length > 0;
    const queryMatches = hasQueryParams
      ? searchParamsMatch(candidateParams, currentSearchParams)
      : false;

    // Skip candidates with query params that don't match
    if (hasQueryParams && !queryMatches) continue;

    const score = countSegments(candidatePath);

    // Prefer: (1) higher segment count, (2) query match over no query
    const isBetter =
      score > bestScore ||
      (score === bestScore && queryMatches && !bestHasQueryMatch);

    if (isBetter) {
      bestKey = candidate.key;
      bestScore = score;
      bestHasQueryMatch = queryMatches;
    }
  }

  return bestKey;
}

// ─── Active Section Resolvers ────────────────────────────────────────────────

/**
 * Returns the active section key within a module, using specificity-based matching.
 * Replaces the old getActiveSection() which depended on config order.
 */
export function getActiveSectionFromPath(
  moduleKey: string,
  pathname: string,
  currentSearchParams: URLSearchParams
): string {
  const moduleGroup = MODULOS_OPERACIONAIS.find((m) => m.key === moduleKey);
  if (!moduleGroup) return "";

  const candidates: MatchCandidate[] = moduleGroup.sections.flatMap((section) =>
    section.items.map((item) => ({ href: item.href, key: section.key }))
  );

  return resolveMostSpecificMatch(pathname, currentSearchParams, candidates) ?? "";
}

/**
 * Returns the active backoffice section key, using specificity-based matching.
 * Replaces the old getActiveBackofficeSection().
 */
export function getActiveBackofficeSectionFromPath(
  pathname: string
): string | null {
  const candidates: MatchCandidate[] = BACKOFFICE_SECTIONS.flatMap((section) =>
    section.items.map((item) => ({ href: item.href, key: section.key }))
  );

  return resolveMostSpecificMatch(
    pathname,
    new URLSearchParams(),
    candidates
  );
}

// ─── Leaf Item Active Matcher ────────────────────────────────────────────────

/**
 * Determines if a leaf sidebar item is currently active.
 *
 * Rules:
 * 1. If the item href contains a query string, match pathname + query params.
 * 2. For exact static routes: pathname === item path.
 * 3. For dynamic routes (e.g., /agricola/safras/[id]/tarefas):
 *    pathname starts with item path and is followed by "/" (segment boundary).
 *
 * @param itemHref - The href from sidebar config (may include query string)
 * @param pathname - Current pathname from usePathname()
 * @param currentSearchParams - Current search params from useSearchParams()
 * @returns Whether this item should be highlighted as active
 */
export function isItemActive(
  itemHref: string,
  pathname: string,
  currentSearchParams: URLSearchParams,
  exact?: boolean
): boolean {
  const { path: itemPath, params: itemParams } = splitHref(itemHref);
  const hasQueryParams = itemParams.toString().length > 0;

  if (hasQueryParams) {
    // Must match both pathname and query params
    return pathname === itemPath && searchParamsMatch(itemParams, currentSearchParams);
  }

  // Exact match
  if (pathname === itemPath) return true;

  if (exact) return false;

  // Dynamic route match: pathname extends the item path at a segment boundary
  return (
    pathname.startsWith(itemPath) &&
    itemPath.length > 1 &&
    pathname[itemPath.length] === "/"
  );
}

// ─── Toggle State Helpers ────────────────────────────────────────────────────

/**
 * Resolves whether a node should be open, given its manual toggle state
 * and whether the route indicates it should auto-expand.
 *
 * Precedence:
 * 1. "closed" manual → always closed
 * 2. "open" manual → always open
 * 3. "auto" + route match → open
 * 4. "auto" + no match → closed
 */
export function resolveToggle(
  toggle: ToggleState | undefined,
  isActiveByRoute: boolean
): boolean {
  const state = toggle ?? "auto";
  if (state === "closed") return false;
  if (state === "open") return true;
  return isActiveByRoute;
}
