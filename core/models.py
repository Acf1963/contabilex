from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal, ROUND_CEILING

class Empresa(models.Model):
    """
    Dados da empresa para o sistema de contabilidade.
    """
    MOEDA_CHOICES = (
        ('AOA', 'Kwanza (AOA)'),
        ('USD', 'Dólar (USD)'),
        ('EUR', 'Euro (EUR)'),
    )
    
    PAIS_CHOICES = (
        ('AO', 'Angola'),
        ('PT', 'Portugal'),
        ('FR', 'França'),
        ('ES', 'Espanha'),
        ('US', 'Estados Unidos'),
    )
    
    PLANO_MODELO_CHOICES = (
        ('PGC_GERAL', 'PGC Angola - Plano Geral'),
        ('PGC_SIMP', 'PGC Angola - Regime Simplificado'),
        ('PERSONALIZADO', 'Personalizado (Importação Manual)'),
    )
    
    nome = models.CharField(max_length=255)
    nif = models.CharField(max_length=50, verbose_name="NIF")
    morada = models.TextField()
    ano_exercicio = models.IntegerField(default=2025)
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=50, blank=True, null=True)
    logo = models.ImageField(upload_to='empresa/', null=True, blank=True)
    
    # Plano de Contas
    plano_modelo = models.CharField(max_length=30, choices=PLANO_MODELO_CHOICES, default='PGC_GERAL', verbose_name="Modelo de Plano de Contas")
    
    # Localização
    pais = models.CharField(max_length=2, choices=PAIS_CHOICES, default='AO', verbose_name="País")

    # Configurações de Moeda
    moeda_padrao = models.CharField(max_length=3, choices=MOEDA_CHOICES, default='AOA', verbose_name="Moeda Base")
    moeda_estrangeira = models.CharField(max_length=3, choices=MOEDA_CHOICES, default='USD', verbose_name="Moeda de Referência")
    taxa_cambio = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal('1.000000'), verbose_name="Taxa de Câmbio (Base/Ref)")

    @property
    def moeda_simbolo(self):
        simbolos = {
            'AOA': 'Kz',
            'USD': '$',
            'EUR': '€',
            'BRL': 'R$',
        }
        return simbolos.get(self.moeda_padrao, 'Kz')

    def get_taxa_na_data(self, data=None):
        """Retorna a taxa de câmbio válida para uma determinada data"""
        if data is None:
            data = timezone.now().date()
        
        # Procura a taxa mais recente que seja menor ou igual à data fornecida
        cambio = self.historico_cambio.filter(data_inicio__lte=data).order_by('-data_inicio').first()
        if cambio:
            return cambio.taxa
        return self.taxa_cambio # Fallback para a taxa padrão definida na empresa

    def __str__(self):
        return f"{self.nome} ({self.ano_exercicio})"

class Cambio(models.Model):
    """Histórico de taxas de câmbio para evitar retroatividade"""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='historico_cambio')
    data_inicio = models.DateField(default=timezone.now, verbose_name="Válido desde")
    taxa = models.DecimalField(max_digits=18, decimal_places=6, verbose_name="Taxa de Câmbio")
    
    class Meta:
        ordering = ['-data_inicio']
        verbose_name = "Câmbio"
        verbose_name_plural = "Câmbios"

    def __str__(self):
        return f"{self.data_inicio} - {self.taxa}"

class Funcionario(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='funcionarios')
    nome = models.CharField(max_length=255)
    nif = models.CharField(max_length=50, blank=True, null=True, verbose_name="NIF")
    numero_seguranca_social = models.CharField(max_length=50, blank=True, null=True, verbose_name="Nº Segurança Social")
    cargo = models.CharField(max_length=100, verbose_name="Cargo/Função")
    data_admissao = models.DateField(verbose_name="Data de Admissão")
    salario_base = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Salário Base")
    subsidio_alimentacao = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Subsídio de Alimentação")
    subsidio_transporte = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Subsídio de Transporte")
    outros_abonos = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Outros Abonos (Sujeitos a SS)")
    
    # Contactos
    telefone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Telefone")
    endereco = models.TextField(blank=True, null=True, verbose_name="Endereço")
    
    # Detalhes Bancários
    banco = models.CharField(max_length=100, blank=True, null=True)
    iban = models.CharField(max_length=50, blank=True, null=True, verbose_name="IBAN")
    
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Funcionário"
        verbose_name_plural = "Funcionários"

