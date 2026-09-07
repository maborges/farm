import { expect, test } from "@playwright/test";

import { getSupportedErpProviders } from "./erp-provider-selector";

test("remove providers sem console e slugs repetidos do seletor ERP", () => {
  const providers = getSupportedErpProviders([
    { id: 1, nome: "Sankhya", slug: "sankhya", descricao: null, logo_url: null },
    { id: 2, nome: "Sankhya fixture", slug: "sankhya-fixture", descricao: null, logo_url: null },
    { id: 3, nome: "Sankhya duplicado", slug: "sankhya", descricao: null, logo_url: null },
  ]);

  expect(providers.map((provider) => provider.id)).toEqual([1]);
});
