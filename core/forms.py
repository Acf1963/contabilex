from django import forms
from .models import Cliente, Fornecedor, Conta, Empresa
from django.db.models import Q
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nome', 'nif', 'morada', 'ano_exercicio', 'email', 'telefone', 'logo', 'moeda_padrao', 'moeda_estrangeira', 'taxa_cambio', 'plano_modelo', 'pais']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da Empresa'}),
            'nif': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIF'}),
            'morada': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Morada Completa', 'rows': 3}),
            'ano_exercicio': forms.NumberInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email de contacto'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefone'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'plano_modelo': forms.Select(attrs={'class': 'form-control'}),
            'pais': forms.Select(attrs={'class': 'form-control'}),
            'moeda_padrao': forms.Select(attrs={'class': 'form-control'}),
            'moeda_estrangeira': forms.Select(attrs={'class': 'form-control'}),
            'taxa_cambio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
        }

from .models import Cambio

class CambioForm(forms.ModelForm):
    class Meta:
        model = Cambio
        fields = ['data_inicio', 'taxa']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'taxa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
        }

class ClienteForm(forms.ModelForm):
    # Permitimos edição manual do código contabilístico via formulário.
    codigo_contabilistico = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 31.1.1.2.1.00001'}))
    class Meta:
        model = Cliente
        fields = ['nome', 'nif', 'email', 'telefone', 'endereco', 'conta_pai']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Cliente'}),
            'nif': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIF'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefone'}),
            'endereco': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Endereço', 'rows': 3}),
            'conta_pai': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        # Se form estiver a editar uma instância, preenche o campo do código
        try:
            if self.instance and getattr(self.instance, 'pk', None):
                self.fields['codigo_contabilistico'].initial = getattr(self.instance, 'codigo_contabilistico', '')
        except Exception:
            pass
        
        # Permitir selecionar qualquer subconta de Clientes (Classe 31)
        # para diferenciar Nacionais (31.1.X) de Estrangeiros (31.X)
        if empresa:
            self.fields['conta_pai'].queryset = Conta.objects.filter(
                codigo__startswith='31', 
                empresa=empresa,
                aceita_lancamentos=False # A conta PAI não deve aceitar lançamentos, pois vai gerar filho
            ).order_by('codigo')
            
            # Se a lista estiver vazia (início de empresa), tentar usar as contas globais (template)
            if not self.fields['conta_pai'].queryset.exists():
                 self.fields['conta_pai'].queryset = Conta.objects.filter(
                    codigo__startswith='31', 
                    empresa__isnull=True,
                    aceita_lancamentos=False
                ).order_by('codigo')

        else:
             self.fields['conta_pai'].queryset = Conta.objects.filter(codigo__startswith='31', empresa__isnull=True).order_by('codigo')

    def save(self, commit=True):
        # Guardar campos normais primeiro
        instance = super().save(commit=False)

        # Se foi enviado um código contabilístico personalizado, aplicar
        codigo_custom = self.cleaned_data.get('codigo_contabilistico')
        if codigo_custom:
            instance.codigo_contabilistico = codigo_custom

        if commit:
            instance.save()

            # Garantir que existe/atualiza a conta associada ao código contabilístico
            try:
                defaults = {
                    'classe': instance.conta_pai.classe,
                    'descricao': instance.nome,
                    'conta_pai': instance.conta_pai,
                    'tipo': 'MOVIMENTO',
                    'tipo_entidade': 'CLIENTE',
                    'aceita_lancamentos': True,
                }
                from .models import Conta
                Conta.objects.update_or_create(
                    codigo=instance.codigo_contabilistico,
                    empresa=instance.empresa,
                    defaults=defaults
                )
            except Exception:
                # Não falhar o processo de save por conta de problemas na sincronização
                pass

        return instance

