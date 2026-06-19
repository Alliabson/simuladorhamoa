import streamlit as st
from datetime import datetime, timedelta
from PIL import Image
import locale
from math import ceil
from io import BytesIO
import subprocess
import sys
import re

# --- Configuração de Locale ---
def configure_locale():
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

configure_locale()

# --- Instalação e Importação de Dependências ---
def install_and_import(package, import_name=None):
    import_name = import_name or package
    try:
        return __import__(import_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return __import__(import_name)

pd = install_and_import('pandas')
np = install_and_import('numpy')
FPDF = install_and_import('fpdf2', 'fpdf').FPDF
install_and_import('openpyxl')

# --- Carregamento de Dados (Excel) ---
@st.cache_data(ttl=3600)
def carregar_dados_lotes():
    try:
        # Lê a planilha. Certifique-se de que o nome do arquivo seja exatamente este.
        df = pd.read_excel("Lotes.xlsx")
        
        # Cria colunas separadas para Quadra e Lote baseadas no IDENTIFICADOR (Ex: QD.01 LT.01)
        df['Quadra'] = df['IDENTIFICADOR'].apply(lambda x: str(x).split(' ')[0].replace('QD.', '').strip() if pd.notnull(x) else '')
        df['Lote'] = df['IDENTIFICADOR'].apply(lambda x: str(x).split(' ')[1].replace('LT.', '').strip() if pd.notnull(x) and len(str(x).split(' ')) > 1 else '')
        return df
    except Exception as e:
        st.warning(f"Aviso: Não foi possível carregar a planilha Lotes.xlsx. Certifique-se de que o arquivo está na mesma pasta. Erro: {e}")
        return pd.DataFrame()

# --- Carregamento da Logo (Cacheado) ---
@st.cache_data(ttl=86400)
def load_logo():
    try:
        logo = Image.open("JMD HAMOA HORIZONTAL - BRANCO.png")
        logo.thumbnail((300, 300))
        return logo
    except Exception:
        return None

# --- Configuração da Página Streamlit e Tema ---
st.set_page_config(layout="wide")

def set_theme():
    st.markdown("""
    <style>
        /* CSS Omitido para economizar espaço, mantendo exatamente as suas configurações originais */
        .stApp { background-color: #1E1E1E; }
        [data-testid="stSidebar"] { background-color: #252526; }
        h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #FFFFFF; }
        .stMarkdown p, .stMarkdown li, .stText, .stNumberInput label, .stSelectbox label { color: #E0E0E0; }
        .stTextInput input, .stNumberInput input, .stSelectbox select { background-color: #333333; color: #FFFFFF; border-color: #555555; }
        .stButton button { background-color: #0056b3; color: white; border: none; border-radius: 4px; }
        .stButton button:hover { background-color: #003d82; }
        .stMetric { background-color: #252526; border-radius: 8px; padding: 15px; border-left: 4px solid #4D6BFE; }
        .stMetric label { color: #A0A0A0 !important; }
        .stMetric div { color: #FFFFFF !important; font-size: 24px !important; }
        .dataframe { background-color: #252526 !important; color: #E0E0E0 !important; }
        .dataframe th { background-color: #4D6BFE !important; color: white !important; }
        .dataframe tr:nth-child(even) { background-color: #333333 !important; }
        .dataframe tr:hover { background-color: #444444 !important; }
        .main .block-container { padding: 2rem 1rem !important; }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"], div[data-testid="stForm"] button[kind="secondary"], .stDownloadButton button { background-color: #4D6BFE !important; color: white !important; border: none !important; border-radius: 12px !important; padding: 10px 24px !important; font-weight: 600 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important; }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover, div[data-testid="stForm"] button[kind="secondary"]:hover, .stDownloadButton button:hover { background-color: #FF4D4D !important; transform: translateY(-2px) !important; box-shadow: 0 4px 8px rgba(255, 77, 77, 0.2) !important; }
    </style>
    """, unsafe_allow_html=True)

# --- Funções de Cálculo Financeiro (Mantidas Iguais) ---
def parse_currency(value_str: str) -> float:
    if not isinstance(value_str, str) or not value_str.strip(): return 0.0
    try:
        return float(re.sub(r'[R$\s\.]', '', value_str.strip()).replace(',', '.'))
    except (ValueError, TypeError): return 0.0

def parse_percentage(percent_str: str) -> float:
    if not isinstance(percent_str, str) or not percent_str.strip(): return 0.0
    try:
        return float(re.sub(r'[%\s]', '', percent_str.strip()).replace(',', '.'))
    except (ValueError, TypeError): return 0.0

def formatar_moeda(valor, simbolo=True):
    try:
        if isinstance(valor, str) and 'R$' in valor: valor = valor.replace('R$', '').strip()
        if valor is None or valor == '': return "R$ 0,00" if simbolo else "0,00"
        if isinstance(valor, str): valor = float(re.sub(r'\.', '', valor).replace(',', '.'))
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
        taxa_diaria = ((1 + taxa_mensal_decimal) ** (1/30)) - 1
        return {'anual': ((1 + taxa_mensal_decimal) ** 12) - 1, 'semestral': ((1 + taxa_mensal_decimal) ** 6) - 1, 'mensal': taxa_mensal_decimal, 'diaria': taxa_diaria}
    except Exception: return {'anual': 0, 'semestral': 0, 'mensal': 0, 'diaria': 0}

def calcular_valor_presente(valor_futuro, taxa_diaria, dias):
    try:
        if dias <= 0 or taxa_diaria <= 0: return float(valor_futuro)
        return round(float(valor_futuro) / ((1 + taxa_diaria) ** dias), 2)
    except Exception: return float(valor_futuro)

def calcular_fator_vp(datas_vencimento, data_inicio, taxa_diaria):
    if taxa_diaria <= 0: return float(len(datas_vencimento))
    fator_total = 0.0
    for data_venc in datas_vencimento:
        if not isinstance(data_venc, datetime): data_venc = datetime.strptime(data_venc, '%d/%m/%Y')
        dias_comerciais = ((data_venc.year - data_inicio.year) * 12 + (data_venc.month - data_inicio.month)) * 30
        if dias_comerciais > 0: fator_total += 1 / ((1 + taxa_diaria) ** dias_comerciais)
    return fator_total

def ajustar_data_vencimento(data_base, periodo, num_periodo=1, dia_vencimento=None):
    try:
        if not isinstance(data_base, datetime): data_base = datetime.combine(data_base, datetime.min.time())
        dia = dia_vencimento if dia_vencimento is not None else data_base.day
        months_to_add = num_periodo if periodo == "mensal" else (6 * num_periodo if periodo == "semestral" else (12 * num_periodo if periodo == "anual" else 0))
        if months_to_add == 0: return data_base
        total_meses = data_base.month + months_to_add
        novo_ano = data_base.year + (total_meses - 1) // 12
        novo_mes = (total_meses - 1) % 12 + 1
        try: return datetime(novo_ano, novo_mes, dia)
        except ValueError: return datetime(novo_ano, novo_mes, (datetime(novo_ano, novo_mes + 1, 1) - timedelta(days=1)).day if novo_mes < 12 else 31)
    except Exception: return data_base + timedelta(days=30 * (months_to_add or num_periodo))

def determinar_modo_calculo(modalidade):
    return {"mensal": 1, "mensal + balão": 2, "só balão anual": 3, "só balão semestral": 4}.get(modalidade, 1)

def atualizar_baloes(modalidade, qtd_parcelas, tipo_balao=None):
    try:
        if modalidade == "mensal + balão": return int(qtd_parcelas) // (12 if tipo_balao == "anual" else 6)
        return 0
    except Exception: return 0

@st.cache_data(ttl=3600)
def gerar_cronograma(valor_financiado, valor_parcela_final, valor_balao_final, qtd_parcelas, qtd_baloes, modalidade, tipo_balao, data_entrada, taxas, valor_ultima_parcela=None, valor_ultimo_balao=None, agendamento_baloes=None, meses_baloes=None, mes_primeiro_balao=None, baloes_especiais=None):
    try:
        dia_vencimento_real = data_entrada.day
        parcelas, baloes = [], []
        baloes_especiais = baloes_especiais or {}

        if modalidade in ["mensal", "mensal + balão"]:
            for i in range(1, qtd_parcelas + 1):
                valor_corrente = valor_ultima_parcela if (i == qtd_parcelas and valor_ultima_parcela is not None) else valor_parcela_final
                data_vencimento = ajustar_data_vencimento(data_entrada, "mensal", i, dia_vencimento_real)
                dias_comerciais = i * 30
                vp = calcular_valor_presente(valor_corrente, taxas['diaria'], dias_comerciais)
                parcelas.append({"Item": f"Parcela {i}", "Tipo": "Parcela", "Data_Vencimento": data_vencimento.strftime('%d/%m/%Y'), "Dias": dias_comerciais, "Valor": round(valor_corrente, 2), "Valor_Presente": round(vp, 2), "Desconto_Aplicado": round(valor_corrente - vp, 2)})

        datas_baloes_a_gerar = []
        if "balão" in modalidade and qtd_baloes > 0:
            if agendamento_baloes == "Personalizado (Mês a Mês)":
                datas_baloes_a_gerar = [ajustar_data_vencimento(data_entrada, "mensal", mes, dia_vencimento_real) for mes in meses_baloes]
            elif agendamento_baloes == "A partir do 1º Vencimento":
                primeira_data_balao = ajustar_data_vencimento(data_entrada, "mensal", mes_primeiro_balao, dia_vencimento_real)
                datas_baloes_a_gerar.append(primeira_data_balao)
                data_anterior = primeira_data_balao
                for _ in range(1, qtd_baloes):
                    proxima_data_balao = ajustar_data_vencimento(data_anterior, tipo_balao, 1, dia_vencimento_real)
                    datas_baloes_a_gerar.append(proxima_data_balao)
                    data_anterior = proxima_data_balao
            else: 
                datas_baloes_a_gerar = [ajustar_data_vencimento(data_entrada, tipo_balao, i, dia_vencimento_real) for i in range(1, qtd_baloes + 1)]

        for i, data_vencimento in enumerate(datas_baloes_a_gerar):
            balao_count = i + 1
            valor_corrente = baloes_especiais.get(balao_count, valor_ultimo_balao if (balao_count == qtd_baloes and valor_ultimo_balao is not None) else valor_balao_final)
            dias_comerciais = ((data_vencimento.year - data_entrada.year) * 12 + (data_vencimento.month - data_entrada.month)) * 30
            vp = calcular_valor_presente(valor_corrente, taxas['diaria'], dias_comerciais)
            baloes.append({"Item": f"Balão {balao_count}", "Tipo": "Balão", "Data_Vencimento": data_vencimento.strftime('%d/%m/%Y'), "Dias": dias_comerciais, "Valor": round(valor_corrente, 2), "Valor_Presente": round(vp, 2), "Desconto_Aplicado": round(valor_corrente - vp, 2)})

        cronograma = sorted(parcelas, key=lambda x: datetime.strptime(x['Data_Vencimento'], '%d/%m/%Y')) + sorted(baloes, key=lambda x: datetime.strptime(x['Data_Vencimento'], '%d/%m/%Y'))

        if cronograma:
            total_valor = round(sum(p['Valor'] for p in cronograma), 2)
            valor_presente_real = round(sum(p['Valor_Presente'] for p in cronograma), 2)
            cronograma.append({"Item": "TOTAL", "Tipo": "", "Data_Vencimento": "", "Dias": "", "Valor": total_valor, "Valor_Presente": valor_presente_real, "Desconto_Aplicado": round(total_valor - valor_presente_real, 2)})
        return cronograma
    except Exception as e:
        st.error(f"Erro inesperado ao gerar cronograma: {str(e)}.")
        return []

# --- Funções de Exportação (Mantidas Iguais) ---
def gerar_pdf(cronograma, dados):
    try:
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Informações do Imóvel", ln=1, align='L'); pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Quadra: {dados.get('quadra', 'N/I')}", ln=1); pdf.cell(200, 10, txt=f"Lote: {dados.get('lote', 'N/I')}", ln=1); pdf.cell(200, 10, txt=f"Metragem: {dados.get('metragem', 'N/I')} m²", ln=1)
        pdf.ln(5); pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Simulação de Financiamento", ln=1, align='L'); pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Valor Total do Imóvel: {formatar_moeda(dados['valor_total'])}", ln=1); pdf.cell(200, 10, txt=f"Entrada: {formatar_moeda(dados['entrada'])}", ln=1); pdf.cell(200, 10, txt=f"Valor Financiado: {formatar_moeda(dados['valor_financiado'])}", ln=1); pdf.cell(200, 10, txt=f"Taxa Mensal Utilizada: {dados['taxa_mensal']:.2f}%", ln=1)
        pdf.ln(10); pdf.set_font("Arial", 'B', 12)
        colunas, larguras = ["Item", "Tipo", "Data Venc.", "Valor", "Valor Presente", "Juros"], [30, 25, 30, 35, 35, 35]
        for col, larg in zip(colunas, larguras): pdf.cell(larg, 10, txt=col, border=1, align='C')
        pdf.ln(); pdf.set_font("Arial", size=10)
        for item in [p for p in cronograma if p['Item'] != 'TOTAL']:
            pdf.cell(larguras[0], 8, txt=item['Item'], border=1); pdf.cell(larguras[1], 8, txt=item['Tipo'], border=1); pdf.cell(larguras[2], 8, txt=item['Data_Vencimento'], border=1)
            pdf.cell(larguras[3], 8, txt=formatar_moeda(item['Valor'], simbolo=False), border=1, align='R'); pdf.cell(larguras[4], 8, txt=formatar_moeda(item['Valor_Presente'], simbolo=False), border=1, align='R'); pdf.cell(larguras[5], 8, txt=formatar_moeda(item['Desconto_Aplicado'], simbolo=False), border=1, align='R'); pdf.ln()
        total = next((p for p in cronograma if p['Item'] == 'TOTAL'), None)
        if total:
            pdf.set_font("Arial", 'B', 10); pdf.cell(sum(larguras[:3]), 10, txt="TOTAL", border=1, align='R')
            pdf.cell(larguras[3], 10, txt=formatar_moeda(total['Valor'], simbolo=False), border=1, align='R'); pdf.cell(larguras[4], 10, txt=formatar_moeda(total['Valor_Presente'], simbolo=False), border=1, align='R'); pdf.cell(larguras[5], 10, txt=formatar_moeda(total['Desconto_Aplicado'], simbolo=False), border=1, align='R')
        return BytesIO(pdf.output())
    except Exception: return BytesIO()

