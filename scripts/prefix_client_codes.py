import os
import django
import sys

# Ajusta o path para o diretório do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contabilidade.settings')

PREFIX = '31.1.1.2.1'

try:
    django.setup()
    from core.models import Cliente, Conta
    updated = []
    for c in Cliente.objects.all().order_by('id'):
        old = c.codigo_contabilistico or ''
        if old.startswith(PREFIX):
            print(f"ID {c.id} já tem prefixo: {old}")
            continue
        if '.' not in old:
            print(f"ID {c.id} código inesperado (sem ponto): {old}, pulando")
            continue
        seq = old.split('.')[-1]
        new = f"{PREFIX}.{seq}"
        print(f"Atualizando cliente ID {c.id}: {old} -> {new}")
        # Atualiza o campo (mesmo sendo editable=False, via código funciona)
        c.codigo_contabilistico = new
        c.save(update_fields=['codigo_contabilistico'])

        # Garante existência/atualização da conta correspondente
        defaults = {
            'classe': c.conta_pai.classe,
            'descricao': c.nome,
            'conta_pai': c.conta_pai,
            'tipo': 'MOVIMENTO',
            'tipo_entidade': 'CLIENTE',
            'aceita_lancamentos': True,
        }
        conta, created = Conta.objects.update_or_create(
            codigo=new,
            empresa=c.empresa,
            defaults=defaults
        )
        if created:
            print(f"  Conta criada: {conta.codigo}")
        else:
            print(f"  Conta existente atualizada: {conta.codigo}")

        updated.append((c.id, old, new))

    if not updated:
        print('Nenhuma atualização necessária.')
    else:
        print('\nResumo de atualizações:')
        for u in updated:
            print(f"ID {u[0]}: {u[1]} -> {u[2]}")

except Exception:
    import traceback; traceback.print_exc()
    print('Erro ao executar o script')
