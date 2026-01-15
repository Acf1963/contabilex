import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contabilidade.settings')
django.setup()

from core.models import Conta, Cliente, Fornecedor
from django.db import transaction

def revert_dots():
    print("Revertendo formatação excessiva de pontos em contas de Entidades...")
    
    # Mapear Entidades
    entidades = list(Cliente.objects.all()) + list(Fornecedor.objects.all())
    
    with transaction.atomic():
        for ent in entidades:
            expected_code = f"{ent.conta_pai.codigo}.{ent.numero_sequencial:05d}"
            # O código atual no banco pode estar deformado como 31.0.0.0.0.1
            # O código esperado é 31.00001
            
            # Vamos ver se existe a conta deformada
            # Simular a deformação
            clean = expected_code.replace('.', '')
            deformed = f"{clean[:2]}.{'.'.join(list(clean[2:]))}"
            
            conta_deformed = Conta.objects.filter(codigo=deformed, empresa=ent.empresa).first()
            conta_expected = Conta.objects.filter(codigo=expected_code, empresa=ent.empresa).first()
            
            if conta_deformed and not conta_expected:
                print(f"Corrigindo {ent.nome}: {deformed} -> {expected_code}")
                conta_deformed.codigo = expected_code
                conta_deformed.save()
            elif conta_expected:
                print(f"OK {ent.nome}: {expected_code}")
                print(f"Aviso: Conta não encontrada para {ent.nome}. Esperado: {expected_code} ou {deformed}")
                # Listar contas da empresa que começam com o prefixo para debug
                prefix = clean[:2] + "."
                candidates = list(Conta.objects.filter(codigo__startswith=prefix, empresa=ent.empresa).values_list('codigo', flat=True))
                # Tentar encontrar a mais parecida
                print(f"  Candidatas encontradas: {candidates}")
                
                # Se houver apenas uma e parecer correta (mesmos digitos), usar
                for cand in candidates:
                     if cand.replace('.', '') == clean:
                         print(f"  -> Encontrada correspondência exata de dígitos: {cand}. Atualizando para {expected_code}")
                         c = Conta.objects.get(codigo=cand, empresa=ent.empresa)
                         c.codigo = expected_code
                         c.save()
                         break
            
            # Atualizar referência na entidade se necessário (embora deva estar certo)
            if ent.codigo_contabilistico != expected_code:
                ent.codigo_contabilistico = expected_code
                ent.save()

    print("Concluído.")

if __name__ == "__main__":
    revert_dots()
