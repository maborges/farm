import { expect, test } from '@playwright/test';

import { isErpPeopleManaged } from './erp-person-governance';

test('mantém o cadastro local quando não existe ERP configurado', () => {
  expect(isErpPeopleManaged({ configurado: false }, [])).toBe(false);
});

test('governa pessoas pelo ERP quando o recurso está habilitado', () => {
  expect(isErpPeopleManaged(
    { configurado: true },
    [{ feature_code: 'pessoas', feature_enabled: true, ativa: true }],
  )).toBe(true);
  expect(isErpPeopleManaged(
    { configurado: true },
    [{ feature_code: 'pessoas', feature_enabled: true, ativa: false }],
  )).toBe(true);
  expect(isErpPeopleManaged(
    { configurado: true },
    [{ feature_code: 'pessoas', feature_enabled: false, ativa: true }],
  )).toBe(false);
});