class ProcessamentoSalarial(models.Model):
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='processamentos')
    mes = models.IntegerField(verbose_name="Mês")
    ano = models.IntegerField(verbose_name="Ano")
    data_processamento = models.DateField(default=timezone.now)
    
    # Variáveis Mensais
    horas_falta = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Faltas (Horas)")
    horas_50 = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Horas Extras (50%)")
    horas_100 = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Horas Extras (100%)")

    # Valores Processados
    salario_base = models.DecimalField(max_digits=12, decimal_places=2)
    subsidio_alimentacao = models.DecimalField(max_digits=12, decimal_places=2)
    subsidio_transporte = models.DecimalField(max_digits=12, decimal_places=2)
    outros_abonos = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Cálculos Extras
    valor_horas_extras = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    desconto_faltas = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    total_bruto = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Descontos Legais
    inss_funcionario = models.DecimalField(max_digits=12, decimal_places=2) # 3%
    inss_empresa = models.DecimalField(max_digits=12, decimal_places=2)    # 8%
    irt = models.DecimalField(max_digits=12, decimal_places=2)
    
    total_descontos = models.DecimalField(max_digits=12, decimal_places=2)
    salario_liquido = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Status
    pago = models.BooleanField(default=False)
    contabilizado = models.BooleanField(default=False)
    lancamento = models.ForeignKey('LancamentoDiario', null=True, blank=True, on_delete=models.SET_NULL, related_name='salarios')


    class Meta:
        verbose_name = "Processamento Salarial"
        verbose_name_plural = "Processamentos Salariais"
        unique_together = ('funcionario', 'mes', 'ano')

    def __str__(self):
        return f"{self.funcionario.nome} - {self.mes}/{self.ano}"

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresa"

class TabelaIRT(models.Model):
    """
    Tabela de IRT (Imposto sobre Rendimento do Trabalho)
    """
    limite = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="Limite do Escalão")
    taxa = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Taxa (%)")
    parcela_fixa = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Parcela Fixa")
    excesso = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Parcela a Abater/Excesso")
    
    class Meta:
        ordering = ['limite']
        verbose_name = "Tabela IRT"
        verbose_name_plural = "Tabela IRT"

    def __str__(self):
        return f"Até {self.limite}: {self.taxa}%"

class TaxaImposto(models.Model):
    """
    Tabela de impostos e taxas em vigor (IVA, Industrial, Selo, etc.)
    """
    codigo = models.CharField(max_length=20, unique=True, help_text="Ex: IVA_NORMAL, IND_NORMAL")
    nome = models.CharField(max_length=100)
    taxa = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentagem do imposto")
    descricao = models.TextField(blank=True, null=True)
    ativo = models.BooleanField(default=True)
    ultima_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Taxa de Imposto"
        verbose_name_plural = "Taxas de Imposto"

    def __str__(self):
        return f"{self.nome} ({self.taxa}%)"

class Falta(models.Model):
    """
    Registo de Faltas
    """
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='faltas')
    data = models.DateField(default=timezone.now)
    horas = models.DecimalField(max_digits=4, decimal_places=2, help_text="Número de horas de ausência")
    justificada = models.BooleanField(default=False)
    motivo = models.CharField(max_length=255, blank=True, null=True)
    comprovativo = models.FileField(upload_to='rh/faltas/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.funcionario.nome} - {self.data} - {self.horas}h"

class HoraExtra(models.Model):
    """
    Registo de Horas Extras
    """
    TIPO_CHOICES = (
        ('50', '50% (Dia Útil/Diurno)'),
        ('100', '100% (Noturno/Fim de Semana/Feriado)'),
    )
    
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='horas_extras')
    data = models.DateField(default=timezone.now)
    horas = models.DecimalField(max_digits=4, decimal_places=2)
    tipo = models.CharField(max_length=3, choices=TIPO_CHOICES, default='50')
    motivo = models.CharField(max_length=255, blank=True, null=True)
    aprovado_por = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.funcionario.nome} - {self.data} - {self.horas}h ({self.get_tipo_display()})"


