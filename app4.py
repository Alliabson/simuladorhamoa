import streamlit as st
from datetime import datetime, timedelta
from PIL import Image
import locale
from math import ceil, floor
from io import BytesIO
import os
import subprocess
import sys
import re

# --- Configuração de Locale ---
def configure_locale():
    """
    Configura o locale para português do Brasil, tentando várias opções
    para garantir compatibilidade em diferentes ambientes.
    """
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
            except locale.Error:
                try:
                    locale.setlocale(locale.LC_ALL, '')
                except locale.Error:
                    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
                    st.warning("Configuração de locale específica não disponível. Usando padrão internacional.")

configure_locale()

# --- Instalação e Importação de Dependências ---
def install_and_import(package, import_name=None):
    """
    Tenta importar um pacote. Se não estiver disponível, instala-o
    usando pip e tenta importar novamente.
    """
    import_name = import_name or package
    try:
        return __import__(import_name)
    except ImportError:
        st.info(f"Instalando {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        st.success(f"{package} instalado com sucesso.")
        return __import__(import_name)

# Importa as bibliotecas necessárias, garantindo a instalação
pd = install_and_import('pandas')
np = install_and_import('numpy')
FPDF = install_and_import('fpdf2', 'fpdf').FPDF

# --- Carregamento da Logo (Cacheado) ---
@st.cache_data(ttl=86400) # Cache por 24 horas
def load_logo():
    """
    Carrega e redimensiona a imagem da logo.
    """
    try:
        logo = Image.open("JMD HAMOA HORIZONTAL - BRANCO.png")
        logo.thumbnail((300, 300))
        return logo
    except Exception as e:
        st.warning(f"Não foi possível carregar a logo: {str(e)}. Verifique se 'JMD HAMOA HORIZONTAL - BRANCO.png' está no diretório correto.")
        return None

# --- Configuração da Página Streamlit e Tema ---
st.set_page_config(layout="wide")

def set_theme():
    """
    Aplica estilos CSS personalizados para um tema escuro.
    """
    st.markdown("""
    <style>
        /* ... (O CSS longo e inalterado foi omitido para brevidade) ... */
        /* Fundo principal */
        .stApp { background-color: #1E1E1E; }
        [data-testid="stSidebar"] { background-color: #252526; }
        h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #FFFFFF; }
        .stMarkdown p, .stMarkdown li, .stText, .stNumberInput label, .stSelectbox label { color: #E0E0E0; }
        .stTextInput input, .stNumberInput input, .stSelectbox select { background-color: #333333; color: #FFFFFF; border-color: #555555; }
        .stMetric { background-color: #252526; border-radius: 8px; padding: 15px; border-left: 4px solid #4D6BFE; }
        .stMetric label { color: #A0A0A0 !important; }
        .stMetric div { color: #FFFFFF !important; font-size: 24px !important; }
        .dataframe { background-color: #252526 !important; color: #E0E0E0 !important; }
        .dataframe th { background-color: #4D6BFE !important; color: white !important; }
        .dataframe tr:nth-child(even) { background-color: #333333 !important; }
        .dataframe tr:hover { background-color: #444444 !important; }
        .main .block-container { padding: 2rem 1rem !important; }
        [data-testid="column"] { display: flex !important; align-items: center !important; justify-content: flex-start !important; padding: 0 !important; }
        h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stTextInput label, .stNumberInput label, .stSelectbox label, .stDateInput label, .stSubheader, .stDownloadButton label { color: #FFFFFF !important; }
        div[data-testid="stForm"] label, div[data-testid="stVerticalBlock"] > div > div > div > div > label { color: #FFFFFF !important; }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"], div[data-testid="stForm"] button[kind="secondary"], .stDownloadButton button { background-color: #4D6BFE !important; color: white !important; border: none !important; border-radius: 12px !important; padding: 10px 24px !important; font-weight: 600 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important; }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover, div[data-testid="stForm"] button[kind="secondary"]:hover, .stDownloadButton button:hover { background-color: #FF4D4D !important; transform: translateY(-2px) !important; box-shadow: 0 4px 8px rgba(255, 77, 77, 0.2) !important; }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:active, div[data-testid="stForm"] button[kind="secondary"]:active, .stDownloadButton button:active { transform: translateY(0) !important; background-color: #E04444 !important; }
        div[data-testid="stForm"] button > div > p, .stDownloadButton button > div > p { color: white !important; font-size: 14px !important; margin: 0 !important; }
    </style>
    """, unsafe_allow_html=True)


# --- Funções de Cálculo Financeiro ---

def formatar_moeda(valor, simbolo=True):
    try:
        # ... (Função inalterada, omitida para brevidade) ...
        if isinstance(valor, str) and 'R$' in valor: valor = valor.replace('R$', '').strip()
        if valor is None or valor == '': return "R$ 0,00" if simbolo else "0,00"
        if isinstance(valor, str): valor = re.sub(r'\.', '', valor).replace(',', '.'); valor = float(valor)
        valor_abs = abs(valor); parte_inteira = int(valor_abs); parte_decimal = int(round((valor_abs - parte_inteira) * 100))
        parte_inteira_str = f"{parte_inteira:,}".replace(",", "."); valor_formatado = f"{parte_inteira_str},{parte_decimal:02d}"
        if valor < 0: valor_formatado = f"-{valor_formatado}"
        return f"R$ {valor_formatado}" if simbolo else valor_formatado
    except Exception as e: return "R$ 0,00" if simbolo else "0,00"

def calcular_taxas(taxa_mensal_percentual):
    try:
        taxa_mensal_decimal = float(taxa_mensal_percentual) / 100
        return {'mensal': taxa_mensal_decimal}
    except Exception as e:
        st.error(f"Erro ao calcular taxas: {str(e)}")
        return {'mensal': 0}

def ajustar_data_vencimento(data_base, num_periodo=0):
    try:
        if not isinstance(data_base, datetime):
            data_base = datetime.combine(data_base, datetime.min.time())
        
        # A primeira parcela (num_periodo=0) vence na data base.
        # As seguintes vencem nos meses subsequentes.
        ano, mes = data_base.year, data_base.month
        
        total_meses = mes + num_periodo
        ano += (total_meses - 1) // 12
        mes = (total_meses - 1) % 12 + 1
        dia = data_base.day

        try:
            return datetime(ano, mes, dia)
        except ValueError:
            ultimo_dia_do_mes = (datetime(ano, mes % 12 + 1, 1) - timedelta(days=1)).day if mes < 12 else 31
            return datetime(ano, mes, ultimo_dia_do_mes)
    except Exception as e:
        return data_base + timedelta(days=30 * num_periodo)

# --- NOVAS FUNÇÕES DE CÁLCULO PRICE BEGIN ---

@st.cache_data(ttl=3600)
def calcular_pmt_price_begin(valor_financiado, taxa_mensal, qtd_parcelas):
    """
    Calcula o valor da parcela (PMT) para uma Tabela Price com pagamentos no início (Begin).
    """
    if taxa_mensal <= 0:
        return valor_financiado / qtd_parcelas if qtd_parcelas > 0 else 0
    if qtd_parcelas <= 0:
        return 0
    
    # A fórmula para Price Begin (renda antecipada) é PMT = PV / (1 + FVA(n-1))
    # Onde FVA é o Fator de Valor Presente de uma Anuidade
    # (1 + i)^-(n-1) -> O expoente é (n-1) porque a primeira parcela é à vista.
    try:
        fator_anuidade = (1 - (1 + taxa_mensal) ** -(qtd_parcelas - 1)) / taxa_mensal
        fator_total = 1 + fator_anuidade
        pmt = valor_financiado / fator_total
        return round(pmt, 2)
    except (ZeroDivisionError, OverflowError):
        return 0

@st.cache_data(ttl=3600)
def gerar_cronograma_price_begin(valor_financiado, valor_parcela_fixa, qtd_parcelas, data_inicio, taxa_mensal):
    """
    Gera uma tabela de amortização completa pelo sistema Price Begin.
    """
    cronograma = []
    saldo_devedor = round(valor_financiado, 2)
    
    # Parcela 1 (na data do contrato)
    juros_p1 = 0.0
    amortizacao_p1 = valor_parcela_fixa
    saldo_devedor -= amortizacao_p1
    cronograma.append({
        "Item": "Parcela 1",
        "Data_Vencimento": ajustar_data_vencimento(data_inicio, 0).strftime('%d/%m/%Y'),
        "Valor_Parcela": valor_parcela_fixa,
        "Juros": juros_p1,
        "Amortizacao": amortizacao_p1,
        "Saldo_Devedor": saldo_devedor
    })

    # Parcelas 2 a N
    for i in range(1, qtd_parcelas):
        saldo_anterior = saldo_devedor
        juros = round(saldo_anterior * taxa_mensal, 2)
        
        # Ajuste final na última parcela para zerar o saldo
        if i == qtd_parcelas - 1:
            amortizacao = saldo_anterior
            valor_parcela_ajustada = amortizacao + juros
            saldo_devedor = 0.0
            item_parcela = valor_parcela_ajustada
        else:
            amortizacao = round(valor_parcela_fixa - juros, 2)
            saldo_devedor -= amortizacao
            item_parcela = valor_parcela_fixa

        cronograma.append({
            "Item": f"Parcela {i+1}",
            "Data_Vencimento": ajustar_data_vencimento(data_inicio, i).strftime('%d/%m/%Y'),
            "Valor_Parcela": item_parcela,
            "Juros": juros,
            "Amortizacao": amortizacao,
            "Saldo_Devedor": saldo_devedor if saldo_devedor > 0.005 else 0.0 # Zera resíduos pequenos
        })
        
    return cronograma

# --- FUNÇÕES DE EXPORTAÇÃO (ATUALIZADAS) ---

def gerar_pdf(cronograma, dados):
    try:
        pdf = FPDF()
        pdf.add_page()
        # ... (Cabeçalho do PDF inalterado, omitido para brevidade) ...
        pdf.set_font("Arial", 'B', 14); pdf.cell(200, 10, txt="Informações do Imóvel", ln=1, align='L')
        pdf.set_font("Arial", size=12); pdf.cell(200, 10, txt=f"Quadra: {dados.get('quadra', 'NI')}", ln=1); pdf.cell(200, 10, txt=f"Lote: {dados.get('lote', 'NI')}", ln=1); pdf.cell(200, 10, txt=f"Metragem: {dados.get('metragem', 'NI')} m²", ln=1); pdf.ln(5)
        pdf.set_font("Arial", 'B', 14); pdf.cell(200, 10, txt="Simulação de Financiamento - Price Begin", ln=1, align='L')
        pdf.set_font("Arial", size=12); pdf.cell(200, 10, txt=f"Valor Total do Imóvel: {formatar_moeda(dados['valor_total'])}", ln=1); pdf.cell(200, 10, txt=f"Entrada: {formatar_moeda(dados['entrada'])}", ln=1); pdf.cell(200, 10, txt=f"Valor Financiado: {formatar_moeda(dados['valor_financiado'])}", ln=1); pdf.cell(200, 10, txt=f"Taxa Mensal Utilizada: {dados['taxa_mensal']:.3f}%", ln=1); pdf.ln(10)

        pdf.set_font("Arial", 'B', 12)
        colunas = ["Parcela", "Vencimento", "Valor Parcela", "Juros", "Amortização", "Saldo Devedor"]
        larguras = [20, 25, 35, 30, 35, 45]
        
        for col, larg in zip(colunas, larguras):
            pdf.cell(larg, 10, txt=col, border=1, align='C')
        pdf.ln()
        
        pdf.set_font("Arial", size=10)
        
        for item in cronograma:
            pdf.cell(larguras[0], 8, txt=item['Item'], border=1)
            pdf.cell(larguras[1], 8, txt=item['Data_Vencimento'], border=1)
            pdf.cell(larguras[2], 8, txt=formatar_moeda(item['Valor_Parcela'], simbolo=False), border=1, align='R')
            pdf.cell(larguras[3], 8, txt=formatar_moeda(item['Juros'], simbolo=False), border=1, align='R')
            pdf.cell(larguras[4], 8, txt=formatar_moeda(item['Amortizacao'], simbolo=False), border=1, align='R')
            pdf.cell(larguras[5], 8, txt=formatar_moeda(item['Saldo_Devedor'], simbolo=False), border=1, align='R')
            pdf.ln()
        
        return BytesIO(pdf.output())
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {str(e)}")
        return BytesIO()


def gerar_excel(cronograma, dados):
    try:
        install_and_import('openpyxl')
        output = BytesIO()
        
        info_df = pd.DataFrame({
            'Campo': ['Quadra', 'Lote', 'Metragem', 'Valor Total do Imóvel', 'Entrada', 'Valor Financiado', 'Taxa Mensal Utilizada'],
            'Valor': [
                dados.get('quadra', 'NI'), dados.get('lote', 'NI'), f"{dados.get('metragem', 'NI')} m²",
                formatar_moeda(dados.get('valor_total', 0)), formatar_moeda(dados.get('entrada', 0)),
                formatar_moeda(dados.get('valor_financiado', 0)), f"{dados.get('taxa_mensal', 0):.3f}%"
            ]
        })
        
        df_cronograma = pd.DataFrame(cronograma)
        df_cronograma.rename(columns={
            'Amortizacao': 'Amortização',
            'Data_Vencimento': 'Data de Vencimento',
            'Valor_Parcela': 'Valor da Parcela',
            'Saldo_Devedor': 'Saldo Devedor'
        }, inplace=True)
            
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            info_df.to_excel(writer, sheet_name='Informações da Simulação', index=False)
            df_cronograma.to_excel(writer, sheet_name='Cronograma Price Begin', index=False)
            
        output.seek(0)
        return output
    except Exception as e:
        st.error(f"Erro ao gerar Excel: {str(e)}")
        return BytesIO()


# --- Função Principal do Aplicativo Streamlit ---
def main():
    set_theme()
    
    logo = load_logo()
    if logo:
        col1, col2 = st.columns([1, 4])
        with col1: st.image(logo, width=200, use_container_width=False)
        with col2: st.title("**Simulador de Financiamento - JMD HAMOA**")
    else:
        st.title("Simulador de Financiamento")
        
    if 'taxa_mensal' not in st.session_state: st.session_state.taxa_mensal = 0.79
    
    def reset_form():
        st.session_state.clear()
        st.session_state.taxa_mensal = 0.79

    with st.container():
        cols = st.columns(3)
        quadra = cols[0].text_input("Quadra", key="quadra")
        lote = cols[1].text_input("Lote", key="lote")
        metragem = cols[2].text_input("Metragem (m²)", key="metragem")
    
    # ALTERADO: Removidos os campos e lógicas de balões para focar no Price Begin
    with st.form("simulador_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            valor_total = st.number_input("Valor Total do Imóvel (R$)", min_value=0.0, step=1000.0, format="%.2f", key="valor_total")
            entrada = st.number_input("Entrada (R$)", min_value=0.0, step=1000.0, format="%.2f", key="entrada")
            data_input = st.date_input("Data do Contrato (1º Vencimento)", value=datetime.now(), format="DD/MM/YYYY", key="data_input")
        
        with col2:
            qtd_parcelas = st.number_input("Quantidade de Parcelas", min_value=1, max_value=180, step=1, key="qtd_parcelas", value=37)
            if qtd_parcelas > 180: st.warning("A quantidade máxima de parcelas permitida é 180.")
            st.info("O sistema de cálculo é o **Price Begin** (juros antecipados), conforme o ERP UAU.")

        col_b1, col_b2, _ = st.columns([1, 1, 4])
        submitted = col_b1.form_submit_button("Calcular")
        col_b2.form_submit_button("Reiniciar", on_click=reset_form)
    
    if submitted:
        try:
            if 1 <= qtd_parcelas <= 36:
                taxa_mensal_para_calculo = 0.0
            elif 37 <= qtd_parcelas <= 48:
                taxa_mensal_para_calculo = 0.395
            else: # 49 a 180
                taxa_mensal_para_calculo = 0.79

            if valor_total <= 0 or entrada < 0 or valor_total <= entrada:
                st.error("Verifique os valores de 'Total do Imóvel' e 'Entrada'. O valor financiado deve ser maior que zero.")
                return
            
            valor_financiado = round(max(valor_total - entrada, 0), 2)
            taxas = calcular_taxas(taxa_mensal_para_calculo)
            
            # --- LÓGICA DE CÁLCULO ALTERADA PARA PRICE BEGIN ---
            
            # Calcula o valor da parcela fixa (PMT)
            valor_parcela_final = calcular_pmt_price_begin(
                valor_financiado,
                taxas['mensal'],
                qtd_parcelas
            )
            
            # Gera o cronograma de amortização
            cronograma = gerar_cronograma_price_begin(
                valor_financiado,
                valor_parcela_final,
                qtd_parcelas,
                datetime.combine(data_input, datetime.min.time()),
                taxas['mensal']
            )
            
            st.subheader("Resultados da Simulação - Price Begin")
            col_res1, col_res2, col_res3 = st.columns(3)
            
            col_res1.metric("Valor Financiado", formatar_moeda(valor_financiado))
            col_res2.metric("Taxa Mensal Aplicada", f"{taxa_mensal_para_calculo:.3f}%")
            if valor_parcela_final > 0:
                # Exibe o valor da parcela ajustada da última linha do cronograma se houver ajuste
                pmt_display = cronograma[-1]['Valor_Parcela'] if len(cronograma) > 0 else valor_parcela_final
                col_res3.metric("Valor da Parcela", formatar_moeda(pmt_display))

            st.subheader("Cronograma de Amortização")
            if cronograma:
                df_cronograma = pd.DataFrame(cronograma)
                
                df_display = df_cronograma.copy()
                for col in ['Valor_Parcela', 'Juros', 'Amortizacao', 'Saldo_Devedor']:
                    df_display[col] = df_display[col].apply(lambda x: formatar_moeda(x))

                # Renomeando colunas para exibição amigável
                df_display.rename(columns={
                    'Amortizacao': 'Amortização',
                    'Data_Vencimento': 'Data de Vencimento',
                    'Valor_Parcela': 'Valor da Parcela',
                    'Saldo_Devedor': 'Saldo Devedor'
                }, inplace=True)
                st.dataframe(df_display, use_container_width=True, hide_index=True)

                total_juros = df_cronograma['Juros'].sum()
                total_pago = df_cronograma['Valor_Parcela'].sum()
                col_tot1, col_tot2, _ = st.columns(3)
                col_tot1.metric("Total Pago no Financiamento", formatar_moeda(total_pago))
                col_tot2.metric("Total de Juros Pagos", formatar_moeda(total_juros))
            
                st.subheader("Exportar Resultados")
                export_data = {
                    'valor_total': valor_total, 'entrada': entrada, 
                    'taxa_mensal': taxa_mensal_para_calculo, 'valor_financiado': valor_financiado, 
                    'quadra': quadra, 'lote': lote, 'metragem': metragem
                }
                
                col_exp1, col_exp2 = st.columns(2)
                pdf_file = gerar_pdf(cronograma, export_data)
                col_exp1.download_button("Exportar para PDF", pdf_file, "simulacao_price_begin.pdf", "application/pdf")
                
                excel_file = gerar_excel(cronograma, export_data)
                col_exp2.download_button("Exportar para Excel", excel_file, "simulacao_price_begin.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        except Exception as e:
            st.error(f"Ocorreu um erro durante a simulação: {str(e)}. Por favor, verifique os valores inseridos e tente novamente.")

if __name__ == '__main__':
    main()
