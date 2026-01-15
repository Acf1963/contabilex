import os
import django
import sys

# Ajusta o path para o diretório do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contabilidade.settings')

try:
    django.setup()
    from core.models import Fornecedor
    qs = Fornecedor.objects.all().order_by('id')
    if not qs.exists():
        print('Nenhum fornecedor encontrado.')
    else:
        print('ID\tNome\tCódigo Contabilístico')
        for f in qs:
            print(f"{f.id}\t{f.nome}\t{f.codigo_contabilistico}")
except Exception as e:
    print('Erro ao listar fornecedores:')
    import traceback; traceback.print_exc()