class Classe(models.Model):
    codigo = models.CharField(max_length=2, unique=True, help_text="Ex: 1, 2, 3...")
    descricao = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"

class Conta(models.Model):
    """
    Representa uma conta do Plano Geral de Contabilidade (PGC) de Angola.
    Ex: 31 (Clientes), 32 (Fornecedores)
    """
    TIPO_CHOICES = (
        ('RAZAO', 'Razão'),
        ('INTEGRACAO', 'Integração'),
        ('MOVIMENTO', 'Movimento'),
        ('APURAMENTO', 'Apuramento'),
        ('A', 'Apuramento'),
    )

    TIPO_ENTIDADE_CHOICES = (
        ('NENHUM', 'Nenhum'),
        ('CLIENTE', 'Cliente'),
        ('FORNECEDOR', 'Fornecedor'),
        ('ESTADO', 'Estado'),
        ('BANCO', 'Banco'),
        ('CAIXA', 'Caixa'),
    )
    
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='contas')
    codigo = models.CharField(max_length=20, help_text="Código da conta. Ex: 31, 31.1")
    descricao = models.CharField(max_length=255)
    conta_pai = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='subcontas')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='MOVIMENTO')
    tipo_entidade = models.CharField(max_length=20, choices=TIPO_ENTIDADE_CHOICES, default='NENHUM', verbose_name="Tipo de Terceiro/Entidade")
    
    # Se esta conta aceita lançamentos ou é apenas agregadora
    aceita_lancamentos = models.BooleanField(default=False)
    
    # Empresa a que pertence (null para contas globais do PGC)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, null=True, blank=True, related_name='contas')

    def save(self, *args, **kwargs):
        if self.codigo and '.' not in self.codigo:
            # 1. Normalizar o código apenas se não tiver pontos
            # Se o utilizador digitar 111, transformar em 11.1
            if len(self.codigo) == 3:
                self.codigo = f"{self.codigo[:2]}.{self.codigo[2:]}"
            elif len(self.codigo) == 4:
                self.codigo = f"{self.codigo[:2]}.{self.codigo[2]}.{self.codigo[3]}"
            elif len(self.codigo) > 4:
                # Caso genérico para códigos longos sem pontos
                base = self.codigo[:2]
                # Tenta manter grupos se possível (ex: 3110001 -> 31.10001 seria melhor mas aqui aplicamos lógica simples)
                # Para evitar problemas com entidades, se for longo e sem pontos, assumimos padrão simples
                # Mas idealmente o input deve vir com pontos.
                resto = ".".join(list(self.codigo[2:]))
                self.codigo = f"{base}.{resto}"

        # 2. Tentar inferir a classe se não estiver definida
        if not self.classe_id and self.codigo:
            from .models import Classe
            primeiro_digito = self.codigo[0]
            classe = Classe.objects.filter(codigo=primeiro_digito).first()
            if classe:
                self.classe = classe

        # 3. Tentar inferir a conta pai baseado no código (ex: pai de 31.1 é 31)
        if not self.conta_pai and self.codigo and '.' in self.codigo:
            # Pega tudo antes do último ponto
            codigo_pai = ".".join(self.codigo.split('.')[:-1])
            pai = Conta.objects.filter(codigo=codigo_pai, empresa=self.empresa).first()
            if not pai and self.empresa:
                # Tenta buscar no plano mestre se não houver na empresa
                pai = Conta.objects.filter(codigo=codigo_pai, empresa__isnull=True).first()
            
            if pai:
                self.conta_pai = pai
            elif len(self.codigo.split('.')[0]) == 2:
                # Se for nível 2 (ex: 31.1), o pai pode ser a conta de 2 dígitos sem ponto
                # Mas aqui o pai já seria 31 (pego pelo join acima)
                pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"

    class Meta:
        ordering = ['codigo']
        unique_together = ('codigo', 'empresa')

