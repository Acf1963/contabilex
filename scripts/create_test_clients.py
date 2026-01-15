from core.models import Cliente, Conta, Empresa
from decimal import Decimal

emp = Empresa.objects.first()
if not emp:
    print("Erro: Nenhuma empresa encontrada.")
else:
    # Tenta encontrar a conta de clientes (31)
    conta_31 = Conta.objects.filter(codigo="31", empresa=emp).first()
    if not conta_31:
        # Tenta uma conta global se não houver da empresa
        conta_31 = Conta.objects.filter(codigo="31").first()
    
    if not conta_31:
        # Se ainda não houver, tenta qualquer conta da classe 3
        conta_31 = Conta.objects.filter(codigo__startswith="3", empresa=emp).first()

    if not conta_31:
        print("Erro: Conta de Clientes (Classe 3) não encontrada.")
    else:
        # Criar 3 clientes simulados
        clientes_data = [
            {
                "nome": "AngoSupply Lda",
                "nif": "5000123456",
                "email": "vendas@angosupply.ao",
                "telefone": "923111222",
                "endereco": "Zona Talatona, Luanda",
            },
            {
                "nome": "Constructora Delta",
                "nif": "5000987654",
                "email": "geral@delta.ao",
                "telefone": "912333444",
                "endereco": "Av. Deolinda Rodrigues, Luanda",
            },
            {
                "nome": "TecnoInova S.A.",
                "nif": "5000555444",
                "email": "compras@tecnoinova.ao",
                "telefone": "934555666",
                "endereco": "Nova Vida, Edifício A",
            }
        ]

        for data in clientes_data:
            cliente, created = Cliente.objects.get_or_create(
                nif=data['nif'],
                empresa=emp,
                defaults={
                    'nome': data['nome'],
                    'email': data['email'],
                    'telefone': data['telefone'],
                    'endereco': data['endereco'],
                    'conta_pai': conta_31
                }
            )
            if created:
                print(f"Cliente criado: {cliente.nome} ({cliente.codigo_contabilistico})")
            else:
                print(f"Cliente já existia: {cliente.nome}")
