import sys

with open("apps/web/src/app/(dashboard)/suprimentos/estoque/page.tsx", "r") as f:
    page_lines = f.readlines()

with open("apps/web/src/app/(dashboard)/suprimentos/estoque/_components/EstoqueDialogs.tsx", "r") as f:
    dialog_content = f.read()

# Find the first export function
first_func_index = dialog_content.find("export function ")

# Extract imports and constants from page.tsx (lines 2 to 139 roughly, up to "export default function EstoquePage")
# We just slice until "export default function EstoquePage"
end_idx = 0
for i, line in enumerate(page_lines):
    if line.startswith("export default function EstoquePage"):
        end_idx = i
        break

header = "".join(page_lines[2:end_idx])

# Some extra imports for Dialogs that might be missing but are in page.tsx:
# page.tsx has useMutation, useQueryClient but they might be used here. Actually page.tsx has them.
# The only issue is that in page.tsx we added "import { EntradaDialog... } from ..." at line 4!
# So we should filter out line 4 from header.
header_lines = header.split("\n")
clean_header = "\n".join([line for line in header_lines if "import { EntradaDialog" not in line])

# We need to make sure 'useQueryClient' and 'useMutation' are imported if not present.
if "useMutation" not in clean_header:
    clean_header = clean_header.replace('import { useQuery', 'import { useQuery, useMutation, useQueryClient')

final_content = "import { useState, useMemo } from \"react\";\n" + clean_header + "\n" + dialog_content[first_func_index:]

with open("apps/web/src/app/(dashboard)/suprimentos/estoque/_components/EstoqueDialogs.tsx", "w") as f:
    f.write(final_content)

