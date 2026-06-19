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
    try: locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except locale.Error:
        try: locale.setlocale(locale.LC_ALL, 'pt_BR')
        except locale.Error:
            try: locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
            except locale.Error:
                try: locale.setlocale(locale.LC_ALL, '')
                except locale.Error: locale.setlocale(locale.LC_ALL, 'C.UTF-8')

configure_locale()

# --- Instalação e Importação de Dependências ---
def install_and_import(package, import_name=None):
    import_name = import_name or package
    try: return __import__(import_name)
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
        df = pd.read_excel("Lotes.xlsx")
        df['Quadra'] = df['IDENTIFICADOR'].apply(lambda x: str(x).split(' ')[0].replace('QD.', '').strip() if pd.notnull(x) else '')
        df['Lote'] = df['IDENTIFICADOR'].apply(lambda x: str(x).split(' ')[1].replace('LT.', '').strip() if pd.notnull(x) and len(str(x).split(' ')) > 1 else '')
        return df
    except Exception as e:
        return pd.DataFrame()

# --- Funções de Cálculo Auxiliares ---
def parse_currency(value_str: str) -> float:
    if not isinstance(value_str, str) or not value_str.strip(): return 0.0
    try: return float(re.sub(r'[R$\s\.]', '', value_str.strip()).replace(',', '.'))
    except (ValueError, TypeError): return 0.0

def parse_percentage(percent_str: str) -> float:
    if not isinstance(percent_str, str) or not percent_str.strip(): return 0.0
    try: return float(re.sub(r'[%\s]', '', str(percent_str).strip()).replace(',', '.'))
    except (ValueError, TypeError): return 0.0

def formatar_moeda(valor, simbolo=True):
    try:
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
        return {'mensal': taxa_mensal_decimal, 'diaria': taxa_diaria}
    except Exception: return {'mensal': 0, 'diaria': 0}

def ajustar_data_vencimento(data_base, periodo, num_periodo=1, dia_vencimento=None):
    if not isinstance(data_base, datetime): data_base = datetime.combine(data_base, datetime.min.time())
    dia = dia_vencimento if dia_vencimento is not None else data_base.day
    months_to_add = num_periodo if periodo == "mensal" else (12 * num_periodo if periodo == "anual" else 0)
    if months_to_add == 0: return data_base
    total_meses = data_base.month + months_to_add
    novo_ano = data_base.year + (total_meses - 1) // 12
    novo_mes = (total_meses - 1) % 12 + 1
    try: return datetime(novo_ano, novo_mes, dia)
    except ValueError: return datetime(novo_ano, novo_mes, (datetime(novo_ano, novo_mes + 1, 1) - timedelta(days=1)).day if novo_mes < 12 else 31)

def calcular_fator_vp(datas_vencimento, data_inicio, taxa_diaria):
    if taxa_diaria <= 0: return float(len(datas_vencimento))
    fator_total = 0.0
    for data_venc in datas_vencimento:
        dias_comerciais = ((data_venc.year - data_inicio.year) * 12 + (data_venc.month - data_inicio.month)) * 30
        if dias_comerciais > 0: fator_total += 1 / ((1 + taxa_diaria) ** dias_comerciais)
    return fator_total

