const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');

const filename = path.join(__dirname, '../src/lib/permissions.ts');
const source = fs.readFileSync(filename, 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
const result = { exports: {} };
new Function('exports', 'module', 'require', compiled)(result.exports, result, require);
const { hasTenantPermission } = result.exports;
const ownerLegacyPermissions = { agricola: 'write', operacional: 'write' };
assert.equal(hasTenantPermission('owner', 'imoveis:propriedades:view', ownerLegacyPermissions), true);
assert.equal(hasTenantPermission('owner', 'estoque:saldo:view', ownerLegacyPermissions), true);
assert.equal(hasTenantPermission('gerente', 'imoveis:propriedades:view', ownerLegacyPermissions), false);
console.log('Permissões do proprietário e de perfis limitados verificadas.');