class Entidade(models.Model):
    """
    Classe abstrata para Clientes e Fornecedores.
    Gera automaticamente o código contabilístico baseado na conta pai.
    """
    TIPO_ENTIDADE = (
        ('CLIENTE', 'Cliente'),
        ('FORNECEDOR', 'Fornecedor'),
    )
    
    nome = models.CharField(max_length=255)
    nif = models.CharField(max_length=50, blank=True, null=True, verbose_name="NIF")
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    endereco = models.TextField(blank=True, null=True)
    
    # A conta pai no PGC (Ex: Conta 31 para Clientes, Conta 32 para Fornecedores)
    conta_pai = models.ForeignKey(Conta, on_delete=models.PROTECT, related_name='%(class)s_relacionados')
    
    # O número sequencial da entidade (Ex: 1, 2, 3...)
    numero_sequencial = models.IntegerField(editable=False)
    
    # O código final contabilístico (Ex: 31.1.00001)
    codigo_contabilistico = models.CharField(max_length=50, editable=False)
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='%(class)s_set')

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.id:
            # Calcular o próximo número sequencial para esta conta pai DENTRO DA EMPRESA
            ultimo = self.__class__.objects.filter(conta_pai=self.conta_pai, empresa=self.empresa).order_by('-numero_sequencial').first()
            if ultimo:
                self.numero_sequencial = ultimo.numero_sequencial + 1
            else:
                self.numero_sequencial = 1
            
            # Formatar o código: ContaPai.0000N
            # Ex: Se conta pai é 31 e seq é 1 -> 31.0001
            # Nota: O utilizador pediu "acrescido ao número". Vamos usar um ponto separador se a conta não tiver.
            self.codigo_contabilistico = f"{self.conta_pai.codigo}.{self.numero_sequencial:04d}"
            
        super().save(*args, **kwargs)
        
        # Garantir que existe uma conta no PGC para esta entidade
        tipo_ent = 'CLIENTE' if isinstance(self, Cliente) else 'FORNECEDOR'
        Conta.objects.get_or_create(
            codigo=self.codigo_contabilistico,
            empresa=self.empresa,
            defaults={
                'classe': self.conta_pai.classe,
                'descricao': self.nome,
                'conta_pai': self.conta_pai,
                'tipo': 'MOVIMENTO',
                'tipo_entidade': tipo_ent,
                'aceita_lancamentos': True
            }
        )

    def __str__(self):
        return f"{self.codigo_contabilistico} - {self.nome}"

class Cliente(Entidade):
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

class Fornecedor(Entidade):
    class Meta:
        verbose_name = "Fornecedor"
        verbose_name_plural = "Fornecedores"

