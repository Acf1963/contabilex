import os
import django
import sys

# Ajusta o path para o diretório do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contabilidade.settings')

try:
    django.setup()
    from core.models import Cliente
    qs = Cliente.objects.all().order_by('id')
    if not qs.exists():
        print('Nenhum cliente encontrado.')
    else:
        print('ID\tNome\tCódigo Contabilístico')
        for c in qs:
            print(f"{c.id}\t{c.nome}\t{c.codigo_contabilistico}")
except Exception as e:
    print('Erro ao listar clientes:')
    import traceback; traceback.print_exc()
