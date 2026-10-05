import sys

with open("apps/web/src/app/(dashboard)/suprimentos/estoque/page.tsx", "r") as f:
    page_content = f.read()

# get all imports from page.tsx (lines starting with import until the first non-import empty line)
import_lines = []
for line in page_content.split('\n'):
    if line.startswith('import') or line.startswith('} from') or line.startswith('  ') or line.startswith('//') or line.startswith('type') or line.startswith('const MOTIVOS'):
        import_lines.append(line)
    if 'MOTIVOS_AJUSTE = ' in line:
        break

with open("apps/web/src/app/(dashboard)/suprimentos/estoque/_components/EstoqueDialogs.tsx", "r") as f:
    dialog_content = f.read()
    
# replace the first block of imports in Dialogs with the one from page.tsx
# find the first `export function `
first_func = dialog_content.find("export function ")
if first_func != -1:
    dialog_content = "\n".join(import_lines) + "\n" + dialog_content[first_func:]
else:
    print("Could not find export function")

with open("apps/web/src/app/(dashboard)/suprimentos/estoque/_components/EstoqueDialogs.tsx", "w") as f:
    f.write(dialog_content)