def gerar_excel(cronograma, dados):
    try:
        output = BytesIO()
        info_df = pd.DataFrame({'Campo': ['Quadra', 'Lote', 'Metragem', 'Valor Total do Imóvel', 'Entrada', 'Valor Financiado', 'Taxa Mensal Utilizada'], 'Valor': [dados.get('quadra', 'N/I'), dados.get('lote', 'N/I'), f"{dados.get('metragem', 'N/I')} m²", formatar_moeda(dados.get('valor_total', 0)), formatar_moeda(dados.get('entrada', 0)), formatar_moeda(dados.get('valor_financiado', 0)), f"{dados.get('taxa_mensal', 0):.2f}%"]})
        df_cronograma_data = pd.DataFrame([p for p in cronograma if p['Item'] != 'TOTAL']).rename(columns={'Desconto_Aplicado': 'Juros'})
        total_row = next((p for p in cronograma if p['Item'] == 'TOTAL'), None)
        if total_row: total_row['Juros'] = total_row.get('Desconto_Aplicado')
        df_final = pd.concat([df_cronograma_data, pd.DataFrame([total_row])], ignore_index=True) if total_row else df_cronograma_data
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            info_df.to_excel(writer, sheet_name='Informações da Simulação', index=False)
            df_final[['Item', 'Tipo', 'Data_Vencimento', 'Valor', 'Valor_Presente', 'Juros']].to_excel(writer, sheet_name='Cronograma de Pagamentos', index=False)
        output.seek(0); return output
    except Exception: return BytesIO()

