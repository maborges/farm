import sys, os

file_path = "apps/web/src/app/(dashboard)/suprimentos/estoque/page.tsx"
with open(file_path, "r") as f:
    content = f.read()

imports = """import { useState, useMemo } from "react";
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

// Tipos provisórios
type Produto = any;
type Deposito = any;
type Saldo = any;
type Reserva = any;
"""

def extract_func(name, new_name):
    global content
    target = f"function {name}("
    start = content.find(target)
    if start == -1:
        return
    
    end = start
    open_braces = 0
    started = False
    
    for i in range(start, len(content)):
        if content[i] == '{':
            open_braces += 1
            started = True
        elif content[i] == '}':
            open_braces -= 1
            
        if started and open_braces == 0:
            end = i + 1
            break
            
    func_content = content[start:end]
    # save to new file
    with open(f"apps/web/src/app/(dashboard)/suprimentos/estoque/_components/{new_name}.tsx", "w") as f:
        f.write(imports + "\nexport " + func_content.replace(target, f"function {new_name}("))
        
    # replace in old
    content = content.replace(func_content, f"// Extracted {new_name}")
    content = content.replace(f"<{name}", f"<{new_name}")

extract_func("EntradaDialog", "EstoqueEntradaDialog")
extract_func("SaidaDialog", "EstoqueSaidaDialog")
extract_func("TransferenciaDialog", "EstoqueTransferenciaDialog")
extract_func("AjusteDialog", "EstoqueAjusteDialog")
extract_func("NovoProdutoDialog", "EstoqueProdutoDialog")
extract_func("NovoDepositoDialog", "EstoqueDepositoDialog")
extract_func("ReservaDialog", "EstoqueNovaReservaDialog")

extra_imports = """
import { EstoqueEntradaDialog } from "./_components/EstoqueEntradaDialog";
import { EstoqueSaidaDialog } from "./_components/EstoqueSaidaDialog";
import { EstoqueTransferenciaDialog } from "./_components/EstoqueTransferenciaDialog";
import { EstoqueAjusteDialog } from "./_components/EstoqueAjusteDialog";
import { EstoqueProdutoDialog } from "./_components/EstoqueProdutoDialog";
import { EstoqueDepositoDialog } from "./_components/EstoqueDepositoDialog";
import { EstoqueNovaReservaDialog } from "./_components/EstoqueNovaReservaDialog";
"""

content = content.replace('import { useMemo, useState } from "react";', extra_imports + '\nimport { useMemo, useState } from "react";')

with open(file_path, "w") as f:
    f.write(content)

print("Done")
