import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import * as React from "react";
import { expect, test } from "@playwright/test";
import { renderToStaticMarkup } from "react-dom/server";
import { KPICard, type KPICardTone } from "../shared/kpi-card";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  type CardVariant,
} from "./card";

const CARD_VARIANTS: readonly CardVariant[] = [
  "default",
  "muted",
  "info",
  "warning",
  "success",
  "destructive",
  "brand",
];

const KPI_TONES: readonly KPICardTone[] = [
  "default",
  "primary",
  "info",
  "warning",
  "success",
  "destructive",
];

interface PwJsxNode {
  __pw_type: "jsx";
  type:
    | string
    | ((props: Record<string, unknown>) => unknown)
    | { render: (props: Record<string, unknown>, ref: unknown) => unknown };
  props: Record<string, unknown> | null;
  key?: string | number | null;
}

function isPwJsxNode(value: unknown): value is PwJsxNode {
  return (
    typeof value === "object" &&
    value !== null &&
    "__pw_type" in value &&
    (value as { __pw_type?: unknown }).__pw_type === "jsx"
  );
}

function toReactNode(value: unknown): React.ReactNode {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "boolean" || typeof value === "string" || typeof value === "number") {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map((item, index) => {
      const resolved = toReactNode(item);
      if (React.isValidElement(resolved) && resolved.key === null) {
        return React.cloneElement(resolved, { key: index });
      }
      return resolved;
    });
  }
  if (isPwJsxNode(value)) {
    const rawProps = value.props ?? {};
    const { children, ...restProps } = rawProps;
    const resolvedChildren =
      children === undefined ? undefined : toReactNode(children);
    const nextProps: Record<string, unknown> =
      resolvedChildren === undefined
        ? { ...restProps }
        : { ...restProps, children: resolvedChildren };

    if (typeof value.type === "function") {
      return toReactNode(value.type(nextProps));
    }
    if (
      typeof value.type === "object" &&
      value.type !== null &&
      "render" in value.type &&
      typeof value.type.render === "function"
    ) {
      return toReactNode(value.type.render(nextProps, null));
    }
    if (typeof value.type === "string") {
      if (value.key !== undefined && value.key !== null) {
        nextProps.key = value.key;
      }
      return React.createElement(value.type, nextProps);
    }
  }
  if (React.isValidElement(value)) {
    return value;
  }
  return null;
}

function renderTree(element: unknown): string {
  return renderToStaticMarkup(toReactNode(element));
}

function srgbToLinear(channel: number): number {
  const normalized = channel / 255;
  return normalized <= 0.04045
    ? normalized / 12.92
    : Math.pow((normalized + 0.055) / 1.055, 2.4);
}

function relativeLuminance(hexColor: string): number {
  const clean = hexColor.replace("#", "");
  const r = Number.parseInt(clean.slice(0, 2), 16);
  const g = Number.parseInt(clean.slice(2, 4), 16);
  const b = Number.parseInt(clean.slice(4, 6), 16);
  return (
    0.2126 * srgbToLinear(r) +
    0.7152 * srgbToLinear(g) +
    0.0722 * srgbToLinear(b)
  );
}

function contrastRatio(hexA: string, hexB: string): number {
  const l1 = relativeLuminance(hexA);
  const l2 = relativeLuminance(hexB);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

function extractCssBlock(css: string, selector: string): string {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = css.match(new RegExp(`(?:^|\\n)${escaped}\\s*\\{`));
  expect(match?.index, `Bloco CSS '${selector}' não encontrado`).toBeDefined();
  const openBrace = css.indexOf("{", match!.index!);
  expect(openBrace).toBeGreaterThanOrEqual(0);
  let depth = 0;
  for (let i = openBrace; i < css.length; i += 1) {
    if (css[i] === "{") depth += 1;
    else if (css[i] === "}") {
      depth -= 1;
      if (depth === 0) {
        return css.slice(openBrace + 1, i);
      }
    }
  }
  throw new Error(`Chave não fechada no bloco '${selector}'`);
}

function extractTokenValue(block: string, tokenName: string): string {
  const match = block.match(new RegExp(`${tokenName}\\s*:\\s*([^;]+);`));
  expect(match, `Token '${tokenName}' não encontrado no bloco CSS`).not.toBeNull();
  return match![1].trim();
}

function collectTsxFiles(dir: string): string[] {
  const entries = readdirSync(dir);
  const files: string[] = [];
  for (const entry of entries) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      files.push(...collectTsxFiles(full));
    } else if (entry.endsWith(".tsx") && !entry.endsWith(".test.tsx")) {
      files.push(full);
    }
  }
  return files;
}