class Fatura(models.Model):
    ESTADOS = (
        ('RASCUNHO', 'Rascunho'),
        ('EMITIDA', 'Emitida'),
        ('PAGAMENTO_PARCIAL', 'Pagamento Parcial'),
        ('PAGA', 'Paga'),
        ('ANULADA', 'Anulada'),
    )

    numero = models.CharField(max_length=50, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='faturas')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='faturas')
    data_emissao = models.DateField(default=timezone.now)
    data_vencimento = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='RASCUNHO')
    observacoes = models.TextField(blank=True, null=True)
    
    # Totais (calculados)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_imposto = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Retenção na Fonte (6.5% ou 15% IPU)
    aplicar_retencao = models.BooleanField(default=False, verbose_name="Aplicar Retenção")
    taxa_retencao = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('6.5'), verbose_name="Taxa de Retenção (%)")
    valor_retencao = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Valor Retido")
    retencao_paga = models.BooleanField(default=False, verbose_name="DAR Recebido")

    class Meta:
        unique_together = ('numero', 'empresa')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.numero:
            # Gerar número sequencial por empresa: FT/ANO/00001
            ano = timezone.now().year
            ultimo = Fatura.objects.filter(empresa=self.empresa, numero__contains=f"FT/{ano}/").order_by('-id').first()
            if ultimo:
                seq = int(ultimo.numero.split('/')[-1]) + 1
            else:
                seq = 1
            self.numero = f"FT/{ano}/{seq:05d}"
            
        super().save(*args, **kwargs)

    def calcular_totais(self):
        # Recalcular baseado nos itens
        # Nota: Idealmente isto deve ser feito com signals ou métodos explicitos para evitar recursão
        # Mas para MVP serve, desde que chamado com cuidado
        self.subtotal = sum(item.total_linha for item in self.itens.all())
        self.total_imposto = sum(item.valor_imposto for item in self.itens.all())
        self.total = self.subtotal + self.total_imposto
        if self.aplicar_retencao:
            self.valor_retencao = self.subtotal * (self.taxa_retencao / Decimal('100'))
        else:
            self.valor_retencao = 0

        # Evitar loop infinito chamando update em vez de save se for só update
        Fatura.objects.filter(id=self.id).update(
            subtotal=self.subtotal, 
            total_imposto=self.total_imposto, 
            total=self.total,
            valor_retencao=self.valor_retencao
        )

    @property
    def total_pago(self):
        return sum(p.valor for p in self.pagamentos.all())

    @property
    def saldo_pendente(self):
        return self.total - self.total_pago

    @property
    def total_a_pagar(self):
        """Valor líquido a pagar pelo cliente (Total - Retenção)"""
        return self.total - self.valor_retencao

    @property
    def total_estrangeiro(self):
        taxa = self.empresa.get_taxa_na_data(self.data_emissao)
        if taxa and taxa > 0:
            return self.total / taxa
        return 0

    def __str__(self):
        return f"{self.numero} - {self.cliente.nome}"

class PagamentoFatura(models.Model):
    fatura = models.ForeignKey(Fatura, on_delete=models.CASCADE, related_name='pagamentos')
    data = models.DateField(default=timezone.now)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    metodo_pagamento = models.CharField(max_length=50, choices=(('CAIXA', 'Caixa'), ('BANCO', 'Banco')), default='BANCO')
    observacoes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pagamento de {self.valor} Kz para {self.fatura.numero}"

    class Meta:
        verbose_name = "Pagamento de Fatura"
        verbose_name_plural = "Pagamentos de Faturas"

class ItemFatura(models.Model):
    fatura = models.ForeignKey(Fatura, on_delete=models.CASCADE, related_name='itens')
    descricao = models.CharField(max_length=255)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    taxa_imposto = models.DecimalField(max_digits=5, decimal_places=2, default=14.00, help_text="Ex: 14 para 14%")
    
    @property
    def total_linha(self):
        return self.quantidade * self.preco_unitario

    @property
    def valor_imposto(self):
        valor = self.total_linha * (self.taxa_imposto / Decimal(100))
        return valor.quantize(Decimal('1'), rounding=ROUND_CEILING)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.fatura.calcular_totais()

class Despesa(models.Model):
    TIPOS = (
        ('FORNECEDOR', 'Fornecedor'),
        ('SALARIO', 'Salário'),
        ('SERVICO', 'Serviço'),
        ('OUTRO', 'Outro'),
    )
    
    numero = models.CharField(max_length=50, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='despesas_reg')
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, related_name='despesas', null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='FORNECEDOR')
    descricao = models.CharField(max_length=255)
    data = models.DateField(default=timezone.now)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    observacoes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.numero:
            # Gerar número sequencial por empresa: DP/ANO/00001
            ano = timezone.now().year
            ultimo = Despesa.objects.filter(empresa=self.empresa, numero__contains=f"DP/{ano}/").order_by('-id').first()
            if ultimo:
                seq = int(ultimo.numero.split('/')[-1]) + 1
            else:
                seq = 1
            self.numero = f"DP/{ano}/{seq:05d}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero} - {self.descricao}"
    
    class Meta:
        verbose_name = "Despesa"
        verbose_name_plural = "Despesas"
        ordering = ['-data']
        unique_together = ('numero', 'empresa')

