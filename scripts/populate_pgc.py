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

if __name__ == "__main__":
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
            
        # Try to match the last character as the type if it is R, I or M
        match = re.search(r'^(.*?)\s+(.*?)\s+([RIM])$', line)
        if match:
            codigo = match.group(1).strip()
            descricao = match.group(2).strip()
            tipo_char = match.group(3).strip()
            add_account(codigo, descricao, tipo_char)
        else:
            # Fallback for lines that might be missing the type or have different tabs
            parts = re.split(r'\t|\s{2,}', line)
            if len(parts) >= 3:
                add_account(parts[0].strip(), parts[1].strip(), parts[-1].strip())
            elif len(parts) == 2:
                # Default to Movimento if type missing
                add_account(parts[0].strip(), parts[1].strip(), 'M')