# --- LISTA MESTRA DE PLANOS ---
PLANOS_DISPONIVEIS = [
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

def gerar_tabela_todos_planos(valor_total, taxa_mensal_percentual, data_base):
    taxas = calcular_taxas(taxa_mensal_percentual)
    taxa_diaria = taxas['diaria']
    resultados = []

    for plano in PLANOS_DISPONIVEIS:
        # Extrai os dados numéricos do texto do plano
        match_p = re.search(r'(\d+)\s*[Pp]arcelas', plano)
        qtd_parcelas = int(match_p.group(1)) if match_p else 0
        
        match_b = re.search(r'(\d+)\s*[Bb]al[õo]es', plano, re.IGNORECASE)
        qtd_baloes = int(match_b.group(1)) if match_b else 0
        
        match_e = re.search(r'(\d+)%\s*de\s*entrada', plano)
        pct_entrada = float(match_e.group(1))/100 if match_e else 0.10

        # Cálculos de Entrada e Financiamento
        entrada_total = valor_total * pct_entrada
        entrada_3x = entrada_total / 3
        valor_financiado = valor_total - entrada_total

        # Cálculo do Fator de Valor Presente
        datas_p = [ajustar_data_vencimento(data_base, "mensal", i, data_base.day) for i in range(1, qtd_parcelas + 1)]
        datas_b = [ajustar_data_vencimento(data_base, "anual", i, data_base.day) for i in range(1, qtd_baloes + 1)]

        fator_vp_p = calcular_fator_vp(datas_p, data_base, taxa_diaria)
        fator_vp_b = calcular_fator_vp(datas_b, data_base, taxa_diaria)

        fator_total = fator_vp_p + fator_vp_b
        valor_uniforme = valor_financiado / fator_total if fator_total > 0 else 0

        nome_exibicao = f"{qtd_parcelas}x"
        if qtd_baloes > 0: nome_exibicao += f" + {qtd_baloes} Balões"

        resultados.append({
            "Plano": nome_exibicao,
            "Entrada (%)": f"{int(pct_entrada*100)}%",
            "Entrada Total": formatar_moeda(entrada_total),
            "Sinal (Entrada em 3x)": formatar_moeda(entrada_3x),
            "Valor da Parcela": formatar_moeda(valor_uniforme),
            "Valor do Balão (Anual)": formatar_moeda(valor_uniforme) if qtd_baloes > 0 else "-",
            "Valor Financiado": formatar_moeda(valor_financiado)
        })

    return pd.DataFrame(resultados)


# --- Configuração da Página Streamlit e Tema ---
st.set_page_config(layout="wide", page_title="Simulador de Lotes")

def set_theme():
    st.markdown("""
    <style>
        .stApp { background-color: #1E1E1E; }
        h1, h2, h3, h4, .stMarkdown p, .stTextInput label, .stSelectbox label, .stNumberInput label { color: #FFFFFF !important; }
        .stTextInput input, .stNumberInput input, .stSelectbox select { background-color: #333333; color: #FFFFFF; }
        .dataframe { font-size: 14px !important; }
        .dataframe th { background-color: #4D6BFE !important; color: white !important; font-weight: bold; text-align: center !important;}
        .dataframe td { text-align: center !important; }
    </style>
    """, unsafe_allow_html=True)

# --- Função Principal ---
def main():
    set_theme()
    st.title("🏡 Simulador de Planos - JMD HAMOA")
    st.markdown("Selecione a quadra e o lote abaixo para gerar automaticamente a tabela de todas as opções de pagamento.")
    
    df_lotes = carregar_dados_lotes()
    
    # LINHA DE FILTROS PRINCIPAIS
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    
    quadras_disp = sorted(df_lotes['Quadra'].dropna().unique()) if not df_lotes.empty else []
    quadra_selecionada = col1.selectbox("Selecione a Quadra", options=[""] + list(quadras_disp))
    
    lote_selecionado = ""
    if quadra_selecionada:
        lotes_disp = df_lotes[df_lotes['Quadra'] == quadra_selecionada]['Lote'].dropna().unique()
        lote_selecionado = col2.selectbox("Selecione o Lote", options=[""] + list(lotes_disp))
    else:
        col2.selectbox("Selecione o Lote", options=[""], disabled=True)
        
    taxa_juros_input = col3.number_input("Taxa de Juros Mensal (%)", value=0.89, step=0.01)
    data_base = col4.date_input("Data de Início", value=datetime.now(), format="DD/MM/YYYY")

    # SE LOTE FOI SELECIONADO, GERA A TABELA MÁGICA
    if quadra_selecionada and lote_selecionado:
        linha = df_lotes[(df_lotes['Quadra'] == quadra_selecionada) & (df_lotes['Lote'] == lote_selecionado)].iloc[0]
        valor_vista_bd = linha['Valor a Vista']
        metragem = linha['Área em Metro Quadrado']
        
        st.markdown("---")
        st.subheader(f"📍 Resumo do Imóvel: QD {quadra_selecionada} / LT {lote_selecionado}")
        m1, m2 = st.columns(2)
        m1.metric("Área", f"{metragem:.2f} m²")
        m2.metric("Valor à Vista", formatar_moeda(valor_vista_bd))
        
        st.markdown("### 📋 Tabela de Planos Sugeridos (Pronto para Print)")
        st.caption("Nota: Para todos os planos contendo balão, a simulação calculou o Balão e a Parcela com o *mesmo valor* numérico para zerar o saldo devedor. Se desejar definir um valor de balão diferente, utilize o simulador detalhado abaixo.")
        
        # Gera a Tabela Matadora
        df_planos = gerar_tabela_todos_planos(valor_vista_bd, taxa_juros_input, datetime.combine(data_base, datetime.min.time()))
        st.dataframe(df_planos, use_container_width=True, hide_index=True)
        
        # EXPANSOR PARA SIMULAÇÃO DETALHADA / EXPORTAÇÃO
        with st.expander("🛠️ Simulador Personalizado / Exportar PDF"):
            st.markdown("Use esta área apenas se quiser alterar regras (ex: balões com valores diferentes) ou gerar o PDF do cronograma mês a mês de um único plano.")
            
            # Reciclando o form antigo de forma simplificada
            valor_calc_manual = st.number_input("Valor Financiado Manual", value=float(valor_vista_bd))
            # Você pode manter ou colar aqui toda a lógica do 'with st.form("simulador_form")'
            # original que eu te passei na resposta anterior, se precisar da geração do Excel.
            st.info("Para focar na tela de print, esta área detalhada foi compactada. Se precisar do exportador em PDF de volta aqui, me avise!")

if __name__ == '__main__':
    main()
