import { z } from 'zod';

const decimal = z.string().trim().regex(/^\d+(?:[.,]\d{1,4})?$/, 'Informe um número positivo, sem separador de milhar.');
export const notaFiscalItemSchema = z.object({
  descricao: z.string().trim().min(1, 'Informe o produto.').max(300),
  ncm: z.string().regex(/^$|^\d{8}$/, 'O NCM deve conter 8 dígitos.'),
  cfop: z.string().regex(/^$|^\d{4}$/, 'O CFOP deve conter 4 dígitos.'),
  quantidade: decimal,
  unidade: z.string().trim().min(1, 'Informe a unidade.').max(6),
  valor_unitario: decimal,
  valor_total: decimal,
});
export const notaFiscalManualSchema = z.object({
  direcao: z.enum(['entrada', 'saida']),
  tipo: z.enum(['NF-e', 'NFP-e', 'NFC-e']),
  numero: z.string().regex(/^$|^[1-9]\d{0,8}$/, 'Número de 1 a 999999999.'),
  serie: z.string().regex(/^\d{1,3}$/, 'Série de até três dígitos.'),
  data_emissao: z.string().min(1, 'Informe a data de emissão.'),
  emitente_nome: z.string().trim().min(1, 'Informe o emitente.').max(200),
  emitente_cpf_cnpj: z.string().trim().max(18),
  destinatario_nome: z.string().trim().min(1, 'Informe o destinatário.').max(200),
  destinatario_documento: z.string().trim().max(18),
  destinatario_uf: z.string().regex(/^$|^[A-Z]{2}$/, 'Informe a UF com duas letras.'),
  chave_acesso: z.string().regex(/^$|^\d{44}$/, 'A chave deve conter 44 dígitos.'),
  valor_total: decimal,
  valor_produtos: decimal,
  valor_icms: decimal,
  valor_frete: decimal,
  descricao_produto: z.string().trim().max(300),
  observacoes: z.string().trim().max(2000),
  itens: z.array(notaFiscalItemSchema).min(1, 'Inclua ao menos um item.').max(990),
});
export type NotaFiscalManualForm = z.infer<typeof notaFiscalManualSchema>;
