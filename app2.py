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
    Tenta importar um pacote. Se não estiver disponível, instala-o.
    """
    import_name = import_name or package
    try:
        return __import__(import_name)
    except ImportError:
        st.info(f"Instalando {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        st.success(f"{package} instalado com sucesso.")
        return __import__(import_name)

# Importa as bibliotecas necessárias
pd = install_and_import('pandas')
np = install_and_import('numpy')
FPDF = install_and_import('fpdf2', 'fpdf').FPDF

# --- Carregamento da Logo (Cacheado) ---
@st.cache_data(ttl=86400)
def load_logo():
    """
    Carrega e redimensiona a imagem da logo.
    """
    try:
        logo = Image.open("JMD HAMOA HORIZONTAL - BRANCO.png")
        logo.thumbnail((300, 300))
        return logo
    except Exception as e:
        st.warning(f"Não foi possível carregar a logo: {str(e)}.")
        return None

# --- Configuração da Página Streamlit e Tema ---
st.set_page_config(layout="wide")

def set_theme():
    """
    Aplica estilos CSS personalizados para um tema escuro
    e aprimora a aparência dos componentes do Streamlit.
    Inclui estilos para botões com efeitos de hover e clique.
    """
    st.markdown("""
    <style>
        /* Fundo principal */
        .stApp {
            background-color: #1E1E1E;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #252526;
        }
        
        /* Títulos */
        h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            color: #FFFFFF;
        }
        
        /* Texto geral */
        .stMarkdown p, .stMarkdown li, .stText, .stNumberInput label, .stSelectbox label {
            color: #E0E0E0;
        }
        
        /* Inputs */
        .stTextInput input, .stNumberInput input, .stSelectbox select {
            background-color: #333333;
            color: #FFFFFF;
            border-color: #555555;
        }
        
        /* Botões padrão (não os customizados abaixo) */
        .stButton button {
            background-color: #0056b3;
            color: white;
            border: none;
            border-radius: 4px;
        }
        
        .stButton button:hover {
            background-color: #003d82;
        }
        
        /* Cards/metricas */
        .stMetric {
            background-color: #252526;
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid #4D6BFE; /* Cor da borda alterada para combinar com os botões */
        }
        
        .stMetric label {
            color: #A0A0A0 !important;
        }
        
        .stMetric div {
            color: #FFFFFF !important;
            font-size: 24px !important;
        }
        
        /* Dataframe */
        .dataframe {
            background-color: #252526 !important;
            color: #E0E0E0 !important;
        }
        
        .dataframe th {
            background-color: #4D6BFE !important; /* Cor do cabeçalho alterada */
            color: white !important;
        }
        
        .dataframe tr:nth-child(even) {
            background-color: #333333 !important;
        }
        
        .dataframe tr:hover {
            background-color: #444444 !important;
        }

        /* ===== LAYOUT ===== */
        /* Container principal */
        .main .block-container {
            padding: 2rem 1rem !important;
        }

        /* Colunas e alinhamento */
        [data-testid="column"] {
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            padding: 0 !important;
        }

        /* Espaçamento entre botões */
        .stButton:first-of-type {
            margin-right: 8px !important;
        }

        /* ===== FLICKERING FIX ===== */
        [data-testid="stDataFrame-container"] {
            will-change: transform !important;
            contain: strict !important;
            min-height: 400px !important;
            transform: translate3d(0, 0, 0) !important;
            backface-visibility: hidden !important;
            perspective: 1000px !important;
        }

        .stDataFrame-fullscreen {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            z-index: 9999 !important;
            background-color: #0E1117 !important;
            padding: 2rem !important;
            overflow: auto !important;
        }

        /* Títulos específicos para cor branca */
        h1, h2, h3, h4, h5, h6, 
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
        /* Textos de input/labels */
        .stTextInput label, .stNumberInput label, 
        .stSelectbox label, .stDateInput label,
        /* Subtítulos das seções */
        .stSubheader,
        /* Botões de exportação (labels) */
        .stDownloadButton label {
            color: #FFFFFF !important;
        }
        
        /* Labels específicos que não são capturados pelas regras acima */
        div[data-testid="stForm"] label,
        div[data-testid="stVerticalBlock"] > div > div > div > div > label {
            color: #FFFFFF !important;
        }

        /* BOTÕES PRINCIPAIS - ESTADO NORMAL (Calcular/Reiniciar/Exportar) */
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"],
        div[data-testid="stForm"] button[kind="secondary"],
        .stDownloadButton button {
            background-color: #4D6BFE !important; /* Azul vibrante */
            color: white !important;
            border: none !important;
            border-radius: 12px !important; /* Bordas super arredondadas */
            padding: 10px 24px !important;
            font-weight: 600 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }

        /* EFEITO HOVER - VERMELHO INTENSO */
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover,
        div[data-testid="stForm"] button[kind="secondary"]:hover,
        .stDownloadButton button:hover {
            background-color: #FF4D4D !important; /* Vermelho vibrante */
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 8px rgba(255, 77, 77, 0.2) !important;
        }

        /* EFEITO CLIQUE */
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:active,
        div[data-testid="stForm"] button[kind="secondary"]:active,
        .stDownloadButton button:active {
            transform: translateY(0) !important;
            background-color: #E04444 !important; /* Vermelho mais escuro */
        }

        /* TEXTO DOS BOTÕES */
        div[data-testid="stForm"] button > div > p,
        .stDownloadButton button > div > p {
            color: white !important;
            font-size: 14px !important;
            margin: 0 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    

# --- Funções de Cálculo Financeiro ---

def parse_currency(value_str: str) -> float:
    """
    Converte uma string de valor monetário para float.
    Aceita formatos como "R$ 150.000,50", "150.000,50", "150000,50", etc.
    """
    if not isinstance(value_str, str) or not value_str.strip():
        return 0.0
    try:
        # Remove símbolos de moeda, espaços e pontos de milhar
        cleaned_value = re.sub(r'[R$\s\.]', '', value_str.strip())
        # Substitui vírgula decimal por ponto
        cleaned_value = cleaned_value.replace(',', '.')
        return float(cleaned_value)
    except (ValueError, TypeError):
        return 0.0

def formatar_moeda(valor, simbolo=True):
    try:
        if isinstance(valor, str) and 'R$' in valor: valor = valor.replace('R$', '').strip()
        if valor is None or valor == '': return "R$ 0,00" if simbolo else "0,00"
        if isinstance(valor, str): valor = re.sub(r'\.', '', valor).replace(',', '.'); valor = float(valor)
        valor_abs, parte_inteira = abs(valor), int(abs(valor))
        parte_decimal = int(round((valor_abs - parte_inteira) * 100))
        parte_inteira_str = f"{parte_inteira:,}".replace(",", ".")
        valor_formatado = f"{parte_inteira_str},{parte_decimal:02d}"
        if valor < 0: valor_formatado = f"-{valor_formatado}"
        return f"R$ {valor_formatado}" if simbolo else valor_formatado
    except Exception: return "R$ 0,00" if simbolo else "0,00"

def calcular_taxas(taxa_mensal_percentual):
    try:
        taxa_mensal_decimal = float(taxa_mensal_percentual) / 100
        taxa_anual = ((1 + taxa_mensal_decimal) ** 12) - 1
        taxa_semestral = ((1 + taxa_mensal_decimal) ** 6) - 1
        taxa_diaria = ((1 + taxa_mensal_decimal) ** (1/30.4375)) - 1
        return {'anual': taxa_anual, 'semestral': taxa_semestral, 'mensal': taxa_mensal_decimal, 'diaria': taxa_diaria}
    except Exception: return {'anual': 0, 'semestral': 0, 'mensal': 0, 'diaria': 0}

def calcular_valor_presente(valor_futuro, taxa_diaria, dias):
    try:
        if dias <= 0 or taxa_diaria <= 0: return float(valor_futuro)
        return round(float(valor_futuro) / ((1 + taxa_diaria) ** dias), 2)
    except Exception: return float(valor_futuro)

def calcular_fator_vp(datas_vencimento, data_inicio, taxa_diaria):
    if taxa_diaria <= 0: return len(datas_vencimento)
    fator_total = 0.0
    for data_venc in datas_vencimento:
        if not isinstance(data_venc, datetime): data_venc = datetime.strptime(data_venc, '%d/%m/%Y')
        dias = (data_venc - data_inicio).days
        if dias > 0: fator_total += 1 / ((1 + taxa_diaria) ** dias)
    return fator_total

def ajustar_data_vencimento(data_base, periodo, num_periodo=1, dia_vencimento=None):
    try:
        if not isinstance(data_base, datetime): data_base = datetime.combine(data_base, datetime.min.time())
        ano, mes, dia = data_base.year, data_base.month, data_base.day if dia_vencimento is None else dia_vencimento
        if periodo == "mensal":
            total_meses = mes + num_periodo; ano += (total_meses - 1) // 12; mes = (total_meses - 1) % 12 + 1
        elif periodo == "semestral":
            total_meses = mes + (6 * num_periodo); ano += (total_meses - 1) // 12; mes = (total_meses - 1) % 12 + 1
        elif periodo == "anual": ano += num_periodo
        try: return datetime(ano, mes, dia)
        except ValueError:
            ultimo_dia = (datetime(ano, mes % 12 + 1, 1) - timedelta(days=1)).day if mes < 12 else 31
            return datetime(ano, mes, ultimo_dia)
    except Exception: return data_base + timedelta(days=30 * num_periodo)

def determinar_modo_calculo(modalidade):
    return {"mensal": 1, "mensal + balão": 2, "só balão anual": 3, "só balão semestral": 4}.get(modalidade, 1)

def atualizar_baloes(modalidade, qtd_parcelas, tipo_balao=None):
    try:
        qtd_parcelas = int(qtd_parcelas)
        if modalidade == "mensal + balão":
            intervalo = 12 if tipo_balao == "anual" else 6
            return qtd_parcelas // intervalo if intervalo > 0 else 0
        elif modalidade == "só balão anual": return max(ceil(qtd_parcelas / 12), 0)
        elif modalidade == "só balão semestral": return max(ceil(qtd_parcelas / 6), 0)
        return 0
    except Exception: return 0

@st.cache_data(ttl=3600)
def gerar_cronograma(valor_financiado, valor_parcela_final, valor_balao_final,
                     qtd_parcelas, qtd_baloes, modalidade, tipo_balao,
                     data_entrada, taxas, valor_ultima_parcela=None, valor_ultimo_balao=None,
                     agendamento_baloes=None, meses_baloes=None, mes_primeiro_balao=None):
    try:
        dia_vencimento = data_entrada.day
        parcelas, baloes = [], []

        if modalidade in ["mensal", "mensal + balão"]:
            for i in range(1, qtd_parcelas + 1):
                valor_corrente = valor_ultima_parcela if (i == qtd_parcelas and valor_ultima_parcela is not None) else valor_parcela_final
                data_vencimento = ajustar_data_vencimento(data_entrada, "mensal", i, dia_vencimento)
                dias = (data_vencimento - data_entrada).days
                vp = calcular_valor_presente(valor_corrente, taxas['diaria'], dias)
                parcelas.append({"Item": f"Parcela {i}", "Tipo": "Parcela", "Data_Vencimento": data_vencimento.strftime('%d/%m/%Y'), "Dias": dias, "Valor": round(valor_corrente, 2), "Valor_Presente": round(vp, 2), "Desconto_Aplicado": round(valor_corrente - vp, 2)})
        
        periodo_map = {"só balão anual": "anual", "só balão semestral": "semestral"}
        if modalidade in periodo_map:
            periodo = periodo_map[modalidade]
            for i in range(1, qtd_baloes + 1):
                valor_corrente = valor_ultimo_balao if (i == qtd_baloes and valor_ultimo_balao is not None) else valor_balao_final
                data_vencimento = ajustar_data_vencimento(data_entrada, periodo, i, dia_vencimento)
                dias = (data_vencimento - data_entrada).days
                vp = calcular_valor_presente(valor_corrente, taxas['diaria'], dias)
                baloes.append({"Item": f"Balão {i}", "Tipo": "Balão", "Data_Vencimento": data_vencimento.strftime('%d/%m/%Y'), "Dias": dias, "Valor": round(valor_corrente, 2), "Valor_Presente": round(vp, 2), "Desconto_Aplicado": round(valor_corrente - vp, 2)})

        if modalidade == "mensal + balão":
            datas_baloes_a_gerar = []
            if agendamento_baloes == "Personalizado (Mês a Mês)":
                datas_baloes_a_gerar = [ajustar_data_vencimento(data_entrada, "mensal", mes, dia_vencimento) for mes in meses_baloes]
            elif agendamento_baloes == "A partir do 1º Vencimento":
                data_base_balao = ajustar_data_vencimento(data_entrada, "mensal", mes_primeiro_balao, dia_vencimento)
                datas_baloes_a_gerar = [ajustar_data_vencimento(data_base_balao, tipo_balao, i) for i in range(qtd_baloes)]
            else: # Padrão
                intervalo = 12 if tipo_balao == "anual" else 6
                datas_baloes_a_gerar = [ajustar_data_vencimento(data_entrada, "mensal", i * intervalo, dia_vencimento) for i in range(1, qtd_baloes + 1)]
            
            for i, data_vencimento in enumerate(datas_baloes_a_gerar):
                balao_count = i + 1
                valor_corrente = valor_ultimo_balao if (balao_count == qtd_baloes and valor_ultimo_balao is not None) else valor_balao_final
                dias = (data_vencimento - data_entrada).days
                vp = calcular_valor_presente(valor_corrente, taxas['diaria'], dias)
                baloes.append({"Item": f"Balão {balao_count}", "Tipo": "Balão", "Data_Vencimento": data_vencimento.strftime('%d/%m/%Y'), "Dias": dias, "Valor": round(valor_corrente, 2), "Valor_Presente": round(vp, 2), "Desconto_Aplicado": round(valor_corrente - vp, 2)})
        
        cronograma = parcelas + baloes
        if cronograma:
            total_valor = round(sum(p['Valor'] for p in cronograma), 2)
            cronograma.append({"Item": "TOTAL", "Tipo": "", "Data_Vencimento": "", "Dias": "", "Valor": total_valor, "Valor_Presente": valor_financiado, "Desconto_Aplicado": round(total_valor - valor_financiado, 2)})
        
        return cronograma
    except Exception as e:
        st.error(f"Erro inesperado ao gerar cronograma: {str(e)}.")
        return []

def gerar_pdf(cronograma, dados):
    try:
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Informações do Imóvel", ln=1, align='L'); pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Quadra: {dados.get('quadra', 'N/I')}", ln=1); pdf.cell(200, 10, txt=f"Lote: {dados.get('lote', 'N/I')}", ln=1); pdf.cell(200, 10, txt=f"Metragem: {dados.get('metragem', 'N/I')} m²", ln=1)
        pdf.ln(5); pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Simulação de Financiamento", ln=1, align='L'); pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Valor Total do Imóvel: {formatar_moeda(dados['valor_total'])}", ln=1); pdf.cell(200, 10, txt=f"Entrada: {formatar_moeda(dados['entrada'])}", ln=1); pdf.cell(200, 10, txt=f"Valor Financiado: {formatar_moeda(dados['valor_financiado'])}", ln=1); pdf.cell(200, 10, txt=f"Taxa Mensal Utilizada: {dados['taxa_mensal']:.2f}%", ln=1)
        pdf.ln(10); pdf.set_font("Arial", 'B', 12)
        colunas = ["Item", "Tipo", "Data Venc.", "Valor", "Valor Presente", "Desconto Aplicado"]; larguras = [30, 25, 30, 35, 35, 35]
        for col, larg in zip(colunas, larguras): pdf.cell(larg, 10, txt=col, border=1, align='C')
        pdf.ln(); pdf.set_font("Arial", size=10)
        cronograma_sem_total = [p for p in cronograma if p['Item'] != 'TOTAL']
        for item in cronograma_sem_total:
            pdf.cell(larguras[0], 8, txt=item['Item'], border=1); pdf.cell(larguras[1], 8, txt=item['Tipo'], border=1); pdf.cell(larguras[2], 8, txt=item['Data_Vencimento'], border=1)
            pdf.cell(larguras[3], 8, txt=formatar_moeda(item['Valor'], simbolo=False), border=1, align='R'); pdf.cell(larguras[4], 8, txt=formatar_moeda(item['Valor_Presente'], simbolo=False), border=1, align='R'); pdf.cell(larguras[5], 8, txt=formatar_moeda(item['Desconto_Aplicado'], simbolo=False), border=1, align='R'); pdf.ln()
        total = next((p for p in cronograma if p['Item'] == 'TOTAL'), None)
        if total:
            pdf.set_font("Arial", 'B', 10); pdf.cell(sum(larguras[:3]), 10, txt="TOTAL", border=1, align='R')
            pdf.cell(larguras[3], 10, txt=formatar_moeda(total['Valor'], simbolo=False), border=1, align='R'); pdf.cell(larguras[4], 10, txt=formatar_moeda(total['Valor_Presente'], simbolo=False), border=1, align='R'); pdf.cell(larguras[5], 10, txt=formatar_moeda(total['Desconto_Aplicado'], simbolo=False), border=1, align='R')
        return BytesIO(pdf.output())
    except Exception as e: st.error(f"Erro ao gerar PDF: {str(e)}"); return BytesIO()