class Compra(models.Model):
    ESTADOS = (
        ('RASCUNHO', 'Rascunho'),
        ('REGISTADA', 'Registada'),
        ('PAGAMENTO_PARCIAL', 'Pagamento Parcial'),
        ('PAGA', 'Paga'),
        ('ANULADA', 'Anulada'),
    )

    numero = models.CharField(max_length=50, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='compras_reg')
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, related_name='compras')
    data_emissao = models.DateField(default=timezone.now, verbose_name="Data do Documento")
    data_vencimento = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='RASCUNHO')
    referencia_fornecedor = models.CharField(max_length=100, blank=True, null=True, help_text="Ex: Nº da fatura do fornecedor")
    
    # Retenção na Fonte (6.5% ou 15% IPU)
    aplicar_retencao = models.BooleanField(default=False, verbose_name="Aplicar Retenção")
    taxa_retencao = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('6.5'), verbose_name="Taxa de Retenção (%)")
    valor_retencao = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Valor Retido")
    retencao_paga = models.BooleanField(default=False, verbose_name="Retenção Liquidada/DAR Recebido")
    
    # Totais (calculados)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_imposto = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    observacoes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.numero:
            # Gerar número sequencial por empresa: CP/ANO/00001
            ano = timezone.now().year
            ultimo = Compra.objects.filter(empresa=self.empresa, numero__contains=f"CP/{ano}/").order_by('-id').first()
            if ultimo:
                seq = int(ultimo.numero.split('/')[-1]) + 1
            else:
                seq = 1
            self.numero = f"CP/{ano}/{seq:05d}"
            
        super().save(*args, **kwargs)

    def calcular_totais(self):
        self.subtotal = sum(item.total_linha for item in self.itens.all())
        self.total_imposto = sum(item.valor_imposto for item in self.itens.all())
        self.total = self.subtotal + self.total_imposto
        
        if self.aplicar_retencao:
            self.valor_retencao = self.subtotal * (self.taxa_retencao / Decimal('100'))
        else:
            self.valor_retencao = 0
            
        Compra.objects.filter(id=self.id).update(
            subtotal=self.subtotal, 
            total_imposto=self.total_imposto, 
            total=self.total,
            valor_retencao=self.valor_retencao
        )

    @property
    def total_a_pagar(self):
        """Valor líquido a pagar ao fornecedor (Total - Retenção)"""
        return self.total - self.valor_retencao

    @property
    def saldo_pendente(self):
        return self.total - self.total_pago

    @property
    def total_estrangeiro(self):
        taxa = self.empresa.get_taxa_na_data(self.data_emissao)
        if taxa and taxa > 0:
            return self.total / taxa
        return 0

    def __str__(self):
        return f"{self.numero} - {self.fornecedor.nome}"

    class Meta:
        unique_together = ('numero', 'empresa')

class PagamentoCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='pagamentos')
    data = models.DateField(default=timezone.now)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    metodo_pagamento = models.CharField(max_length=50, choices=(('CAIXA', 'Caixa'), ('BANCO', 'Banco')), default='BANCO')
    observacoes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pagamento de {self.valor} Kz para {self.compra.numero}"

    class Meta:
        verbose_name = "Pagamento de Compra"
        verbose_name_plural = "Pagamentos de Compras"

class ItemCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='itens')
    descricao = models.CharField(max_length=255)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    taxa_imposto = models.DecimalField(max_digits=5, decimal_places=2, default=14.00, help_text="Ex: 14 para 14%")
    
    @property
    def total_linha(self):
        return self.quantidade * self.preco_unitario

    @property
    def valor_imposto(self):
        valor = self.total_linha * (self.taxa_imposto / Decimal(100))
        return valor.quantize(Decimal('1'), rounding=ROUND_CEILING)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.compra.calcular_totais()