# --- Lista de Planos Pré-definidos ---
PLANOS_DISPONIVEIS = [
    "Personalizado (Digitar Manualmente)",
    "Plano de 24 Parcelas, 10% de entrada, parcelado em 03 vezes",
    "Plano de 36 Parcelas, 10% de entrada, parcelado em 03 vezes",
    "Plano de 48 Parcelas, 10% de entrada, parcelado em 03 vezes",
    "Plano de 60 Parcelas, 10% de entrada, parcelado em 03 vezes",
    "Plano de 72 Parcelas, 06% de entrada, parcelado em 03 vezes",
    "Plano de 84 Parcelas, 06% de entrada, parcelado em 03 vezes",
    "Plano de 96 Parcelas, 06% de entrada, parcelado em 03 vezes",
    "Plano de 108 Parcelas, 06% de entrada, parcelado em 03 vezes",
    "Plano de 120 Parcelas, 06% de entrada, parcelado em 03 vezes",
    "Plano de 132 Parcelas, 06% de entrada, parcelado em 03 vezes",
    "Plano de 144 Parcelas, 06% de entrada, parcelado em 03 vezes",
    "Plano de 156 Parcelas, 06% de entrada, parcelado em 03 vezes",
    "Plano de 72 Parcelas + 06 balões, 06% de entrada, parcelado em 03 vezes",
    "Plano de 84 Parcelas + 07 balões, 06% de entrada, parcelado em 03 vezes",
    "Plano de 96 Parcelas + 08 Balões, 06% de entrada, parcelado em 03 vezes",
    "Plano de 108 Parcelas + 09 Balões, 06% de entrada, parcelado em 03 vezes",
    "Plano de 120 Parcelas + 10 Balões, 06% de entrada, parcelado em 03 vezes",
    "Plano de 132 Parcelas + 11 Balões, 06% de entrada, parcelado em 03 vezes",
    "Plano de 144 Parcelas + 12 Balões, 06% de entrada, parcelado em 03 vezes",
    "Plano de 156 Parcelas + 13 Balões, 06% de entrada, parcelado em 03 vezes"
]

