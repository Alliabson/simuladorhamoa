import streamlit as st
from datetime import datetime, timedelta
from PIL import Image
import locale
import subprocess
import sys
import re

# --- Configuração de Locale (Para formato de moeda em Reais) ---
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

# --- Instalação e Importação de Dependências Dinâmicas ---
def install_and_import(package, import_name=None):
    import_name = import_name or package
    try: return __import__(import_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return __import__(import_name)

pd = install_and_import('pandas')
np = install_and_import('numpy')

# --- Carregamento de Dados (Excel ou CSV) ---
@st.cache_data(ttl=3600)
def carregar_dados_lotes():
    try:
        # Tenta ler a planilha Excel padrão
        df = pd.read_excel("Lotes.xlsx")
    except Exception:
        try:
            # Se falhar (por exemplo, no GitHub), tenta ler o CSV que fizeste upload
            df = pd.read_csv("Lotes.xlsx - Planilha1.csv")
        except Exception as e:
            st.error(f"Erro ao carregar a base de dados de lotes: {e}")
            return pd.DataFrame()
            
    try:
        # Separa a coluna IDENTIFICADOR (Ex: QD.01 LT.01) em Quadra e Lote
        df['Quadra'] = df['IDENTIFICADOR'].apply(lambda x: str(x).split(' ')[0].replace('QD.', '').strip() if pd.notnull(x) else '')
        df['Lote'] = df['IDENTIFICADOR'].apply(lambda x: str(x).split(' ')[1].replace('LT.', '').strip() if pd.notnull(x) and len(str(x).split(' ')) > 1 else '')
        return df
    except Exception as e:
        st.error(f"Erro ao processar as colunas da planilha: {e}")
        return pd.DataFrame()

# --- Funções Auxiliares de Formatação e Cálculo Financeiro ---
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
    
    try: 
        return datetime(novo_ano, novo_mes, dia)
    except ValueError: 
        # Lida com dias que não existem no mês (ex: 31 de Fevereiro)
        return datetime(novo_ano, novo_mes, (datetime(novo_ano, novo_mes + 1, 1) - timedelta(days=1)).day if novo_mes < 12 else 31)

def calcular_fator_vp(datas_vencimento, data_inicio, taxa_diaria):
    """Soma o fator de descapitalização (Valor Presente) para descobrir o valor da parcela/balão."""
    if taxa_diaria <= 0: return float(len(datas_vencimento))
    fator_total = 0.0
    for data_venc in datas_vencimento:
        dias_comerciais = ((data_venc.year - data_inicio.year) * 12 + (data_venc.month - data_inicio.month)) * 30
        if dias_comerciais > 0: 
            fator_total += 1 / ((1 + taxa_diaria) ** dias_comerciais)
    return fator_total

# --- LISTA MESTRA DE PLANOS OFICIAIS ---
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

# --- LÓGICA DE GERAÇÃO DA TABELA ---
def gerar_tabela_todos_planos(valor_total, data_base):
    resultados = []

    for plano in PLANOS_DISPONIVEIS:
        # 1. Extração via Regex (Expressões Regulares) dos dados da string do plano
        match_p = re.search(r'(\d+)\s*[Pp]arcelas', plano)
        qtd_parcelas = int(match_p.group(1)) if match_p else 0
        
        match_b = re.search(r'(\d+)\s*[Bb]al[õo]es', plano, re.IGNORECASE)
        qtd_baloes = int(match_b.group(1)) if match_b else 0
        
        match_e = re.search(r'(\d+)%\s*de\s*entrada', plano)
        pct_entrada = float(match_e.group(1))/100 if match_e else 0.10

        # 2. DEFINIÇÃO DA FAIXA DE JUROS AUTOMÁTICA
        if 1 <= qtd_parcelas <= 36:
            taxa_mensal_para_calculo = 0.0
        elif 37 <= qtd_parcelas <= 48:
            taxa_mensal_para_calculo = 0.395
        elif 49 <= qtd_parcelas <= 60:
            taxa_mensal_para_calculo = 0.59
        elif 61 <= qtd_parcelas <= 156:
            taxa_mensal_para_calculo = 0.79
        else: # Segurança contra anomalias
            taxa_mensal_para_calculo = 0.0
            
        taxas = calcular_taxas(taxa_mensal_para_calculo)
        taxa_diaria = taxas['diaria']

        # 3. Cálculos Iniciais (Entrada e Financiamento)
        entrada_total = valor_total * pct_entrada
        entrada_3x = entrada_total / 3
        valor_financiado = valor_total - entrada_total

        # 4. Construção das Datas e Fator de Valor Presente
        datas_p = [ajustar_data_vencimento(data_base, "mensal", i, data_base.day) for i in range(1, qtd_parcelas + 1)]
        datas_b = [ajustar_data_vencimento(data_base, "anual", i, data_base.day) for i in range(1, qtd_baloes + 1)]

        fator_vp_p = calcular_fator_vp(datas_p, data_base, taxa_diaria)
        fator_vp_b = calcular_fator_vp(datas_b, data_base, taxa_diaria)

        # Assumindo que Parcela e Balão têm o mesmo valor para quitar o saldo
        fator_total = fator_vp_p + fator_vp_b
        valor_uniforme = valor_financiado / fator_total if fator_total > 0 else 0

        # 5. Formatação do Nome de Exibição
        nome_exibicao = f"{qtd_parcelas}x"
        if qtd_baloes > 0: nome_exibicao += f" + {qtd_baloes} Balões"

        # 6. Agrupamento dos Resultados
        resultados.append({
            "Plano": nome_exibicao,
            "Taxa (a.m.)": f"{taxa_mensal_para_calculo:.3f}%".replace('.', ','),
            "Entrada (%)": f"{int(pct_entrada*100)}%",
            "Entrada Total": formatar_moeda(entrada_total),
            "Sinal (Entrada em 3x)": formatar_moeda(entrada_3x),
            "Valor da Parcela": formatar_moeda(valor_uniforme),
            "Valor do Balão (Anual)": formatar_moeda(valor_uniforme) if qtd_baloes > 0 else "-",
            "Valor Financiado": formatar_moeda(valor_financiado)
        })

    return pd.DataFrame(resultados)


# --- Configuração da Página Streamlit e Tema Customizado ---
st.set_page_config(layout="wide", page_title="Simulador JMD HAMOA")

def set_theme():
    st.markdown("""
    <style>
        /* Fundo escuro */
        .stApp { background-color: #1E1E1E; }
        /* Títulos e Textos Brancos */
        h1, h2, h3, h4, .stMarkdown p, .stTextInput label, .stSelectbox label, .stDateInput label { color: #FFFFFF !important; }
        /* Caixas de input escuras */
        .stTextInput input, .stNumberInput input, .stSelectbox select, .stDateInput input { 
            background-color: #333333 !important; 
            color: #FFFFFF !important; 
            border-color: #555555 !important;
        }
        /* Configuração Visual do DataFrame (Tabela) */
        .dataframe { font-size: 14px !important; width: 100% !important; background-color: #252526 !important; color: #E0E0E0 !important;}
        .dataframe th { 
            background-color: #4D6BFE !important; 
            color: white !important; 
            font-weight: bold !important; 
            text-align: center !important;
        }
        .dataframe td { text-align: center !important; border-bottom: 1px solid #444 !important; }
        .dataframe tr:hover { background-color: #333333 !important; }
        /* Cartões de Métricas */
        .stMetric { background-color: #252526; border-radius: 8px; padding: 15px; border-left: 4px solid #4D6BFE; }
        .stMetric label { color: #A0A0A0 !important; }
        .stMetric div { color: #FFFFFF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO PRINCIPAL ---
def main():
    set_theme()
    
    # Cabeçalho e Logo
    col_logo, col_titulo = st.columns([1, 4])
    try:
        logo = Image.open("JMD HAMOA HORIZONTAL - BRANCO.png")
        col_logo.image(logo, width=150)
    except Exception:
        pass # Ignora se a imagem não estiver presente
    
    col_titulo.title("🏡 Simulador de Planos - JMD HAMOA")
    col_titulo.markdown("Selecione a quadra e o lote abaixo para gerar automaticamente a tabela oficial com todas as opções de pagamento.")
    
    # Carrega a base de dados
    df_lotes = carregar_dados_lotes()
    
    st.markdown("---")
    
    # LINHA DE FILTROS PRINCIPAIS
    col1, col2, col3 = st.columns([2, 2, 2])
    
    # Lógica de Quadras Disponíveis
    quadras_disp = sorted(df_lotes['Quadra'].dropna().unique()) if not df_lotes.empty else []
    quadra_selecionada = col1.selectbox("Selecione a Quadra", options=[""] + list(quadras_disp))
    
    # Lógica de Lotes Encadeados
    lote_selecionado = ""
    if quadra_selecionada:
        lotes_disp = df_lotes[df_lotes['Quadra'] == quadra_selecionada]['Lote'].dropna().unique()
        lote_selecionado = col2.selectbox("Selecione o Lote", options=[""] + list(lotes_disp))
    else:
        col2.selectbox("Selecione o Lote", options=[""], disabled=True)
        
    data_base = col3.date_input("Data de Início do Contrato", value=datetime.now(), format="DD/MM/YYYY")

    # QUANDO O USUÁRIO PREENCHE TUDO, A MÁGICA ACONTECE:
    if quadra_selecionada and lote_selecionado:
        # Busca a linha correspondente na base de dados
        linha = df_lotes[(df_lotes['Quadra'] == quadra_selecionada) & (df_lotes['Lote'] == lote_selecionado)].iloc[0]
        valor_vista_bd = linha['Valor a Vista']
        metragem = linha['Área em Metro Quadrado']
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader(f"📍 Resumo do Imóvel Selecionado: QD {quadra_selecionada} / LT {lote_selecionado}")
        
        m1, m2 = st.columns(2)
        m1.metric("📐 Área Total", f"{metragem:.2f} m²")
        m2.metric("💰 Valor à Vista", formatar_moeda(valor_vista_bd))
        
        st.markdown("<br>### 📋 Tabela de Pagamentos (Pronto para Captura de Ecrã)", unsafe_allow_html=True)
        st.caption("ℹ️ Nota: As taxas de juros são aplicadas automaticamente conforme a faixa de parcelas. Nas modalidades com balão anual, o valor projetado iguala a parcela para viabilizar a quitação.")
        
        # Gera e exibe o DataFrame formatado
        df_planos = gerar_tabela_todos_planos(valor_vista_bd, datetime.combine(data_base, datetime.min.time()))
        st.dataframe(df_planos, use_container_width=True, hide_index=True)

if __name__ == '__main__':
    main()
