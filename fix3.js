const fs = require('fs');
let content = fs.readFileSync('apps/web/src/app/(dashboard)/dashboard/settings/team/page.tsx', 'utf8');
content = content.replace(/from "@farm\/zod-schemas"/g, 'from "@/types/global"');
fs.writeFileSync('apps/web/src/app/(dashboard)/dashboard/settings/team/page.tsx', content);

let imoveisContent = fs.readFileSync('apps/web/src/app/(dashboard)/cadastros/imoveis/ImoveisClient.tsx', 'utf8');
imoveisContent = imoveisContent.replace(/nome: imovel.nome,\n      unidade_produtiva_id: imovel.unidade_produtiva_id,\n      nirf/g, 'nome: imovel.nome,\n      unidade_produtiva_id: imovel.unidade_produtiva_id,\n      matricula: imovel.matricula || "",\n      situacao: imovel.situacao || "PROPRIO",\n      proprietario_nome: imovel.proprietario_nome || "",\n      nirf');
fs.writeFileSync('apps/web/src/app/(dashboard)/cadastros/imoveis/ImoveisClient.tsx', imoveisContent);

