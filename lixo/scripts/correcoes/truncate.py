import sys

with open("apps/web/src/app/(dashboard)/suprimentos/estoque/page.tsx", "r") as f:
    lines = f.readlines()

# keep up to line 806 (index 805)
lines = lines[:806]

with open("apps/web/src/app/(dashboard)/suprimentos/estoque/page.tsx", "w") as f:
    f.writelines(lines)

