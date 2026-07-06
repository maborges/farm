import os
import re

mapping = {
    r'\bcanônica\b': 'oficial',
    r'\bcanônicas\b': 'oficiais',
    r'\bcanônico\b': 'oficial',
    r'\bcanônicos\b': 'oficiais',
    r'\bcanonica\b': 'oficial',
    r'\bcanonicas\b': 'oficiais',
    r'\bcanonico\b': 'oficial',
    r'\bcanonicos\b': 'oficiais',
    r'\bcanonical\b': 'oficial',
    r'\bCanônica\b': 'Oficial',
    r'\bCanônicas\b': 'Oficiais',
    r'\bCanônico\b': 'Oficial',
    r'\bCanônicos\b': 'Oficiais',
    r'\bCanonica\b': 'Oficial',
    r'\bCanonicas\b': 'Oficiais',
    r'\bCanonico\b': 'Oficial',
    r'\bCanonicos\b': 'Oficiais',
    r'\bCanonical\b': 'Oficial',
    r'\bCANÔNICO\b': 'OFICIAL',
    r'\bCANÔNICA\b': 'OFICIAL',
    r'\bCANONICO\b': 'OFICIAL',
    r'\bCANONICA\b': 'OFICIAL',
    r'\bCANONICAL\b': 'OFICIAL'
}

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content
    for pattern, replacement in mapping.items():
        new_content = re.sub(pattern, replacement, new_content)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main():
    root_dir = '/opt/lampp/htdocs/farm'
    count = 0
    for root, dirs, files in os.walk(root_dir):
        if 'node_modules' in root or '.git' in root or '.venv' in root:
            continue
        for file in files:
            if file.endswith('.md'):
                filepath = os.path.join(root, file)
                if replace_in_file(filepath):
                    count += 1
    
    print(f"Modificados {count} arquivos Markdown.")

if __name__ == '__main__':
    main()
