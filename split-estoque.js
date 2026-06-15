const fs = require('fs');

const file = 'apps/web/src/app/(dashboard)/suprimentos/estoque/page.tsx';
let content = fs.readFileSync(file, 'utf8');

const imports = `import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

// @ts-ignore
type Produto = any;
// @ts-ignore
type Deposito = any;
// @ts-ignore
type Saldo = any;
`;

const extractFunction = (name, newName) => {
    const startStr = "function " + name + "(";
    const startIndex = content.indexOf(startStr);
    if (startIndex === -1) {
        console.log("NOT FOUND: ", name);
        return;
    }
    
    let openBraces = 0;
    let endIndex = startIndex;
    let started = false;
    for (let i = startIndex; i < content.length; i++) {
        if (content[i] === '{') {
            openBraces++;
            started = true;
        } else if (content[i] === '}') {
            openBraces--;
        }
        if (started && openBraces === 0) {
            endIndex = i + 1;
            break;
        }
    }

    let funcContent = content.substring(startIndex, endIndex);
    
    let newFileContent = imports + "\n" + "export " + funcContent.replace(startStr, "function " + newName + "(");
    fs.writeFileSync("apps/web/src/app/(dashboard)/suprimentos/estoque/_components/" + newName + ".tsx", newFileContent);

    content = content.replace(funcContent, "// Extracted " + newName);
    // Replace all <Name with <NewName
    content = content.replace(new RegExp("<" + name, 'g'), "<" + newName);
};

extractFunction("EntradaDialog", "EstoqueEntradaDialog");
extractFunction("SaidaDialog", "EstoqueSaidaDialog");
extractFunction("TransferenciaDialog", "EstoqueTransferenciaDialog");
extractFunction("AjusteDialog", "EstoqueAjusteDialog");
extractFunction("NovoProdutoDialog", "EstoqueProdutoDialog");
extractFunction("NovoDepositoDialog", "EstoqueDepositoDialog");

const extraImports = `
import { EstoqueEntradaDialog } from "./_components/EstoqueEntradaDialog";
import { EstoqueSaidaDialog } from "./_components/EstoqueSaidaDialog";
import { EstoqueTransferenciaDialog } from "./_components/EstoqueTransferenciaDialog";
import { EstoqueAjusteDialog } from "./_components/EstoqueAjusteDialog";
import { EstoqueProdutoDialog } from "./_components/EstoqueProdutoDialog";
import { EstoqueDepositoDialog } from "./_components/EstoqueDepositoDialog";
`;

content = content.replace('import { useMemo, useState } from "react";', extraImports + '\nimport { useMemo, useState } from "react";');

fs.writeFileSync(file, content);