def gerar_excel(cronograma, dados):
    try:
        install_and_import('openpyxl'); output = BytesIO()
        info_df = pd.DataFrame({'Campo': ['Quadra', 'Lote', 'Metragem', 'Valor Total do Imóvel', 'Entrada', 'Valor Financiado', 'Taxa Mensal Utilizada'], 'Valor': [dados.get('quadra', 'N/I'), dados.get('lote', 'N/I'), f"{dados.get('metragem', 'N/I')} m²", formatar_moeda(dados.get('valor_total', 0)), formatar_moeda(dados.get('entrada', 0)), formatar_moeda(dados.get('valor_financiado', 0)), f"{dados.get('taxa_mensal', 0):.2f}%"]})
        df_cronograma_data = pd.DataFrame([p for p in cronograma if p['Item'] != 'TOTAL'])
        total_row = next((p for p in cronograma if p['Item'] == 'TOTAL'), None)
        df_final = pd.concat([df_cronograma_data, pd.DataFrame([total_row])], ignore_index=True) if total_row else df_cronograma_data
        df_export = df_final[['Item', 'Tipo', 'Data_Vencimento', 'Valor', 'Valor_Presente', 'Desconto_Aplicado']]
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            info_df.to_excel(writer, sheet_name='Informações da Simulação', index=False)
            df_export.to_excel(writer, sheet_name='Cronograma de Pagamentos', index=False)
        output.seek(0); return output
    except Exception as e: st.error(f"Erro ao gerar Excel: {str(e)}"); return BytesIO()

