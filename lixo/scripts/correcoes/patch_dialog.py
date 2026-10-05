import re

with open("apps/web/src/components/agricola/safra-create-dialog.tsx", "r", encoding="utf-8") as f:
    content = f.read()

old_block = """                <Controller
                    control={control}
                    name={`cultivos.${index}.cultura`}
                    render={({ field: f }) => (
                        <Select value={f.value} onValueChange={f.onChange}>
                            <SelectTrigger className={cn("h-8 text-sm", cultivoErrors?.cultura && "border-destructive")}>
                                <SelectValue placeholder="Selecione a cultura" />
                            </SelectTrigger>
                            <SelectContent>
                                {culturas.map(c => (
                                    <SelectItem key={c.id} value={c.nome} className="text-sm">
                                        {c.nome}
                                        {c.variedade && <span className="text-muted-foreground ml-1">· {c.variedade}</span>}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    )}
                />"""

new_block = """                <Controller
                    control={control}
                    name={`cultivos.${index}.cultura`}
                    render={({ field: f }) => {
                        const selectedId = culturas.find(c => c.nome === f.value)?.id || f.value;
                        return (
                            <Select 
                                value={selectedId} 
                                onValueChange={(val) => {
                                    const selected = culturas.find(c => c.id === val);
                                    if (selected) {
                                        f.onChange(selected.nome);
                                        if (selected.variedade && !watch(`cultivos.${index}.cultivar_nome`)) {
                                            setValue(`cultivos.${index}.cultivar_nome`, selected.variedade, { shouldDirty: true });
                                        }
                                    } else {
                                        f.onChange(val);
                                    }
                                }}
                            >
                                <SelectTrigger className={cn("h-8 text-sm", cultivoErrors?.cultura && "border-destructive")}>
                                    <SelectValue placeholder="Selecione a cultura" />
                                </SelectTrigger>
                                <SelectContent>
                                    {culturas.map(c => (
                                        <SelectItem key={c.id} value={c.id} className="text-sm">
                                            {c.nome}
                                            {c.variedade && <span className="text-muted-foreground ml-1">· {c.variedade}</span>}
                                        </SelectItem>
                                    ))}
                                    {f.value && !culturas.find(c => c.nome === f.value) && (
                                        <SelectItem value={f.value} className="text-sm">
                                            {f.value}
                                        </SelectItem>
                                    )}
                                </SelectContent>
                            </Select>
                        );
                    }}
                />"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open("apps/web/src/components/agricola/safra-create-dialog.tsx", "w", encoding="utf-8") as f:
        f.write(content)
    print("Patch applied successfully.")
else:
    print("Could not find block to patch.")
