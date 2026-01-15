from django import forms
from django.db.models import Q
from .models import Produto, Inventario, LinhaInventario, MovimentoStock

class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['codigo', 'nome', 'descricao', 'tipo', 'categoria', 'unidade',
                  'preco_custo', 'preco_venda', 'stock_minimo', 'stock_maximo', 
                  'conta_stock', 'ativo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: PROD001'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do produto'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'categoria': forms.TextInput(attrs={'class': 'form-control'}),
            'unidade': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'UN'}),
            'preco_custo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preco_venda': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_maximo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'conta_stock': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            # Filtrar contas da Classe 2 (Existências): 22-Matérias Primas, 26-Mercadorias, etc.
            self.fields['conta_stock'].queryset = empresa.contas.filter(
                Q(codigo__startswith='22') | Q(codigo__startswith='26') | Q(codigo__startswith='2')
            ).filter(aceita_lancamentos=True)

class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['data', 'descricao', 'responsavel', 'observacoes']
        widgets = {
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Inventário Mensal Dezembro 2024'}),
            'responsavel': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class LinhaInventarioForm(forms.ModelForm):
    class Meta:
        model = LinhaInventario
        fields = ['produto', 'stock_contado', 'observacoes']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-control'}),
            'stock_contado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class MovimentoStockForm(forms.ModelForm):
    class Meta:
        model = MovimentoStock
        fields = ['produto', 'tipo', 'origem', 'data', 'quantidade', 'preco_unitario', 'observacoes']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'origem': forms.Select(attrs={'class': 'form-control'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preco_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['produto'].queryset = empresa.produtos.filter(ativo=True)