# --- Função Principal do Aplicativo Streamlit ---
def main():
    set_theme()
    st.write("\n")
    logo = load_logo()
    if logo:
        col1, col2 = st.columns([1, 4]); col1.image(logo, width=200, use_container_width=False)
        col2.title("**Seja bem vindo ao Simulador da JMD HAMOA**")
    else: st.title("Simulador Imobiliária Celeste")
        
    if 'taxa_mensal' not in st.session_state: st.session_state.taxa_mensal = 0.89
    
    def reset_form(): 
        taxa_atual = st.session_state.taxa_mensal
        st.session_state.clear()
        st.session_state.taxa_mensal = taxa_atual

    with st.container():
        cols = st.columns(3); quadra = cols[0].text_input("Quadra", key="quadra", placeholder="Ex: 15")
        lote = cols[1].text_input("Lote", key="lote", placeholder="Ex: 22"); metragem = cols[2].text_input("Metragem (m²)", key="metragem", placeholder="Ex: 360")
    
    with st.form("simulador_form"):
        col1, col2 = st.columns(2)
        with col1:
            valor_total_str = st.text_input("Valor Total do Imóvel (R$)", key="valor_total_str", placeholder="Ex: 150.000,50")
            entrada_str = st.text_input("Entrada (R$)", key="entrada_str", placeholder="Ex: 20.000,00")
            data_input = st.date_input("Data de Entrada", value=datetime.now(), format="DD/MM/YYYY", key="data_input")
            taxa_mensal = st.number_input("Taxa de Juros Mensal (%)", min_value=0.00, value=st.session_state.taxa_mensal, step=0.01, format="%.2f", key="taxa_mensal", help="Use vírgula para decimais (ex: 0,79).")
            modalidade = st.selectbox("Modalidade de Pagamento", ["mensal", "mensal + balão", "só balão anual", "só balão semestral"], key="modalidade")
            tipo_balao, agendamento_baloes, meses_baloes, mes_primeiro_balao = None, "Padrão", [], 12
            if modalidade == "mensal + balão": 
                tipo_balao = st.selectbox("Período Padrão do Balão:", ["anual", "semestral"], key="tipo_balao")
                agendamento_baloes = st.selectbox("Agendamento dos Balões", ["Padrão", "A partir do 1º Vencimento", "Personalizado (Mês a Mês)"], key="agendamento_baloes")
                
                # Pre-calcula o maximo de parcelas de forma segura
                max_parcelas_seguro = int(st.session_state.get("qtd_parcelas", 1))
                if max_parcelas_seguro <= 0: max_parcelas_seguro = 1 # Garante que o range não seja vazio
                
                if agendamento_baloes == "Personalizado (Mês a Mês)":
                    meses_baloes = st.multiselect("Selecione os meses dos balões:", options=list(range(1, max_parcelas_seguro + 1)), key="meses_baloes")
                elif agendamento_baloes == "A partir do 1º Vencimento":
                    # AJUSTE: O valor padrão e máximo agora são seguros
                    valor_padrao_mes = min(12, max_parcelas_seguro)
                    mes_primeiro_balao = st.number_input("Mês de Vencimento do 1º Balão", min_value=1, max_value=max_parcelas_seguro, value=valor_padrao_mes, step=1, key="mes_primeiro_balao")
            
            elif "anual" in modalidade: tipo_balao = "anual"
            elif "semestral" in modalidade: tipo_balao = "semestral"

        with col2:
            # AJUSTE: Limite de parcelas removido
            qtd_parcelas = st.number_input("Quantidade de Parcelas", min_value=0, step=1, key="qtd_parcelas", placeholder="Ex: 180")
            qtd_baloes = 0
            if "balão" in modalidade:
                if agendamento_baloes == "Personalizado (Mês a Mês)": qtd_baloes = len(meses_baloes)
                else: qtd_baloes = atualizar_baloes(modalidade, qtd_parcelas, tipo_balao)
                st.write(f"Quantidade de Balões: **{qtd_baloes}**")
            valor_parcela_str = st.text_input("Valor da Parcela (R$)", key="valor_parcela_str", placeholder="Deixe em branco para cálculo")
            valor_balao_str = ""
            if "balão" in modalidade:
                valor_balao_str = st.text_input("Valor do Balão (R$)", key="valor_balao_str", placeholder="Deixe em branco para cálculo")
        
        # AJUSTE: Botões movidos para dentro do formulário
        col_b1, col_b2, _ = st.columns([1, 1, 4])
        with col_b1:
            submitted = st.form_submit_button("Calcular")
        with col_b2:
            st.form_submit_button("Reiniciar", on_click=reset_form)
    
    if submitted:
        try:
            # Parse dos valores monetários
            valor_total = parse_currency(valor_total_str)
            entrada = parse_currency(entrada_str)
            valor_parcela = parse_currency(valor_parcela_str)
            valor_balao = parse_currency(valor_balao_str)
            
            taxa_mensal_para_calculo = st.session_state.taxa_mensal if not (1 <= qtd_parcelas <= 36 and modalidade == 'mensal') else 0.0
            if valor_total <= 0 or entrada < 0 or valor_total <= entrada: st.error("Verifique os valores de 'Total do Imóvel' e 'Entrada'."); return
            
            valor_financiado = round(max(valor_total - entrada, 0), 2)
            taxas = calcular_taxas(taxa_mensal_para_calculo); modo = determinar_modo_calculo(modalidade)
            v_p_final, v_b_final = 0.0, 0.0; v_ultima_p, v_ultimo_b = None, None
            data_entrada = datetime.combine(data_input, datetime.min.time()); dia_vencimento = data_entrada.day
            
            if taxa_mensal_para_calculo == 0.0:
                if modo == 1 and qtd_parcelas > 0:
                    vp = round(valor_financiado / qtd_parcelas, 2); dif = round((vp * qtd_parcelas) - valor_financiado, 2)
                    v_p_final = vp; v_ultima_p = vp - dif
                elif modo in [3, 4] and qtd_baloes > 0:
                    vb = round(valor_financiado / qtd_baloes, 2); dif = round((vb * qtd_baloes) - valor_financiado, 2)
                    v_b_final = vb; v_ultimo_b = vb - dif
                elif modo == 2 and qtd_parcelas > 0 and qtd_baloes > 0:
                    if valor_parcela > 0 and valor_balao == 0:
                        v_p_final = valor_parcela; vp_restante = valor_financiado - (valor_parcela * qtd_parcelas)
                        vb = round(vp_restante / qtd_baloes, 2); dif = round((vb * qtd_baloes) - vp_restante, 2)
                        v_b_final = vb; v_ultimo_b = vb - dif
                    elif valor_balao > 0 and valor_parcela == 0:
                        v_b_final = valor_balao; vp_restante = valor_financiado - (valor_balao * qtd_baloes)
                        vp = round(vp_restante / qtd_parcelas, 2); dif = round((vp * qtd_parcelas) - vp_restante, 2)
                        v_p_final = vp; v_ultima_p = vp - dif
                    else: st.error("No modo 'mensal + balão', informe OU o valor da parcela OU o valor do balão."); return
            else: # Lógica para planos com juros
                if modo == 1 and qtd_parcelas > 0:
                    datas = [ajustar_data_vencimento(data_entrada, "mensal", i, dia_vencimento) for i in range(1, qtd_parcelas + 1)]
                    fator_vp = calcular_fator_vp(datas, data_entrada, taxas['diaria']); v_p_final = round(valor_financiado / fator_vp, 2) if fator_vp > 0 else 0
                elif modo in [3, 4] and qtd_baloes > 0:
                    periodo = "anual" if modo == 3 else "semestral"
                    datas = [ajustar_data_vencimento(data_entrada, periodo, i, dia_vencimento) for i in range(1, qtd_baloes + 1)]
                    fator_vp = calcular_fator_vp(datas, data_entrada, taxas['diaria']); v_b_final = round(valor_financiado / fator_vp, 2) if fator_vp > 0 else 0
                elif modo == 2 and qtd_parcelas > 0 and qtd_baloes > 0:
                    datas_p = [ajustar_data_vencimento(data_entrada, "mensal", i, dia_vencimento) for i in range(1, qtd_parcelas + 1)]
                    if agendamento_baloes == "Personalizado (Mês a Mês)":
                        datas_b = [ajustar_data_vencimento(data_entrada, "mensal", mes, dia_vencimento) for mes in meses_baloes]
                    elif agendamento_baloes == "A partir do 1º Vencimento":
                        data_base_b = ajustar_data_vencimento(data_entrada, "mensal", mes_primeiro_balao, dia_vencimento)
                        datas_b = [ajustar_data_vencimento(data_base_b, tipo_balao, i) for i in range(qtd_baloes)]
                    else: # Padrão
                        intervalo_b = 12 if tipo_balao == 'anual' else 6
                        datas_b = [ajustar_data_vencimento(data_entrada, "mensal", i * intervalo_b, dia_vencimento) for i in range(1, qtd_baloes + 1)]
                    fator_vp_p = calcular_fator_vp(datas_p, data_entrada, taxas['diaria']); fator_vp_b = calcular_fator_vp(datas_b, data_entrada, taxas['diaria'])
                    if valor_parcela > 0 and valor_balao == 0:
                        v_p_final = valor_parcela; vp_restante = max(valor_financiado - (v_p_final * fator_vp_p), 0)
                        v_b_final = round(vp_restante / fator_vp_b, 2) if fator_vp_b > 0 else 0
                    elif valor_balao > 0 and valor_parcela == 0:
                        v_b_final = valor_balao; vp_restante = max(valor_financiado - (v_b_final * fator_vp_b), 0)
                        v_p_final = round(vp_restante / fator_vp_p, 2) if fator_vp_p > 0 else 0
                    else: st.error("No modo 'mensal + balão', informe OU o valor da parcela OU o valor do balão."); return
            
            cronograma = gerar_cronograma(valor_financiado, v_p_final, v_b_final, qtd_parcelas, qtd_baloes, modalidade, tipo_balao, data_entrada, taxas, valor_ultima_parcela=v_ultima_p, valor_ultimo_balao=v_ultimo_b, agendamento_baloes=agendamento_baloes, meses_baloes=meses_baloes, mes_primeiro_balao=mes_primeiro_balao)
            
            st.subheader("Resultados da Simulação")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Valor Financiado", formatar_moeda(valor_financiado)); c2.metric("Taxa Mensal Utilizada", f"{taxa_mensal_para_calculo:.2f}%")
            if v_p_final > 0: c3.metric("Valor da Parcela", formatar_moeda(v_p_final))
            if v_b_final > 0: c4.metric("Valor do Balão", formatar_moeda(v_b_final))

            st.subheader("Cronograma de Pagamentos")
            if cronograma:
                df_cronograma = pd.DataFrame([p for p in cronograma if p['Item'] != 'TOTAL'])
                df_display = df_cronograma.copy()
                for col in ['Valor', 'Valor_Presente', 'Desconto_Aplicado']: df_display[col] = df_display[col].apply(lambda x: formatar_moeda(x, simbolo=True))
                st.dataframe(df_display, use_container_width=True, hide_index=True, column_config={"Data_Vencimento": "Data Venc."})
                total = next(p for p in cronograma if p['Item'] == 'TOTAL')
                c1, c2, c3 = st.columns(3)
                c1.metric("Valor Total a Pagar", formatar_moeda(total['Valor'])); c2.metric("Valor Presente Total", formatar_moeda(total['Valor_Presente'])); c3.metric("Total de Descontos", formatar_moeda(total['Desconto_Aplicado']))
                st.subheader("Exportar Resultados")
                export_data = {'valor_total': valor_total, 'entrada': entrada, 'taxa_mensal': taxa_mensal_para_calculo, 'valor_financiado': valor_financiado, 'quadra': quadra, 'lote': lote, 'metragem': metragem}
                c1, c2 = st.columns(2)
                pdf_file = gerar_pdf(cronograma, export_data); c1.download_button("Exportar para PDF", pdf_file, "simulacao.pdf", "application/pdf")
                excel_file = gerar_excel(cronograma, export_data); c2.download_button("Exportar para Excel", excel_file, "simulacao.xlsx")
        except Exception as e:
            st.error(f"Ocorreu um erro durante a simulação: {str(e)}. Por favor, verifique os valores inseridos e tente novamente.")

if __name__ == '__main__':
    main()