class LancamentoDiario(models.Model):
    """
    Registo de lançamentos no Diário (Partidas Dobradas)
    """
    TIPOS = (
        ('NORMAL', 'Normal'),
        ('ABERTURA', 'Abertura de Exercício'),
        ('FECHO', 'Fecho de Exercício'),
    )
    
    numero = models.CharField(max_length=50, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='lancamentos_reg')
    tipo = models.CharField(max_length=20, choices=TIPOS, default='NORMAL')
    data = models.DateField(default=timezone.now)
    descricao = models.CharField(max_length=255)
    
    # Referência opcional (Fatura ou Despesa)
    fatura = models.ForeignKey(Fatura, on_delete=models.SET_NULL, null=True, blank=True, related_name='lancamentos')
    compra = models.ForeignKey(Compra, on_delete=models.SET_NULL, null=True, blank=True, related_name='lancamentos')
    despesa = models.ForeignKey(Despesa, on_delete=models.SET_NULL, null=True, blank=True, related_name='lancamentos')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.numero:
            ano = timezone.now().year
            ultimo = LancamentoDiario.objects.filter(empresa=self.empresa, numero__contains=f"LC/{ano}/").order_by('-id').first()
            if ultimo:
                seq = int(ultimo.numero.split('/')[-1]) + 1
            else:
                seq = 1
            self.numero = f"LC/{ano}/{seq:05d}"
        super().save(*args, **kwargs)
    
    @property
    def total_debito(self):
        return sum(m.valor for m in self.movimentos.filter(tipo='D'))

    @property
    def total_credito(self):
        return sum(m.valor for m in self.movimentos.filter(tipo='C'))

    def __str__(self):
        return f"{self.numero} - {self.descricao}"
    
    class Meta:
        verbose_name = "Lançamento Diário"
        verbose_name_plural = "Lançamentos Diário"
        ordering = ['-data', '-id']
        unique_together = ('numero', 'empresa')

class MovimentoRazao(models.Model):
    """
    Movimentos individuais (Débito/Crédito) para cada conta
    """
    TIPO_CHOICES = (
        ('D', 'Débito'),
        ('C', 'Crédito'),
    )
    
    lancamento = models.ForeignKey(LancamentoDiario, on_delete=models.CASCADE, related_name='movimentos')
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT, related_name='movimentos')
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    
    def __str__(self):
        return f"{self.conta.codigo} - {self.get_tipo_display()}: {self.valor}"

# ============================================
# GESTÃO DE STOCKS
# ============================================

class Produto(models.Model):
    """Produtos/Artigos para gestão de stock"""
    TIPO_CHOICES = (
        ('MERCADORIA', 'Mercadoria'),
        ('MATERIA_PRIMA', 'Matéria-Prima'),
        ('PRODUTO_ACABADO', 'Produto Acabado'),
        ('SERVICO', 'Serviço'),
    )
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='produtos')
    codigo = models.CharField(max_length=50, verbose_name="Código/Referência")
    nome = models.CharField(max_length=200, verbose_name="Designação")
    descricao = models.TextField(blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='MERCADORIA')
    
    # Classificação
    categoria = models.CharField(max_length=100, blank=True, null=True)
    unidade = models.CharField(max_length=20, default='UN', help_text="Ex: UN, KG, L, M, CX")
    
    # Preços
    preco_custo = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Preço de Custo")
    preco_venda = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Preço de Venda")
    
    # Stock
    stock_atual = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Stock Atual")
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Stock Mínimo")
    stock_maximo = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Stock Máximo", blank=True, null=True)
    
    # Contabilidade
    conta_stock = models.ForeignKey(Conta, on_delete=models.PROTECT, related_name='produtos_stock', 
                                     null=True, blank=True, help_text="Conta PGC para valorização do stock (Classe 2: 22-Matérias-Primas, 26-Mercadorias)")
    
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        unique_together = ('empresa', 'codigo')
        ordering = ['nome']
    
    def __str__(self):
        return f"{self.codigo} - {self.nome}"
    
    @property
    def valor_stock(self):
        """Valor total do stock atual"""
        return self.stock_atual * self.preco_custo
    
    @property
    def alerta_stock(self):
        """Verifica se está abaixo do stock mínimo"""
        return self.stock_atual < self.stock_minimo