class FornecedorForm(forms.ModelForm):
    # Permitimos edição manual do código contabilístico via formulário.
    codigo_contabilistico = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 32.1.1.2.1.00001'}))
    
    class Meta:
        model = Fornecedor
        fields = ['nome', 'nif', 'email', 'telefone', 'endereco', 'conta_pai']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Fornecedor'}),
            'nif': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIF'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefone'}),
            'endereco': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Endereço', 'rows': 3}),
            'conta_pai': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        # Se form estiver a editar uma instância, preenche o campo do código
        try:
            if self.instance and getattr(self.instance, 'pk', None):
                self.fields['codigo_contabilistico'].initial = getattr(self.instance, 'codigo_contabilistico', '')
        except Exception:
            pass
        
        # Permitir selecionar qualquer subconta de Fornecedores (Classe 32)
        if empresa:
            self.fields['conta_pai'].queryset = Conta.objects.filter(
                codigo__startswith='32', 
                empresa=empresa,
                aceita_lancamentos=False
            ).order_by('codigo')
            
            if not self.fields['conta_pai'].queryset.exists():
                self.fields['conta_pai'].queryset = Conta.objects.filter(
                    codigo__startswith='32', 
                    empresa__isnull=True,
                    aceita_lancamentos=False
                ).order_by('codigo')

        else:
             self.fields['conta_pai'].queryset = Conta.objects.filter(codigo__startswith='32', empresa__isnull=True).order_by('codigo')

    def save(self, commit=True):
        # Guardar campos normais primeiro
        instance = super().save(commit=False)

        # Se foi enviado um código contabilístico personalizado, aplicar
        codigo_custom = self.cleaned_data.get('codigo_contabilistico')
        if codigo_custom:
            instance.codigo_contabilistico = codigo_custom

        if commit:
            instance.save()

            # Garantir que existe/atualiza a conta associada ao código contabilístico
            try:
                defaults = {
                    'classe': instance.conta_pai.classe,
                    'descricao': instance.nome,
                    'conta_pai': instance.conta_pai,
                    'tipo': 'MOVIMENTO',
                    'tipo_entidade': 'FORNECEDOR',
                    'aceita_lancamentos': True,
                }
                from .models import Conta
                Conta.objects.update_or_create(
                    codigo=instance.codigo_contabilistico,
                    empresa=instance.empresa,
                    defaults=defaults
                )
            except Exception:
                # Não falhar o processo de save por conta de problemas na sincronização
                pass

        return instance

from .models import Fatura, ItemFatura, Compra, ItemCompra

class FaturaForm(forms.ModelForm):
    class Meta:
        model = Fatura
        fields = ['cliente', 'data_vencimento', 'aplicar_retencao', 'taxa_retencao', 'observacoes']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-control'}),
            'data_vencimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observações da Fatura'}),
            'aplicar_retencao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'taxa_retencao': forms.Select(choices=[(6.5, 'Serviços (6.5%)'), (15.0, 'IPU - Rendas (15%)')], attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa)

class ItemFaturaForm(forms.ModelForm):
    class Meta:
        model = ItemFatura
        fields = ['descricao', 'quantidade', 'preco_unitario', 'taxa_imposto']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrição do serviço/produto'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preco_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'taxa_imposto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

ItemFaturaFormSet = forms.inlineformset_factory(
    Fatura, 
    ItemFatura, 
    form=ItemFaturaForm,
    extra=1,
    can_delete=True
)

from .models import Despesa

class DespesaForm(forms.ModelForm):
    class Meta:
        model = Despesa
        fields = ['fornecedor', 'tipo', 'descricao', 'data', 'valor', 'observacoes']
        widgets = {
            'fornecedor': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrição da despesa'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observações'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(empresa=empresa)

class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['fornecedor', 'data_emissao', 'data_vencimento', 'referencia_fornecedor', 'observacoes', 'aplicar_retencao', 'taxa_retencao']
        widgets = {
            'fornecedor': forms.Select(attrs={'class': 'form-control'}),
            'data_emissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_vencimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'referencia_fornecedor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nº da fatura do fornecedor'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observações da Compra'}),
            'aplicar_retencao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'taxa_retencao': forms.Select(choices=[(6.5, 'Serviços (6.5%)'), (15.0, 'IPU - Rendas (15%)')], attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(empresa=empresa)

class ItemCompraForm(forms.ModelForm):
    class Meta:
        model = ItemCompra
        fields = ['descricao', 'quantidade', 'preco_unitario', 'taxa_imposto']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrição do item'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preco_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'taxa_imposto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

ItemCompraFormSet = forms.inlineformset_factory(
    Compra, 
    ItemCompra, 
    form=ItemCompraForm,
    extra=1,
    can_delete=True
)

from .models import PagamentoFatura, PagamentoCompra

