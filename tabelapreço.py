import streamlit as st
from datetime import datetime, timedelta
import locale
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
install_and_import('openpyxl')

# --- Configuração da Página e Tema Customizado ---
st.set_page_config(layout="wide", page_title="Gerador de Tabelas Celeste")

def set_theme():
    st.markdown("""
    <style>
        .stApp { background-color: #1E1E1E; }
        h1, h2, h3, h4, h5, h6, .stMarkdown p, .stMarkdown li, .stText, label { color: #FFFFFF !important; }
        .stTextInput input, .stNumberInput input, .stSelectbox select, .stDateInput input {
            background-color: #333333 !important; color: #FFFFFF !important; border-color: #555555 !important;
        }
        .dataframe { background-color: #252526 !important; color: #E0E0E0 !important; width: 100% !important; font-size: 13px !important;}
        .dataframe th { background-color: #4D6BFE !important; color: white !important; text-align: center !important;}
        .dataframe td { text-align: center !important; border-bottom: 1px solid #444 !important; }
        
        /* ESTILO DOS BOTÕES PADRÃO E EXPORTAÇÃO */
        .stButton button, .stDownloadButton button {
            background-color: #4D6BFE !important; color: white !important; border: none !important; border-radius: 12px !important;
            padding: 10px 24px !important; font-weight: 600 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important; width: 100% !important;
        }
        .stButton button:hover, .stDownloadButton button:hover { 
            background-color: #FF4D4D !important; transform: translateY(-2px) !important; box-shadow: 0 4px 8px rgba(255, 77, 77, 0.2) !important; 
        }
        
        .upload-text { font-size: 18px; color: #A0A0A0; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- Funções Matemáticas e Financeiras (Da sua Lógica Original) ---
def calcular_taxas(taxa_mensal_percentual):
    try:
        taxa_mensal_decimal = float(taxa_mensal_percentual) / 100
        taxa_diaria = ((1 + taxa_mensal_decimal) ** (1/30)) - 1
        return {'mensal': taxa_mensal_decimal, 'diaria': taxa_diaria}
    except Exception: return {'mensal': 0, 'diaria': 0}

def ajustar_data_vencimento(data_base, periodo, num_periodo=1, dia_vencimento=None):
    if not isinstance(data_base, datetime): data_base = datetime.combine(data_base, datetime.min.time())
    dia = dia_vencimento if dia_vencimento is not None else data_base.day
    
    if periodo == "mensal": months_to_add = num_periodo
    elif periodo == "semestral": months_to_add = 6 * num_periodo
    elif periodo == "anual": months_to_add = 12 * num_periodo
    else: months_to_add = 0
        
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

# --- LISTA DE PLANOS OFICIAIS ---
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

def extrair_dados_plano(plano_str):
    match_p = re.search(r'(\d+)\s*[Pp]arcelas', plano_str)
    qtd_parcelas = int(match_p.group(1)) if match_p else 0
    match_b = re.search(r'(\d+)\s*[Bb]al[õo]es', plano_str, re.IGNORECASE)
    qtd_baloes = int(match_b.group(1)) if match_b else 0
    match_e = re.search(r'(\d+)%\s*de\s*entrada', plano_str)
    pct_entrada = float(match_e.group(1))/100 if match_e else 0.10

    if 1 <= qtd_parcelas <= 36: taxa_mensal = 0.0
    elif 37 <= qtd_parcelas <= 48: taxa_mensal = 0.395
    elif 49 <= qtd_parcelas <= 60: taxa_mensal = 0.59
    elif 61 <= qtd_parcelas <= 156: taxa_mensal = 0.79
    else: taxa_mensal = 0.0
        
    return qtd_parcelas, qtd_baloes, pct_entrada, taxa_mensal

# --- PRÉ-CÁLCULO DOS FATORES PARA PERFORMANCE (Muito rápido!) ---
@st.cache_data
def pre_calcular_fatores(data_base_str):
    data_base = datetime.strptime(data_base_str, "%Y-%m-%d")
    fatores_planos = {}
    
    for plano in PLANOS_DISPONIVEIS:
        qtd_p, qtd_b, pct_e, t_mensal = extrair_dados_plano(plano)
        taxas = calcular_taxas(t_mensal)
        
        datas_p = [ajustar_data_vencimento(data_base, "mensal", i, data_base.day) for i in range(1, qtd_p + 1)]
        f_vp_p = calcular_fator_vp(datas_p, data_base, taxas['diaria'])
        
        datas_b = [ajustar_data_vencimento(data_base, "anual", i, data_base.day) for i in range(1, qtd_b + 1)]
        f_vp_b = calcular_fator_vp(datas_b, data_base, taxas['diaria'])
        
        fatores_planos[plano] = {
            'qtd_p': qtd_p, 'qtd_b': qtd_b, 'pct_e': pct_e, 
            'f_vp_p': f_vp_p, 'f_vp_b': f_vp_b,
            'nome_col': f"{qtd_p}x" + (f" + {qtd_b}B" if qtd_b > 0 else "")
        }
    return fatores_planos

# --- GERAÇÃO DA TABELA MASTER ---
def gerar_tabela_master(df_lotes, data_base):
    # Pré-calcula os fatores matemáticos 1 única vez para velocidade
    fatores = pre_calcular_fatores(data_base.strftime("%Y-%m-%d"))
    linhas_tabela = []

    progress_bar = st.progress(0)
    total_lotes = len(df_lotes)

    for i, row in df_lotes.iterrows():
        try: v_vista = float(row['Valor a Vista'])
        except: continue
        
        if pd.isna(v_vista) or v_vista <= 0: continue

        # Identificação da linha
        linha_dict = {
            'Quadra': str(row.get('Quadra', '')).replace('.0', ''),
            'Lote': str(row.get('Lote', '')).replace('.0', ''),
            'Área (m²)': float(row.get('Área em Metro Quadrado', 0)),
            'Valor à Vista': v_vista
        }

        # Aplica os 20 planos matematicamente nesse lote
        for plano_nome, fat in fatores.items():
            entrada_total = v_vista * fat['pct_e']
            financiado = v_vista - entrada_total
            
            if fat['qtd_b'] > 0:
                vp_baloes = v_vista * 0.47
                vp_parcelas = financiado - vp_baloes
            else:
                vp_baloes = 0
                vp_parcelas = financiado

            valor_parcela = (vp_parcelas / fat['f_vp_p']) if (fat['qtd_p'] > 0 and fat['f_vp_p'] > 0) else 0
            valor_balao = (vp_baloes / fat['f_vp_b']) if (fat['qtd_b'] > 0 and fat['f_vp_b'] > 0) else 0

            # Preenche as colunas para o Excel (em formato de número real para excel somar)
            prefixo = fat['nome_col']
            linha_dict[f'{prefixo} (Entrada)'] = entrada_total
            linha_dict[f'{prefixo} (Parcela)'] = valor_parcela
            if fat['qtd_b'] > 0:
                linha_dict[f'{prefixo} (Balão Anual)'] = valor_balao

        linhas_tabela.append(linha_dict)
        progress_bar.progress((i + 1) / total_lotes)
        
    progress_bar.empty()
    return pd.DataFrame(linhas_tabela)

# --- APP PRINCIPAL ---
def main():
    set_theme()
    st.write("\n")
    st.title("📊 Gerador de Tabelas de Preços Master")
    st.markdown("Faça o upload da sua planilha bruta de lotes. O sistema calculará todas as condições de pagamento e gerará uma planilha Excel completa e pronta para uso.")
    
    st.markdown("---")
    
    col_up1, col_up2 = st.columns([3, 1])
    
    with col_up1:
        st.markdown("<p class='upload-text'>1. Suba o arquivo Excel Base (Precisa conter: IDENTIFICADOR, Área em Metro Quadrado, Valor a Vista)</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("", type=["xlsx", "csv"])
        
    with col_up2:
        st.markdown("<p class='upload-text'>2. Data de Início Base</p>", unsafe_allow_html=True)
        data_base = st.date_input("", value=datetime.now(), format="DD/MM/YYYY")

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'): df_lotes = pd.read_csv(uploaded_file)
            else: df_lotes = pd.read_excel(uploaded_file)
                
            df_lotes['Quadra'] = df_lotes['IDENTIFICADOR'].apply(lambda x: str(x).split(' ')[0].replace('QD.', '').strip() if pd.notnull(x) else '')
            df_lotes['Lote'] = df_lotes['IDENTIFICADOR'].apply(lambda x: str(x).split(' ')[1].replace('LT.', '').strip() if pd.notnull(x) and len(str(x).split(' ')) > 1 else '')
            
            st.success(f"Planilha carregada com sucesso! {len(df_lotes)} lotes encontrados.")
            
            if st.button("🚀 Gerar Tabela de Preços Completa"):
                data_calculo = datetime.combine(data_base, datetime.min.time())
                
                with st.spinner("Processando todos os lotes e planos. Isso pode levar alguns segundos..."):
                    df_master = gerar_tabela_master(df_lotes, data_calculo)
                
                st.subheader("Pré-visualização da Tabela Gerada")
                
                # Formatação visual apenas para o preview no Streamlit (não afeta o Excel)
                config_colunas = {
                    col: st.column_config.NumberColumn(format="R$ %.2f") 
                    for col in df_master.columns if col not in ['Quadra', 'Lote', 'Área (m²)']
                }
                st.dataframe(df_master, use_container_width=True, hide_index=True, column_config=config_colunas, height=400)
                
                # Preparar para Excel (Exportando como NÚMEROS reais)
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_master.to_excel(writer, index=False, sheet_name='Tabela de Vendas')
                output.seek(0)
                
                st.markdown("---")
                st.markdown("### 📥 Tabela Pronta!")
                st.download_button(
                    label="Baixar Tabela em Excel (.xlsx)",
                    data=output,
                    file_name=f"Tabela_de_Precos_{datetime.now().strftime('%d-%m-%Y')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
        except Exception as e:
            st.error(f"Erro ao processar o arquivo. Verifique se o cabeçalho está correto. Erro: {e}")

if __name__ == '__main__':
    main()