# --- Função Principal ---
def main():
    set_theme()
    st.write("\n")
    logo = load_logo()
    if logo:
        col1, col2 = st.columns([1, 4]); col1.image(logo, width=200, use_container_width=False)
        col2.title("**Seja bem vindo ao Simulador da JMD HAMOA**")
    else: st.title("Simulador Imobiliária Celeste")
        
    if 'taxa_mensal' not in st.session_state: st.session_state.taxa_mensal = "0,89"
    
    def reset_form(): 
        taxa_atual = st.session_state.taxa_mensal
        st.session_state.clear()
        st.session_state.taxa_mensal = taxa_atual

    # 1. Carrega os lotes
    df_lotes = carregar_dados_lotes()
    
    with st.container():
        st.subheader("Seleção do Imóvel")
        cols = st.columns(3)
        
        # Filtros encadeados de Quadra e Lote
        quadra_selecionada = ""
        lote_selecionado = ""
        
        if not df_lotes.empty:
            quadras_disponiveis = sorted(df_lotes['Quadra'].dropna().unique())
            quadra_selecionada = cols[0].selectbox("Quadra", options=[""] + list(quadras_disponiveis))
            
            if quadra_selecionada:
                lotes_disponiveis = df_lotes[df_lotes['Quadra'] == quadra_selecionada]['Lote'].dropna().unique()
                lote_selecionado = cols[1].selectbox("Lote", options=[""] + list(lotes_disponiveis))
            else:
                lote_selecionado = cols[1].selectbox("Lote", options=[""])
                
            # Recupera os valores automaticamente
            metragem_bd = ""
            valor_vista_bd = ""
            if quadra_selecionada and lote_selecionado:
                linha = df_lotes[(df_lotes['Quadra'] == quadra_selecionada) & (df_lotes['Lote'] == lote_selecionado)].iloc[0]
                metragem_bd = f"{linha['Área em Metro Quadrado']:.2f}" if pd.notnull(linha['Área em Metro Quadrado']) else ""
                
                v_vista = linha['Valor a Vista']
                if pd.notnull(v_vista):
                    valor_vista_bd = f"{v_vista:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            quadra_selecionada = cols[0].text_input("Quadra", key="quadra", placeholder="Ex: 15")
            lote_selecionado = cols[1].text_input("Lote", key="lote", placeholder="Ex: 22")
            metragem_bd = ""
            valor_vista_bd = ""
            
        metragem = cols[2].text_input("Metragem (m²)", value=metragem_bd, placeholder="Ex: 360")
        
    with st.container():
        st.subheader("Plano de Pagamento")
        plano_selecionado = st.selectbox("Escolha um Plano Sugerido (Opcional)", PLANOS_DISPONIVEIS)
        
        # Lógica de Extração dos Planos
        qtd_parcelas_sug = 0
        qtd_baloes_sug = 0
        percentual_entrada_sug = 0.0
        modalidade_sug = "mensal"
        
        if plano_selecionado != "Personalizado (Digitar Manualmente)":
            # Extrai Parcelas
            match_p = re.search(r'(\d+) Parcelas', plano_selecionado)
            if match_p: qtd_parcelas_sug = int(match_p.group(1))
            
            # Extrai Balões
            match_b = re.search(r'(\d+) [Bb]al[õo]es', plano_selecionado)
            if match_b: 
                qtd_baloes_sug = int(match_b.group(1))
                modalidade_sug = "mensal + balão"
            
            # Extrai % Entrada
            if "10% de entrada" in plano_selecionado: percentual_entrada_sug = 0.10
            elif "06% de entrada" in plano_selecionado: percentual_entrada_sug = 0.06

    with st.form("simulador_form"):
        col1, col2 = st.columns(2)
        with col1:
            valor_total_str = st.text_input("Valor Total do Imóvel (R$)", value=valor_vista_bd, key="valor_total_str", placeholder="Ex: 150.000,50")
            
            # Calcula entrada sugerida automaticamente baseada no plano escolhido
            entrada_sug_str = ""
            if percentual_entrada_sug > 0 and valor_vista_bd:
                v_total_calc = parse_currency(valor_vista_bd)
                v_entrada_calc = v_total_calc * percentual_entrada_sug
                entrada_sug_str = f"{v_entrada_calc:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                
            entrada_str = st.text_input("Entrada (R$)", value=entrada_sug_str, key="entrada_str", placeholder="Ex: 20.000,00 (Edite se necessário)")
            
            data_input = st.date_input("Data de Entrada", value=datetime.now(), format="DD/MM/YYYY", key="data_input")
            taxa_mensal_str = st.text_input("Taxa de Juros Mensal (%)", value=st.session_state.taxa_mensal, key="taxa_mensal_str", placeholder="Ex: 0,89")
            
            modalidade_index = ["mensal", "mensal + balão", "só balão anual", "só balão semestral"].index(modalidade_sug)
            modalidade = st.selectbox("Modalidade de Pagamento", ["mensal", "mensal + balão", "só balão anual", "só balão semestral"], index=modalidade_index, key="modalidade")
            
            tipo_balao, agendamento_baloes, meses_baloes, mes_primeiro_balao = None, "Padrão", [], 12
            
            if "balão" in modalidade: 
                if modalidade == "mensal + balão":
                    tipo_balao = st.selectbox("Período Padrão do Balão:", ["anual", "semestral"], key="tipo_balao")
                elif "anual" in modalidade: tipo_balao = "anual"
                elif "semestral" in modalidade: tipo_balao = "semestral"

                agendamento_baloes = st.selectbox("Agendamento dos Balões", ["Padrão", "A partir do 1º Vencimento", "Personalizado (Mês a Mês)"], key="agendamento_baloes")
                max_meses_plano = 360 
                
                if agendamento_baloes == "Personalizado (Mês a Mês)":
                    meses_baloes = st.multiselect("Selecione os meses dos balões:", options=list(range(1, max_meses_plano + 1)), key="meses_baloes")
                elif agendamento_baloes == "A partir do 1º Vencimento":
                    mes_primeiro_balao = st.number_input("Mês de Vencimento do 1º Balão", min_value=1, max_value=max_meses_plano, value=(12 if tipo_balao == 'anual' else 6), step=1, key="mes_primeiro_balao")

        with col2:
            qtd_parcelas, qtd_baloes = 0, 0
            
            if not modalidade.startswith("só balão"):
                qtd_parcelas = st.number_input("Quantidade de Parcelas", min_value=0, value=qtd_parcelas_sug, step=1, key="qtd_parcelas", placeholder="Ex: 180")

            if "balão" in modalidade:
                if agendamento_baloes == "Personalizado (Mês a Mês)":
                    qtd_baloes = len(meses_baloes)
                    st.write(f"Quantidade de Balões: **{qtd_baloes}** (definido pela seleção)")
                    if modalidade.startswith("só balão"): st.number_input("Quantidade de Balões", value=qtd_baloes, disabled=True, key="qtd_baloes_direto_disabled")
                elif modalidade.startswith("só balão"):
                    qtd_baloes = st.number_input("Quantidade de Balões", min_value=0, value=max(0, qtd_baloes_sug), step=1, key="qtd_baloes_direto", placeholder="Ex: 4")
                else: 
                    # Usa o valor sugerido do plano se houver, se não calcula.
                    qtd_baloes = qtd_baloes_sug if qtd_baloes_sug > 0 else atualizar_baloes(modalidade, qtd_parcelas, tipo_balao)
                    st.write(f"Quantidade de Balões: **{qtd_baloes}**")

            valor_parcela_str = st.text_input("Valor da Parcela (R$)", key="valor_parcela_str", placeholder="Deixe em branco para cálculo") if not modalidade.startswith("só balão") else ""
            
            valor_balao_str = ""
            baloes_especiais_input = {}
            if "balão" in modalidade:
                valor_balao_str = st.text_input("Valor Padrão do Balão (R$)", key="valor_balao_str", placeholder="Deixe em branco para cálculo")
                with st.expander("Adicionar Balões com Valores Diferentes (Opcional)"):
                    num_especiais = st.number_input("Quantos balões terão valor especial?", min_value=0, max_value=4, step=1, key="num_baloes_especiais")
                    for i in range(num_especiais):
                        cols_esp = st.columns(2)
                        idx = cols_esp[0].number_input(f"Vencimento do {i+1}º Balão Especial", min_value=1, step=1, key=f"idx_b_{i}")
                        val_str = cols_esp[1].text_input(f"Valor do {i+1}º Balão Especial (R$)", key=f"val_b_{i}")
                        if idx and val_str: baloes_especiais_input[idx] = parse_currency(val_str)
        
        col_b1, col_b2, _ = st.columns([1, 1, 4])
        with col_b1: submitted = st.form_submit_button("Calcular")
        with col_b2: st.form_submit_button("Reiniciar", on_click=reset_form)
    
    # --- Processamento do Formulário ---
    if submitted:
        try:
            valor_total = parse_currency(valor_total_str)
            entrada = parse_currency(entrada_str)
            valor_parcela = parse_currency(valor_parcela_str)
            valor_balao = parse_currency(valor_balao_str)
            taxa_mensal = parse_percentage(taxa_mensal_str)
            
            st.session_state.taxa_mensal = taxa_mensal_str
            taxa_mensal_para_calculo = taxa_mensal
            
            if valor_total <= 0 or entrada < 0 or valor_total <= entrada: 
                st.error("Verifique os valores de 'Total do Imóvel' e 'Entrada'.")
                return
            
            valor_financiado = round(max(valor_total - entrada, 0), 2)
            taxas = calcular_taxas(taxa_mensal_para_calculo)
            v_p_final, v_b_final = 0.0, 0.0
            data_entrada = datetime.combine(data_input, datetime.min.time())
            dia_vencimento = data_entrada.day
            
            if taxa_mensal_para_calculo == 0.0:
                vp_baloes_especiais = sum(baloes_especiais_input.values())
                vp_restante = valor_financiado - vp_baloes_especiais
                num_baloes_regulares = qtd_baloes - len(baloes_especiais_input)

                if valor_parcela > 0: 
                    v_p_final = valor_parcela
                    vp_restante -= v_p_final * qtd_parcelas
                    if num_baloes_regulares > 0 and vp_restante > 0: v_b_final = round(vp_restante / num_baloes_regulares, 2)
                elif valor_balao > 0: 
                    v_b_final = valor_balao
                    vp_restante -= v_b_final * num_baloes_regulares
                    if qtd_parcelas > 0 and vp_restante > 0: v_p_final = round(vp_restante / qtd_parcelas, 2)
                else:
                    total_items = qtd_parcelas + num_baloes_regulares
                    if total_items > 0:
                        valor_uniforme = round(vp_restante / total_items, 2)
                        if qtd_parcelas > 0: v_p_final = valor_uniforme
                        if num_baloes_regulares > 0: v_b_final = valor_uniforme
            else: 
                datas_p = [ajustar_data_vencimento(data_entrada, "mensal", i, dia_vencimento) for i in range(1, (qtd_parcelas or 0) + 1)]
                datas_b_todas = []
                if "balão" in modalidade and qtd_baloes > 0:
                    if agendamento_baloes == "Personalizado (Mês a Mês)": datas_b_todas = [ajustar_data_vencimento(data_entrada, "mensal", mes, dia_vencimento) for mes in meses_baloes]
                    elif agendamento_baloes == "A partir do 1º Vencimento":
                        dt = ajustar_data_vencimento(data_entrada, "mensal", mes_primeiro_balao, dia_vencimento)
                        datas_b_todas.append(dt)
                        for _ in range(1, qtd_baloes):
                            dt = ajustar_data_vencimento(dt, tipo_balao, 1, dia_vencimento)
                            datas_b_todas.append(dt)
                    else: datas_b_todas = [ajustar_data_vencimento(data_entrada, tipo_balao, i, dia_vencimento) for i in range(1, qtd_baloes + 1)]

                vp_baloes_especiais = 0.0
                datas_b_regulares = []
                for i, data_b in enumerate(datas_b_todas):
                    idx_balao = i + 1
                    if idx_balao in baloes_especiais_input:
                        dias_comerciais = ((data_b.year - data_entrada.year) * 12 + (data_b.month - data_entrada.month)) * 30
                        vp_baloes_especiais += calcular_valor_presente(baloes_especiais_input[idx_balao], taxas['diaria'], dias_comerciais)
                    else: datas_b_regulares.append(data_b)
                
                vp_restante = valor_financiado - vp_baloes_especiais
                if vp_restante < 0: st.error("O valor presente dos balões especiais excede o valor financiado."); return
                
                fator_vp_p = calcular_fator_vp(datas_p, data_entrada, taxas['diaria'])
                fator_vp_b_reg = calcular_fator_vp(datas_b_regulares, data_entrada, taxas['diaria'])
                
                if valor_parcela > 0 and valor_balao == 0:
                    v_p_final = valor_parcela
                    vp_para_baloes = vp_restante - (v_p_final * fator_vp_p)
                    if fator_vp_b_reg > 0 and vp_para_baloes > 0: v_b_final = round(vp_para_baloes / fator_vp_b_reg, 2)
                elif valor_balao > 0 and valor_parcela == 0: 
                    v_b_final = valor_balao
                    vp_para_parcelas = vp_restante - (v_b_final * fator_vp_b_reg)
                    if fator_vp_p > 0 and vp_para_parcelas > 0: v_p_final = round(vp_para_parcelas / fator_vp_p, 2)
                elif valor_parcela == 0 and valor_balao == 0: 
                    if fator_vp_p > 0 and fator_vp_b_reg == 0: v_p_final = round(vp_restante / fator_vp_p, 2)
                    elif fator_vp_b_reg > 0 and fator_vp_p == 0: v_b_final = round(vp_restante / fator_vp_b_reg, 2)
                    else: st.error("Para cálculo automático, informe o valor da Parcela OU do Balão Padrão."); return
                else: v_p_final, v_b_final = valor_parcela, valor_balao

            cronograma = gerar_cronograma(valor_financiado, v_p_final, v_b_final, (qtd_parcelas or 0), qtd_baloes, modalidade, tipo_balao, data_entrada, taxas, agendamento_baloes=agendamento_baloes, meses_baloes=meses_baloes, mes_primeiro_balao=mes_primeiro_balao, baloes_especiais=baloes_especiais_input)
            
            st.subheader("Resultados da Simulação")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Valor Financiado", formatar_moeda(valor_financiado)); c2.metric("Taxa Mensal Utilizada", f"{taxa_mensal_para_calculo:.2f}%")
            if v_p_final > 0: c3.metric("Valor da Parcela", formatar_moeda(v_p_final))
            if v_b_final > 0 or any(v > 0 for v in baloes_especiais_input.values()): c4.metric("Valor do Balão Padrão", formatar_moeda(v_b_final))

            st.subheader("Cronograma de Pagamentos")
            if cronograma:
                df_cronograma = pd.DataFrame([p for p in cronograma if p['Item'] != 'TOTAL'])
                df_display = df_cronograma.copy()
                for col in ['Valor', 'Valor_Presente', 'Desconto_Aplicado']: df_display[col] = df_display[col].apply(lambda x: formatar_moeda(x, simbolo=True))
                df_display.rename(columns={'Desconto_Aplicado': 'Juros'}, inplace=True)
                st.dataframe(df_display, use_container_width=True, hide_index=True, column_config={"Data_Vencimento": "Data Venc."})
                total = next((p for p in cronograma if p['Item'] == 'TOTAL'), None)
                if total:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Valor Total a Pagar", formatar_moeda(total['Valor'])); c2.metric("Valor Presente Total", formatar_moeda(total['Valor_Presente'])); c3.metric("Total de Juros", formatar_moeda(total['Desconto_Aplicado']))
                    
                    if abs(total['Valor_Presente'] - valor_financiado) > 1.0:
                        st.warning(f"Atenção: A soma dos valores presentes ({formatar_moeda(total['Valor_Presente'])}) não corresponde exatamente ao valor financiado ({formatar_moeda(valor_financiado)}).")

                    st.subheader("Exportar Resultados")
                    export_data = {'valor_total': valor_total, 'entrada': entrada, 'taxa_mensal': taxa_mensal_para_calculo, 'valor_financiado': valor_financiado, 'quadra': quadra_selecionada, 'lote': lote_selecionado, 'metragem': metragem}
                    c1_exp, c2_exp = st.columns(2)
                    pdf_file = gerar_pdf(cronograma, export_data); c1_exp.download_button("Exportar para PDF", pdf_file, "simulacao.pdf", "application/pdf")
                    excel_file = gerar_excel(cronograma, export_data); c2_exp.download_button("Exportar para Excel", excel_file, "simulacao.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error(f"Ocorreu um erro durante a simulação: {str(e)}. Por favor, verifique os valores inseridos e tente novamente.")

if __name__ == '__main__':
    main()
