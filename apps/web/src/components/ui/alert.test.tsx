import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import * as React from "react";
import { expect, test } from "@playwright/test";
import { renderToStaticMarkup } from "react-dom/server";
import { Alert, AlertDescription, AlertTitle, type AlertVariant } from "./alert";

const VARIANTS: readonly AlertVariant[] = [
  "default",
  "info",
  "warning",
  "success",
  "destructive",
];

const TOKEN_FIELDS = ["bg", "border", "title", "description", "icon"] as const;

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
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "string" || typeof value === "number") {
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

function renderAlertTree(element: unknown): string {
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
    } else if (entry.endsWith(".tsx")) {
      files.push(full);
    }
  }
  return files;
}

function extractAlertOpeningTags(source: string): string[] {
  const tags: string[] = [];
  const pattern = /<Alert(?=\s|>)/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(source)) !== null) {
    let i = match.index + "<Alert".length;
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

test.describe("Alert design system contract", () => {
  test("renderiza as 5 variantes semânticas com classes e atributos padronizados", () => {
    for (const variant of VARIANTS) {
      const html = renderAlertTree(
        <Alert variant={variant}>
          <svg aria-hidden="true" />
          <AlertTitle>Título</AlertTitle>
          <AlertDescription>Descrição</AlertDescription>
        </Alert>
      );

      expect(html).toContain('role="alert"');
      expect(html).toContain('data-slot="alert"');
      expect(html).toContain(`data-variant="${variant}"`);
      expect(html).toContain("rounded-sm");
      expect(html).toContain(`bg-alert-${variant}-bg`);
      expect(html).toContain(`border-alert-${variant}-border`);
      expect(html).toContain(`[&amp;&gt;svg]:text-alert-${variant}-icon`);
      expect(html).toContain("[&amp;&gt;svg]:size-4");
    }
  });

  test("AlertTitle e AlertDescription preservam data-slot e tokens mesmo dentro de wrapper div", () => {
    const html = renderAlertTree(
      <Alert variant="warning">
        <div className="flex items-start justify-between">
          <div>
            <AlertTitle>Aviso interno</AlertTitle>
            <AlertDescription>Texto dentro de wrapper</AlertDescription>
          </div>
        </div>
      </Alert>
    );

    expect(html).toContain('data-slot="alert-title"');
    expect(html).toContain("text-alert-title");
    expect(html).toContain('data-slot="alert-description"');
    expect(html).toContain("text-alert-description");
  });

  test("permite sobrescrever role padrão para role='status'", () => {
    const html = renderAlertTree(
      <Alert variant="info" role="status">
        <AlertDescription>Status informativo</AlertDescription>
      </Alert>
    );

    expect(html).toContain('role="status"');
    expect(html).not.toContain('role="alert"');
  });

  test("globals.css expõe todos os tokens em :root, .dark, @theme inline e bindings de data-variant", () => {
    const cssPath = resolve(process.cwd(), "src/app/globals.css");
    const css = readFileSync(cssPath, "utf8");

    const themeBlock = extractCssBlock(css, "@theme inline");
    const rootBlock = extractCssBlock(css, ":root");
    const darkBlock = extractCssBlock(css, ".dark");

    expect(themeBlock).toContain("--color-alert-title: var(--alert-title);");
    expect(themeBlock).toContain("--color-alert-description: var(--alert-description);");

    for (const variant of VARIANTS) {
      for (const field of TOKEN_FIELDS) {
        const token = `--alert-${variant}-${field}`;
        expect(themeBlock).toContain(`--color-alert-${variant}-${field}: var(${token});`);
        expect(rootBlock).toContain(`${token}:`);
        expect(darkBlock).toContain(`${token}:`);
      }

      expect(css).toContain(`[data-slot="alert"][data-variant="${variant}"]`);
    }
  });

  test("paleta light e dark atende contraste mínimo WCAG AA (>= 4.5:1) para título, descrição e ícone", () => {
    const cssPath = resolve(process.cwd(), "src/app/globals.css");
    const css = readFileSync(cssPath, "utf8");

    const rootBlock = extractCssBlock(css, ":root");
    const darkBlock = extractCssBlock(css, ".dark");

    for (const [mode, block] of [
      ["light", rootBlock],
      ["dark", darkBlock],
    ] as const) {
      for (const variant of VARIANTS) {
        const bg = extractTokenValue(block, `--alert-${variant}-bg`);
        const title = extractTokenValue(block, `--alert-${variant}-title`);
        const description = extractTokenValue(block, `--alert-${variant}-description`);
        const icon = extractTokenValue(block, `--alert-${variant}-icon`);

        expect(
          contrastRatio(title, bg),
          `${mode} ${variant} title (${title} on ${bg})`
        ).toBeGreaterThanOrEqual(4.5);
        expect(
          contrastRatio(description, bg),
          `${mode} ${variant} description (${description} on ${bg})`
        ).toBeGreaterThanOrEqual(4.5);
        expect(
          contrastRatio(icon, bg),
          `${mode} ${variant} icon (${icon} on ${bg})`
        ).toBeGreaterThanOrEqual(4.5);
      }
    }
  });

  test("nenhum <Alert> no app usa overrides manuais de paleta e /agricola/fenologia usa variant='warning'", () => {
    const srcRoot = resolve(process.cwd(), "src");
    const tsxFiles = collectTsxFiles(srcRoot);
    const manualColorPattern =
      /\b(?:bg|text|border)-(?:amber|yellow|sky|blue|emerald|green|red|orange|rose|violet)-/;

    const violations: string[] = [];
    for (const file of tsxFiles) {
      const content = readFileSync(file, "utf8");
      const tags = extractAlertOpeningTags(content);
      for (const tag of tags) {
        if (manualColorPattern.test(tag)) {
          violations.push(`${file.replace(`${srcRoot}/`, "")}: ${tag}`);
        }
      }
    }

    expect(violations).toEqual([]);

    const fenologiaPath = resolve(srcRoot, "app/(dashboard)/agricola/fenologia/page.tsx");
    const fenologiaContent = readFileSync(fenologiaPath, "utf8");
    expect(fenologiaContent).toContain('<Alert variant="warning">');
  });
});