class PagamentoFaturaForm(forms.ModelForm):
    class Meta:
        model = PagamentoFatura
        fields = ['data', 'valor', 'metodo_pagamento', 'observacoes']
        widgets = {
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'metodo_pagamento': forms.Select(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observações do pagamento'}),
        }

class PagamentoCompraForm(forms.ModelForm):
    class Meta:
        model = PagamentoCompra
        fields = ['data', 'valor', 'metodo_pagamento', 'observacoes']
        widgets = {
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'metodo_pagamento': forms.Select(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observações do pagamento'}),
        }

from .models import LancamentoDiario, MovimentoRazao

class LancamentoAberturaForm(forms.ModelForm):
    class Meta:
        model = LancamentoDiario
        fields = ['data', 'descricao']
        widgets = {
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Balanço de Abertura 2025'}),
        }

class MovimentoAberturaForm(forms.ModelForm):
    class Meta:
        model = MovimentoRazao
        fields = ['conta', 'tipo', 'valor']
        widgets = {
            'conta': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
        }

MovimentoAberturaFormSet = forms.inlineformset_factory(
    LancamentoDiario,
    MovimentoRazao,
    form=MovimentoAberturaForm,
    extra=10, # Oferecer 10 linhas iniciais para o balanço de abertura
    can_delete=True
)

class LancamentoManualForm(forms.ModelForm):
    class Meta:
        model = LancamentoDiario
        fields = ['data', 'descricao']
        widgets = {
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrição do lançamento...'}),
        }

class MovimentoManualForm(forms.ModelForm):
    class Meta:
        model = MovimentoRazao
        fields = ['conta', 'tipo', 'valor']
        widgets = {
            'conta': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            # Mostrar contas globais (empresa=None) E contas desta empresa
            self.fields['conta'].queryset = Conta.objects.filter(
                Q(empresa=empresa) | Q(empresa__isnull=True),
                aceita_lancamentos=True
            ).order_by('codigo')

MovimentoManualFormSet = forms.inlineformset_factory(
    LancamentoDiario,
    MovimentoRazao,
    form=MovimentoManualForm,
    extra=2,
    can_delete=True
)

class ContaForm(forms.ModelForm):
    class Meta:
        model = Conta
        fields = ['classe', 'codigo', 'descricao', 'conta_pai', 'tipo', 'tipo_entidade', 'aceita_lancamentos']
        widgets = {
            'classe': forms.Select(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 11.1.1'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrição da conta'}),
            'conta_pai': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'tipo_entidade': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            from django.db.models import Q
            self.fields['conta_pai'].queryset = Conta.objects.filter(
                Q(empresa=empresa) | Q(empresa__isnull=True)
            ).order_by('codigo')
        else:
            self.fields['conta_pai'].queryset = Conta.objects.filter(empresa__isnull=True).order_by('codigo')

class ImportarPGCForm(forms.Form):
    arquivo = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))

class ProcessamentoVariaveisForm(forms.Form):
    horas_falta = forms.DecimalField(label='Faltas (Horas)', min_value=0, max_value=720, required=False, initial=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'placeholder': 'Ex: 4 para meio dia, 8 para dia'}))
    horas_50 = forms.DecimalField(label='Horas Extras (50%)', min_value=0, decimal_places=2, required=False, initial=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}))
    horas_100 = forms.DecimalField(label='Horas Extras (100%)', min_value=0, decimal_places=2, required=False, initial=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}))

from .models import Funcionario

class FuncionarioForm(forms.ModelForm):
    class Meta:
        model = Funcionario
        fields = ['nome', 'nif', 'numero_seguranca_social', 'cargo', 'data_admissao', 'salario_base', 'subsidio_alimentacao', 'subsidio_transporte', 'outros_abonos', 'telefone', 'endereco', 'banco', 'iban', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome Completo'}),
            'nif': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIF'}),
            'numero_seguranca_social': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nº SS'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cargo / Função'}),
            'data_admissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'salario_base': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'subsidio_alimentacao': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'subsidio_transporte': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'outros_abonos': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefone'}),
            'endereco': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Endereço Completo', 'rows': 3}),
            'banco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Banco'}),
            'iban': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'IBAN'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

from .models import TabelaIRT, Falta, HoraExtra

class TabelaIRTForm(forms.ModelForm):
    class Meta:
        model = TabelaIRT
        fields = ['limite', 'taxa', 'parcela_fixa', 'excesso']
        widgets = {
            'limite': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'taxa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'parcela_fixa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'excesso': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class FaltaForm(forms.ModelForm):
    class Meta:
        model = Falta
        fields = ['funcionario', 'data', 'horas', 'justificada', 'motivo', 'comprovativo']
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-control'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'horas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'motivo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Motivo da ausência'}),
            'comprovativo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['funcionario'].queryset = Funcionario.objects.filter(empresa=empresa, ativo=True)

class HoraExtraForm(forms.ModelForm):
    class Meta:
        model = HoraExtra
        fields = ['funcionario', 'data', 'horas', 'tipo', 'motivo', 'aprovado_por']
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-control'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'horas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'motivo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Motivo/Trabalho realizado'}),
            'aprovado_por': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Aprovado por'}),
        }
    
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['funcionario'].queryset = Funcionario.objects.filter(empresa=empresa, ativo=True)

class UsuarioForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Confirmar Senha")
    
    class Meta:
        model = User
        fields = ['username', 'email', 'groups', 'is_staff', 'is_superuser']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("As senhas não coincidem.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

