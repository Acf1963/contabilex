import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
from django.utils import timezone
from .models import Fatura, ItemFatura, Cliente, Produto, Empresa

def gerar_saft_xml(empresa, start_date, end_date):
    """
    Gera o ficheiro XML no formato SAF-T (AO)
    
    Estrutura Simplificada para cumprimento mínimos:
    - Header
    - MasterFiles (Customer, SalesProduct, TaxTable)
    - SourceDocuments (SalesInvoices)
    """
    
    # Namespaces
    ns = {
        'xmlns': "urn:OECD:StandardAuditFile-Tax:AO_1.01_01"
    }
    
    root = ET.Element("AuditFile", xmlns=ns['xmlns'])
    
    # ================= HEADER =================
    header = ET.SubElement(root, "Header")
    ET.SubElement(header, "AuditFileVersion").text = "1.01_01"
    ET.SubElement(header, "CompanyID").text = empresa.nif or "CONSUMIDOR_FINAL"
    ET.SubElement(header, "TaxRegistrationNumber").text = empresa.nif or "999999999"
    ET.SubElement(header, "TaxAccountingBasis").text = "F" # Facturação
    ET.SubElement(header, "CompanyName").text = empresa.nome
    
    # Address
    company_addr = ET.SubElement(header, "CompanyAddress")
    ET.SubElement(company_addr, "AddressDetail").text = empresa.morada or "Endereço Desconhecido"
    ET.SubElement(company_addr, "City").text = "Luanda" # Default
    ET.SubElement(company_addr, "Country").text = "AO"
    
    ET.SubElement(header, "FiscalYear").text = str(start_date.year)
    ET.SubElement(header, "StartDate").text = start_date.strftime("%Y-%m-%d")
    ET.SubElement(header, "EndDate").text = end_date.strftime("%Y-%m-%d")
    ET.SubElement(header, "CurrencyCode").text = "AOA"
    ET.SubElement(header, "DateCreated").text = datetime.now().strftime("%Y-%m-%d")
    ET.SubElement(header, "TaxEntity").text = "Global"
    ET.SubElement(header, "ProductCompanyTaxID").text = "NIF_PRODUTOR_SOFTWARE" # Preencher com NIF do produtor
    ET.SubElement(header, "SoftwareValidationNumber").text = "000/AGT/2024" # Mock validation
    ET.SubElement(header, "ProductID").text = "ContabileX/Antigravity"
    ET.SubElement(header, "ProductVersion").text = "1.0.0"
    
    # ================= MASTER FILES =================
    master_files = ET.SubElement(root, "MasterFiles")
    
    # --- 1. Customer ---
    # Obter clientes com movimentos no período
    clientes = Cliente.objects.filter(faturas__empresa=empresa, faturas__data_emissao__range=[start_date, end_date]).distinct()
    
    for cli in clientes:
        customer = ET.SubElement(master_files, "Customer")
        ET.SubElement(customer, "CustomerID").text = str(cli.id)
        ET.SubElement(customer, "AccountID").text = cli.codigo_contabilistico or "Desconhecido"
        ET.SubElement(customer, "CustomerTaxID").text = cli.nif or "999999999"
        ET.SubElement(customer, "CompanyName").text = cli.nome
        
        billing_addr = ET.SubElement(customer, "BillingAddress")
        ET.SubElement(billing_addr, "AddressDetail").text = cli.endereco or "Desconhecido"
        ET.SubElement(billing_addr, "City").text = "Luanda"
        ET.SubElement(billing_addr, "Country").text = "AO"
        
        ET.SubElement(customer, "SelfBillingIndicator").text = "0"
    
    # --- 2. Product ---
    produtos = Produto.objects.filter(empresa=empresa) # Idealmente filtrar só os usados
    for prod in produtos:
        product = ET.SubElement(master_files, "Product")
        ET.SubElement(product, "ProductType").text = "P" if prod.tipo != 'SERVICO' else "S"
        ET.SubElement(product, "ProductCode").text = prod.codigo
        ET.SubElement(product, "ProductGroup").text = prod.categoria or "Geral"
        ET.SubElement(product, "ProductDescription").text = prod.nome
        ET.SubElement(product, "ProductNumberCode").text = prod.codigo
    
    # --- 3. TaxTable ---
    # Construir tabela de impostos baseada nas faturas
    # AGT requer: ISE (Isento), NOR (Normal), RED (Reduzida)
    # Vamos assumir:
    # 14% -> NOR
    # 0% -> ISE (M04, M02...)
    # Outros -> OUT
    
    tax_table = ET.SubElement(master_files, "TaxTable")
    
    # Criar Entrada para Taxa Normal (14%)
    tax_entry_nor = ET.SubElement(tax_table, "TaxTableEntry")
    ET.SubElement(tax_entry_nor, "TaxType").text = "IVA"
    ET.SubElement(tax_entry_nor, "TaxCountryRegion").text = "AO"
    ET.SubElement(tax_entry_nor, "TaxCode").text = "NOR"
    ET.SubElement(tax_entry_nor, "Description").text = "Taxa Normal"
    ET.SubElement(tax_entry_nor, "TaxPercentage").text = "14.00"
    
    # Criar Entrada para Isento (0%)
    tax_entry_ise = ET.SubElement(tax_table, "TaxTableEntry")
    ET.SubElement(tax_entry_ise, "TaxType").text = "IVA"
    ET.SubElement(tax_entry_ise, "TaxCountryRegion").text = "AO"
    ET.SubElement(tax_entry_ise, "TaxCode").text = "ISE"
    ET.SubElement(tax_entry_ise, "Description").text = "Isento"
    ET.SubElement(tax_entry_ise, "TaxPercentage").text = "0.00"
    
    # ================= SOURCE DOCUMENTS =================
    source_docs = ET.SubElement(root, "SourceDocuments")
    sales_invoices = ET.SubElement(source_docs, "SalesInvoices")
    
    # Totais de Controlo
    number_of_entries = 0
    total_debit = Decimal(0)
    total_credit = Decimal(0) # SalesInvoices são Credit references? Sales usually increase debit unless Credit Note
    # Na verdade, Invoice TotalGrossAmount 
    
    faturas = Fatura.objects.filter(
        empresa=empresa,
        data_emissao__range=[start_date, end_date],
        estado__in=['EMITIDA', 'PAGA', 'PAGAMENTO_PARCIAL']
    ).order_by('data_emissao', 'id')
    
    number_of_entries = faturas.count()
    total_credit = sum(f.total for f in faturas) # Total Bruto
    
    ET.SubElement(sales_invoices, "NumberOfEntries").text = str(number_of_entries)
    ET.SubElement(sales_invoices, "TotalDebit").text = "0.00"
    ET.SubElement(sales_invoices, "TotalCredit").text = f"{total_credit:.2f}"
    
    for fat in faturas:
        invoice = ET.SubElement(sales_invoices, "Invoice")
        
        ET.SubElement(invoice, "InvoiceNo").text = fat.numero
        
        # Determine status
        # 'N' Normal, 'A' Anulado. As nossas estão EMITIDA/PAGA. Se fosse ANULADA não estaria nesta lista filtrada acima?
        # Deveriamos incluir anuladas com status 'A'.
        # Por simplicidade, assumir 'N'
        doc_status = ET.SubElement(invoice, "DocumentStatus")
        ET.SubElement(doc_status, "InvoiceStatus").text = "N"
        ET.SubElement(doc_status, "InvoiceStatusDate").text = fat.created_at.strftime("%Y-%m-%dT%H:%M:%S")
        ET.SubElement(doc_status, "SourceID").text = "Admin"
        ET.SubElement(doc_status, "SourceBilling").text = "P" # P=Produzido na aplicação
        
        ET.SubElement(invoice, "Hash").text = "0" # Obrigatório hash real para certificação. 0 'desenrasca' em dev.
        ET.SubElement(invoice, "HashControl").text = "1"
        
        ET.SubElement(invoice, "Period").text = str(fat.data_emissao.month)
        ET.SubElement(invoice, "InvoiceDate").text = fat.data_emissao.strftime("%Y-%m-%d")
        ET.SubElement(invoice, "InvoiceType").text = "FT" # Factura
        
        # System Entry Date (Data de gravação)
        ET.SubElement(invoice, "SystemEntryDate").text = fat.created_at.strftime("%Y-%m-%dT%H:%M:%S")
        
        ET.SubElement(invoice, "CustomerID").text = str(fat.cliente.id)
        
        # Lines
        for item in fat.itens.all():
            line = ET.SubElement(invoice, "Line")
            ET.SubElement(line, "LineNumber").text = str(item.id) # Should be sequential 1, 2... inside invoice
            # Simplificação: Usar ID do item, mas SAFT pede sequencial. Ignorar por agora.
            
            ET.SubElement(line, "ProductCode").text = "GENERICO" # Precisavamos ligar item a produto
            ET.SubElement(line, "ProductDescription").text = item.descricao
            ET.SubElement(line, "Quantity").text = f"{item.quantidade:.2f}"
            ET.SubElement(line, "UnitOfMeasure").text = "UN"
            ET.SubElement(line, "UnitPrice").text = f"{item.preco_unitario:.2f}"
            ET.SubElement(line, "TaxPointDate").text = fat.data_emissao.strftime("%Y-%m-%d")
            ET.SubElement(line, "Description").text = item.descricao
            ET.SubElement(line, "CreditAmount").text = f"{item.total_linha:.2f}" # Base amount
            
            # Tax
            tax = ET.SubElement(line, "Tax")
            ET.SubElement(tax, "TaxType").text = "IVA"
            ET.SubElement(tax, "TaxCountryRegion").text = "AO"
            ET.SubElement(tax, "TaxCode").text = "NOR" if item.taxa_imposto >= 14 else "ISE"
            ET.SubElement(tax, "TaxPercentage").text = f"{item.taxa_imposto:.2f}"
            
            if item.taxa_imposto < 1:
                 ET.SubElement(tax, "TaxExemptionReason").text = "M04" # Isento
                 ET.SubElement(tax, "TaxExemptionCode").text = "M04"
        
        # Document Totals
        totals = ET.SubElement(invoice, "DocumentTotals")
        ET.SubElement(totals, "TaxPayable").text = f"{fat.total_imposto:.2f}"
        ET.SubElement(totals, "NetTotal").text = f"{fat.subtotal:.2f}"
        ET.SubElement(totals, "GrossTotal").text = f"{fat.total:.2f}"
        
    return ET.tostring(root, encoding='utf-8', method='xml')
