import os
import django
import sys
import re

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contabilidade.settings')
django.setup()

from core.models import Conta, Classe

def add_account(codigo, descricao, tipo_char):
    tipo_map = {'R': 'RAZAO', 'I': 'INTEGRACAO', 'M': 'MOVIMENTO'}
    tipo = tipo_map.get(tipo_char.upper(), 'MOVIMENTO')
    aceita = (tipo == 'MOVIMENTO')
    
    try:
        classe_cod = codigo[0]
        classe = Classe.objects.get(codigo=classe_cod)
    except Exception as e:
        print(f"Error finding class for {codigo}: {e}")
        return

    # Find parent
    pai = None
    potential_parent_code = codigo[:-1]
    while len(potential_parent_code) >= 2:
        pai = Conta.objects.filter(codigo=potential_parent_code).first()
        if pai:
            break
        potential_parent_code = potential_parent_code[:-1]

    Conta.objects.update_or_create(
        codigo=codigo,
        defaults={
            'descricao': descricao,
            'tipo': tipo,
            'aceita_lancamentos': aceita,
            'classe': classe,
            'conta_pai': pai,
            'empresa': None
        }
    )

def process_file(filepath):
    print(f"Processing {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            match = re.search(r'^(.*?)\s+(.*?)\s+([RIM])$', line)
            if match:
                add_account(match.group(1).strip(), match.group(2).strip(), match.group(3).strip())
            else:
                parts = re.split(r'\t|\s{2,}', line)
                if len(parts) >= 3:
                    add_account(parts[0].strip(), parts[1].strip(), parts[-1].strip())
                elif len(parts) == 2:
                    add_account(parts[0].strip(), parts[1].strip(), 'M')

if __name__ == "__main__":
    for i in range(1, 5):
        process_file(f'scripts/pgc_data_{i}.txt')
