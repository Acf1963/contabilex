import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contabilidade.settings')
django.setup()

from core.models import Conta, Cliente, Fornecedor
from django.db import transaction

def normalize_code(code):
    if not code:
        return code
    clean_code = str(code).replace('.', '').strip()
    if len(clean_code) > 2:
        base = clean_code[:2]
        resto = ".".join(list(clean_code[2:]))
        return f"{base}.{resto}"
    return clean_code

@transaction.atomic
def fix_accounts():
    print("Iniciando normalização de códigos do Plano de Contas...")
    
    # 1. Primeiro as contas normais
    contas = list(Conta.objects.all())
    for c in contas:
        old_code = c.codigo
        new_code = normalize_code(old_code)
        
        if old_code != new_code:
            # Verifica se já existe uma conta com o novo código
            existing = Conta.objects.filter(codigo=new_code, empresa=c.empresa).exclude(id=c.id).first()
            if existing:
                print(f"Mesclando {old_code} -> {new_code} (já existia)")
                # Mover relações
                c.movimentos.all().update(conta=existing)
                c.subcontas.all().update(conta_pai=existing)
                # Clientes e Fornecedores relacionados (se houver via conta_pai na Entidade)
                Cliente.objects.filter(conta_pai=c).update(conta_pai=existing)
                Fornecedor.objects.filter(conta_pai=c).update(conta_pai=existing)
                c.delete()
            else:
                print(f"Atualizando Conta {old_code} -> {new_code}")
                # Usamos update direto para evitar disparar o save() que talvez fizesse algo extra 
                # Mas o save() agora tem a mesma lógica, então c.save() está ok.
                # No entanto, para evitar problemas de integridade durante o loop, update é mais seguro se não houver signals complexos.
                Conta.objects.filter(id=c.id).update(codigo=new_code)

    # 2. Agora as entidades (Clientes e Fornecedores)
    # Suas contas já foram atualizadas acima (seja por código ou por mesclagem)
    # Mas precisamos atualizar o campo codigo_contabilistico no próprio modelo Cliente/Fornecedor
    
    print("Atualizando códigos de Clientes...")
    for cli in Cliente.objects.all():
        old_cod = cli.codigo_contabilistico
        # O código do cliente é composto pelo pai + sequencial
        # Se o pai mudou (já mudou), o novo código deve ser recalculado
        new_cod = f"{cli.conta_pai.codigo}.{cli.numero_sequencial:05d}"
        if old_cod != new_cod:
            print(f"  {cli.nome}: {old_cod} -> {new_cod}")
            Cliente.objects.filter(id=cli.id).update(codigo_contabilistico=new_cod)
            # A conta correspondente no PGC também deve ser atualizada se já não foi
            Conta.objects.filter(codigo=old_cod, empresa=cli.empresa).update(codigo=new_cod)

    print("Atualizando códigos de Fornecedores...")
    for forn in Fornecedor.objects.all():
        old_cod = forn.codigo_contabilistico
        new_cod = f"{forn.conta_pai.codigo}.{forn.numero_sequencial:05d}"
        if old_cod != new_cod:
            print(f"  {forn.nome}: {old_cod} -> {new_cod}")
            Fornecedor.objects.filter(id=forn.id).update(codigo_contabilistico=new_cod)
            Conta.objects.filter(codigo=old_cod, empresa=forn.empresa).update(codigo=new_cod)

    print("Normalização concluída com sucesso!")

if __name__ == "__main__":
    fix_accounts()