class MovimentoStock(models.Model):
    """Movimentos de entrada/saída de stock"""
    TIPO_CHOICES = (
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
        ('AJUSTE', 'Ajuste'),
        ('INVENTARIO', 'Inventário'),
    )
    
    ORIGEM_CHOICES = (
        ('COMPRA', 'Compra'),
        ('VENDA', 'Venda'),
        ('PRODUCAO', 'Produção'),
        ('DEVOLUCAO', 'Devolução'),
        ('TRANSFERENCIA', 'Transferência'),
        ('AJUSTE_MANUAL', 'Ajuste Manual'),
        ('INVENTARIO', 'Inventário'),
    )
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='movimentos_stock')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='movimentos')
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES)
    
    data = models.DateField(default=timezone.now)
    quantidade = models.DecimalField(max_digits=12, decimal_places=2)
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Referências
    compra = models.ForeignKey('Compra', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimentos_stock')
    fatura = models.ForeignKey('Fatura', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimentos_stock')
    inventario = models.ForeignKey('Inventario', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimentos')
    
    observacoes = models.TextField(blank=True, null=True)
    usuario = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Movimento de Stock"
        verbose_name_plural = "Movimentos de Stock"
        ordering = ['-data', '-created_at']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.produto.codigo} - {self.quantidade} {self.produto.unidade}"
    
    @property
    def valor_total(self):
        return self.quantidade * self.preco_unitario

class Inventario(models.Model):
    """Contagens de inventário físico"""
    ESTADO_CHOICES = (
        ('EM_CURSO', 'Em Curso'),
        ('FINALIZADO', 'Finalizado'),
        ('CANCELADO', 'Cancelado'),
    )
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='inventarios')
    numero = models.CharField(max_length=50, editable=False)
    data = models.DateField(default=timezone.now)
    descricao = models.CharField(max_length=200, verbose_name="Descrição")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='EM_CURSO')
    
    responsavel = models.CharField(max_length=100, blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Inventário"
        verbose_name_plural = "Inventários"
        unique_together = ('empresa', 'numero')
        ordering = ['-data', '-created_at']
    
    def save(self, *args, **kwargs):
        if not self.numero:
            ano = timezone.now().year
            ultimo = Inventario.objects.filter(empresa=self.empresa, numero__contains=f"INV/{ano}/").order_by('-id').first()
            if ultimo:
                seq = int(ultimo.numero.split('/')[-1]) + 1
            else:
                seq = 1
            self.numero = f"INV/{ano}/{seq:05d}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.numero} - {self.descricao}"

class LinhaInventario(models.Model):
    """Linhas de contagem de inventário"""
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name='linhas')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='linhas_inventario')
    
    stock_sistema = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Stock no Sistema")
    stock_contado = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Stock Contado")
    
    preco_custo = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Preço de Custo")
    
    observacoes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Linha de Inventário"
        verbose_name_plural = "Linhas de Inventário"
        unique_together = ('inventario', 'produto')
    
    def __str__(self):
        return f"{self.inventario.numero} - {self.produto.codigo}"
    
    @property
    def diferenca(self):
        """Diferença entre contado e sistema"""
        return self.stock_contado - self.stock_sistema
    
    @property
    def valor_diferenca(self):
        """Valor monetário da diferença"""
        return self.diferenca * self.preco_custo
    
    class Meta:
        verbose_name = "Movimento Razão"
        verbose_name_plural = "Movimentos Razão"