function extractCardOpeningTags(source: string): string[] {
  const tags: string[] = [];
  const pattern = /<Card(?=\s|>)/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(source)) !== null) {
    let i = match.index + "<Card".length;
    let braceDepth = 0;
    let quote: string | null = null;
    while (i < source.length) {
      const ch = source[i];
      if (quote) {
        if (ch === "\\" && i + 1 < source.length) {
          i += 2;
          continue;
        }
        if (ch === quote) quote = null;
      } else if (ch === '"' || ch === "'" || ch === "`") {
        quote = ch;
      } else if (ch === "{") {
        braceDepth += 1;
      } else if (ch === "}") {
        braceDepth = Math.max(0, braceDepth - 1);
      } else if (ch === ">" && braceDepth === 0) {
        tags.push(source.slice(match.index, i + 1));
        break;
      }
      i += 1;
    }
  }
  return tags;
}

function SampleIcon({ className }: { className?: string }) {
  return <svg aria-hidden="true" className={className} />;
}

test.describe("Card design system contract", () => {
  test("renderiza as 7 variantes semânticas de Card com slots e tokens padronizados", () => {
    const expectedClasses: Record<CardVariant, readonly string[]> = {
      default: ["bg-card", "text-card-foreground"],
      muted: ["bg-muted/40", "text-card-foreground"],
      info: ["border-alert-info-border", "bg-alert-info-bg", "text-alert-info-description"],
      warning: ["border-alert-warning-border", "bg-alert-warning-bg", "text-alert-warning-description"],
      success: ["border-alert-success-border", "bg-alert-success-bg", "text-alert-success-description"],
      destructive: ["border-alert-destructive-border", "bg-alert-destructive-bg", "text-alert-destructive-description"],
      brand: ["border-card-brand-border", "bg-card-brand-bg", "text-card-brand-title"],
    };

    for (const variant of CARD_VARIANTS) {
      const html = renderTree(
        <Card variant={variant}>
          <CardHeader>
            <CardTitle>Título</CardTitle>
            <CardDescription>Descrição</CardDescription>
          </CardHeader>
          <CardContent>Conteúdo</CardContent>
        </Card>
      );

      expect(html).toContain('data-slot="card"');
      expect(html).toContain(`data-variant="${variant}"`);
      expect(html).toContain("rounded-sm");
      expect(html).toContain('data-slot="card-title"');
      expect(html).toContain('data-slot="card-description"');
      expect(html).toContain("text-card-description");
      for (const expectedClass of expectedClasses[variant]) {
        expect(html, `Variante ${variant} deveria incluir ${expectedClass}`).toContain(expectedClass);
      }
    }
  });

  test("globals.css expõe tokens semânticos de Card e protege headings em variantes não neutras", () => {
    const cssPath = resolve(process.cwd(), "src/app/globals.css");
    const css = readFileSync(cssPath, "utf8");

    const themeBlock = extractCssBlock(css, "@theme inline");
    const rootBlock = extractCssBlock(css, ":root");
    const darkBlock = extractCssBlock(css, ".dark");

    expect(themeBlock).toContain("--color-card-title: var(--card-title);");
    expect(themeBlock).toContain("--color-card-description: var(--card-description);");
    expect(themeBlock).toContain("--color-card-brand-bg: var(--card-brand-bg);");
    expect(themeBlock).toContain("--color-card-brand-border: var(--card-brand-border);");
    expect(themeBlock).toContain("--color-card-brand-title: var(--card-brand-title);");
    expect(themeBlock).toContain("--color-card-brand-description: var(--card-brand-description);");

    for (const token of [
      "--card-brand-bg",
      "--card-brand-border",
      "--card-brand-title",
      "--card-brand-description",
    ]) {
      expect(rootBlock).toContain(`${token}:`);
      expect(darkBlock).toContain(`${token}:`);
    }

    for (const variant of ["info", "warning", "success", "destructive", "brand"] as const) {
      expect(css).toContain(`[data-slot="card"][data-variant="${variant}"]`);
    }
    expect(css).toContain(':where(h1, h2, h3, h4, h5, h6)');
    expect(css).toContain('[data-slot="card-title"]');
  });

  test("paleta light e dark do Card variante brand atende contraste WCAG AA (>= 4.5:1)", () => {
    const cssPath = resolve(process.cwd(), "src/app/globals.css");
    const css = readFileSync(cssPath, "utf8");

    const rootBlock = extractCssBlock(css, ":root");
    const darkBlock = extractCssBlock(css, ".dark");

    for (const [mode, block] of [
      ["light", rootBlock],
      ["dark", darkBlock],
    ] as const) {
      const bg = extractTokenValue(block, "--card-brand-bg");
      const title = extractTokenValue(block, "--card-brand-title");
      const description = extractTokenValue(block, "--card-brand-description");

      expect(
        contrastRatio(title, bg),
        `${mode} brand title (${title} on ${bg})`
      ).toBeGreaterThanOrEqual(4.5);
      expect(
        contrastRatio(description, bg),
        `${mode} brand description (${description} on ${bg})`
      ).toBeGreaterThanOrEqual(4.5);
    }
  });

  test("KPICard suporta tones semânticos com rounded-sm e preserva compatibilidade retroativa", () => {
    for (const tone of KPI_TONES) {
      const html = renderTree(
        <KPICard
          label="Indicador"
          value="R$ 100,00"
          subtitle="Detalhe"
          icon={SampleIcon}
          tone={tone}
          valueTone={tone}
          highlightBorder={tone !== "default"}
        />
      );

      expect(html).not.toContain("rounded-lg");
      expect(html).toContain("rounded-sm");
      if (tone === "info" || tone === "warning" || tone === "success" || tone === "destructive") {
        expect(html).toContain(`bg-alert-${tone}-bg`);
        expect(html).toContain(`text-alert-${tone}-icon`);
        expect(html).toContain(`border-alert-${tone}-border`);
      }
    }

    const legacyHtml = renderTree(
      <KPICard
        label="Legado"
        value={10}
        icon={SampleIcon}
        iconBg="bg-primary/10"
        iconColor="text-primary"
      />
    );
    expect(legacyHtml).toContain("bg-primary/10");
    expect(legacyHtml).toContain("text-primary");
    expect(legacyHtml).not.toContain("rounded-lg");
  });

  test("nenhum <Card> usa background apenas light sem equivalente dark:", () => {
    const srcRoot = resolve(process.cwd(), "src");
    const tsxFiles = collectTsxFiles(srcRoot);
    const lightBgPattern =
      /(?<!dark:)\bbg-(?:white|(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(?:50|100|200))(?:\/\d+)?\b/;

    const violations: string[] = [];
    for (const file of tsxFiles) {
      const content = readFileSync(file, "utf8");
      const tags = extractCardOpeningTags(content);
      for (const tag of tags) {
        if (lightBgPattern.test(tag) && !/\bdark:bg-/.test(tag)) {
          violations.push(`${file.replace(`${srcRoot}/`, "")}: ${tag}`);
        }
      }
    }

    expect(violations).toEqual([]);
  });

  test("nenhum <Card> viola rounded-sm ou usa fundo sólido manual bg-emerald/green/primary sem variante semântica", () => {
    const srcRoot = resolve(process.cwd(), "src");
    const tsxFiles = collectTsxFiles(srcRoot);
    const nonSmRadiusPattern = /\brounded-(?:md|lg|xl|2xl|3xl|full)\b/;
    const solidGreenPattern = /\bbg-(?:emerald|green)-(?:600|700|800|900)\b/;
    const primarySolidPattern = /\bbg-primary\b(?![/-])/;
    const whiteTextPattern = /\b(?:text-primary-foreground|text-white)\b/;

    const violations: string[] = [];
    for (const file of tsxFiles) {
      const content = readFileSync(file, "utf8");
      const tags = extractCardOpeningTags(content);
      for (const tag of tags) {
        if (
          nonSmRadiusPattern.test(tag) ||
          solidGreenPattern.test(tag) ||
          (primarySolidPattern.test(tag) && whiteTextPattern.test(tag))
        ) {
          violations.push(`${file.replace(`${srcRoot}/`, "")}: ${tag}`);
        }
      }
    }

    expect(violations).toEqual([]);
  });
});
