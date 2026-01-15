import os
import sys
import django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contabilidade.settings')
django.setup()

from core.models import Conta
with open('dump_contas.txt', 'w') as f:
    for c in Conta.objects.all().order_by('codigo'):
        f.write(f"{c.codigo}|{c.descricao}\n")
