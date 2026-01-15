# Contabilex - Sistema de Contabilidade (PGC Angolano)

Sistema de gestão contabilística e financeira desenvolvido em Django, adaptado às normas do Plano Geral de Contas (PGC) de Angola.

## 🚀 Funcionalidades

### 📈 Contabilidade

- **Plano de Contas (PGC):** Gestão hierárquica de contas.
- **Lançamentos Diários:** Registo detalhado de movimentos.
- **Relatórios Financeiros:**
  - Balancete de Verificação.
  - Balanço Patrimonial.
  - Demonstração de Resultados.
  - Diário e Razão.
- **Comparativo Anual:** Análise de desempenho face a exercícios anteriores.

### 👥 Gestão de Entidades

- **Clientes e Fornecedores:** Gestão de contas correntes e saldos.
- **Recursos Humanos:** Registo de funcionários, faltas e processamento salarial (IRT/INSS).

### 🛠️ Outros

- **Gestão de Impostos:** Tabelas de IRT, IVA e Imposto de Selo.
- **Importação de Dados:** Suporte para importação de ficheiros Excel.
- **Câmbios:** Histórico de taxas de câmbio (AOA, USD, EUR).

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python 3.12+ / Django 6.0
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla)
- **Base de Dados:** SQLite (Desenvolvimento) / PostgreSQL (Recomendado para Produção)
- **Relatórios:** ReportLab (Geração de PDFs) e OpenPyXL (Excel)

## 📋 Pré-requisitos

- Python 3.12 ou superior
- Pip (Gestor de pacotes do Python)

## 🔧 Instalação e Configuração

1. **Clonar o Repositório:**

   ```bash
   git clone https://github.com/Acf1963/contabilex.git
   cd contabilex
   ```

2. **Ambiente Virtual:**

   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Instalar Dependências:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar Variáveis de Ambiente:**
   Crie um ficheiro `.env` na raiz do projeto (veja `.env.example`).

5. **Migrações da Base de Dados:**

   ```bash
   python manage.py migrate
   ```

6. **Criar Superutilizador (Admin):**

   ```bash
   python manage.py createsuperuser
   ```

7. **Iniciar o Servidor:**
   ```bash
   python manage.py runserver
   ```
   Aceda a `http://127.0.0.1:8000` no seu navegador.

## 📄 Licença

Este projeto está sob a licença [MIT](LICENSE).
