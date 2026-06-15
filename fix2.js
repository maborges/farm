const fs = require('fs');
let content = fs.readFileSync('apps/web/src/app/(dashboard)/cadastros/imoveis/ImoveisClient.tsx', 'utf8');
content = content.replace(/area_reserva_legal_ha: "",\n      municipio/g, 'area_reserva_legal_ha: "",\n      matricula: "",\n      situacao: "PROPRIO",\n      proprietario_nome: "",\n      municipio');
content = content.replace(/imovel\.area_reserva_legal_ha\?\.toString\(\) \|\| "",\n      municipio/g, 'String(imovel.area_reserva_legal_ha || ""),\n      matricula: imovel.matricula || "",\n      situacao: imovel.situacao || "PROPRIO",\n      proprietario_nome: imovel.proprietario_nome || "",\n      municipio');
content = content.replace(/imovel\.tipo/g, '(imovel as any).tipo');
content = content.replace(/imovel\.observacao/g, '(imovel as any).observacao');
fs.writeFileSync('apps/web/src/app/(dashboard)/cadastros/imoveis/ImoveisClient.tsx', content);
