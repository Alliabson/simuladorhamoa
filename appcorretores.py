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
FPDF = install_and_import('fpdf2', 'fpdf').FPDF
install_and_import('openpyxl')

# --- Configuração da Página Streamlit e Tema ---
st.set_page_config(layout="wide", page_title="Simulador Imobiliária Celeste")

def set_theme():
    st.markdown("""
    <style>
        .stApp { background-color: #1E1E1E; }
        [data-testid="stSidebar"] { background-color: #252526; }
        h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #FFFFFF !important; }
        .stMarkdown p, .stMarkdown li, .stText, .stNumberInput label, .stSelectbox label, .stDateInput label { color: #E0E0E0 !important; }
        .stTextInput input, .stNumberInput input, .stSelectbox select, .stDateInput input {
            background-color: #333333 !important; color: #FFFFFF !important; border-color: #555555 !important;
        }
        .stMetric { background-color: #252526; border-radius: 8px; padding: 15px; border-left: 4px solid #4D6BFE; }
        .stMetric label { color: #A0A0A0 !important; }
        .stMetric div { color: #FFFFFF !important; font-size: 24px !important; }
        .dataframe { background-color: #252526 !important; color: #E0E0E0 !important; width: 100% !important; font-size: 14px !important;}
        .dataframe th { background-color: #4D6BFE !important; color: white !important; text-align: center !important;}
        .dataframe td { text-align: center !important; }
        .dataframe tr:nth-child(even) { background-color: #333333 !important; }
        .dataframe tr:hover { background-color: #444444 !important; }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"], div[data-testid="stForm"] button[kind="secondary"], .stDownloadButton button {
            background-color: #4D6BFE !important; color: white !important; border: none !important; border-radius: 12px !important;
            padding: 10px 24px !important; font-weight: 600 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important; width: 100% !important;
        }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover, div[data-testid="stForm"] button[kind="secondary"]:hover, .stDownloadButton button:hover {
            background-color: #FF4D4D !important; transform: translateY(-2px) !important; box-shadow: 0 4px 8px rgba(255, 77, 77, 0.2) !important;
        }
    </style>
    """, unsafe_allow_html=True)

# --- Carregamento de Dados ---
@st.cache_data(ttl=3600)
def carregar_dados_lotes():
    try: df = pd.read_excel("Lotes.xlsx")
    except Exception:
        try: df = pd.read_csv("Lotes.xlsx - Planilha1.csv")
        except Exception: return pd.DataFrame()
    try:
        df['Quadra'] = df['IDENTIFICADOR'].apply(lambda x: str(x).split(' ')[0].replace('QD.', '').strip() if pd.notnull(x) else '')
        df['Lote'] = df['IDENTIFICADOR'].apply(lambda x: str(x).split(' ')[1].replace('LT.', '').strip() if pd.notnull(x) and len(str(x).split(' ')) > 1 else '')
        return df
    except Exception: return pd.DataFrame()

# --- Funções Matemáticas e Financeiras (EXATAMENTE COMO NO SEU ORIGINAL) ---
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
    if dias <= 0 or taxa_diaria <= 0: return float(valor_futuro)
    return round(float(valor_futuro) / ((1 + taxa_diaria) ** dias), 2)

def calcular_fator_vp(datas_vencimento, data_inicio, taxa_diaria):
    if taxa_diaria <= 0: return float(len(datas_vencimento))
    fator_total = 0.0
    for data_venc in datas_vencimento:
        if not isinstance(data_venc, datetime): data_venc = datetime.strptime(data_venc, '%d/%m/%Y')
        dias_comerciais = ((data_venc.year - data_inicio.year) * 12 + (data_venc.month - data_inicio.month)) * 30
        if dias_comerciais > 0: fator_total += 1 / ((1 + taxa_diaria) ** dias_comerciais)
    return fator_total

def ajustar_data_vencimento(data_base, periodo, num_periodo=1, dia_vencimento=None):
    if not isinstance(data_base, datetime): data_base = datetime.combine(data_base, datetime.min.time())
    dia = dia_vencimento if dia_vencimento is not None else data_base.day
    months_to_add = num_periodo if periodo == "mensal" else (6 * num_periodo if periodo == "semestral" else (12 * num_periodo if periodo == "anual" else 0))
    if months_to_add == 0: return data_base
    total_meses = data_base.month + months_to_add
    novo_ano = data_base.year + (total_meses - 1) // 12
    novo_mes = (total_meses - 1) % 12 + 1
    try: return datetime(novo_ano, novo_mes, dia)
    except ValueError: return datetime(novo_ano, novo_mes, (datetime(novo_ano, novo_mes + 1, 1) - timedelta(days=1)).day if novo_mes < 12 else 31)

def determinar_modo_calculo(modalidade):
    return {"mensal": 1, "mensal + balão": 2, "só balão anual": 3, "só balão semestral": 4}.get(modalidade, 1)

def atualizar_baloes(modalidade, qtd_parcelas, tipo_balao=None):
    try:
        qtd_parcelas = int(qtd_parcelas) if qtd_parcelas else 0
        if modalidade == "mensal + balão": return qtd_parcelas // (12 if tipo_balao == "anual" else 6)
        return 0
    except Exception: return 0

# --- GERADOR DE CRONOGRAMA ORIGINAL ---
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
            if agendamento_baloes == "Personalizado (Mês a Mês)": datas_baloes_a_gerar = [ajustar_data_vencimento(data_entrada, "mensal", mes, dia_vencimento_real) for mes in meses_baloes]
            elif agendamento_baloes == "A partir do 1º Vencimento":
                primeira_data_balao = ajustar_data_vencimento(data_entrada, "mensal", mes_primeiro_balao, dia_vencimento_real)
                datas_baloes_a_gerar.append(primeira_data_balao)
                data_anterior = primeira_data_balao
                for _ in range(1, qtd_baloes):
                    proxima_data_balao = ajustar_data_vencimento(data_anterior, tipo_balao, 1, dia_vencimento_real)
                    datas_baloes_a_gerar.append(proxima_data_balao)
                    data_anterior = proxima_data_balao
            else: datas_baloes_a_gerar = [ajustar_data_vencimento(data_entrada, tipo_balao, i, dia_vencimento_real) for i in range(1, qtd_baloes + 1)]

        for i, data_vencimento in enumerate(datas_baloes_a_gerar):
            balao_count = i + 1
            if balao_count in baloes_especiais: valor_corrente = baloes_especiais[balao_count]
            else: valor_corrente = valor_ultimo_balao if (balao_count == qtd_baloes and valor_ultimo_balao is not None) else valor_balao_final
            dias_comerciais = ((data_vencimento.year - data_entrada.year) * 12 + (data_vencimento.month - data_entrada.month)) * 30
            vp = calcular_valor_presente(valor_corrente, taxas['diaria'], dias_comerciais)
            baloes.append({"Item": f"Balão {balao_count}", "Tipo": "Balão", "Data_Vencimento": data_vencimento.strftime('%d/%m/%Y'), "Dias": dias_comerciais, "Valor": round(valor_corrente, 2), "Valor_Presente": round(vp, 2), "Desconto_Aplicado": round(valor_corrente - vp, 2)})

        cronograma = sorted(parcelas, key=lambda x: datetime.strptime(x['Data_Vencimento'], '%d/%m/%Y')) + sorted(baloes, key=lambda x: datetime.strptime(x['Data_Vencimento'], '%d/%m/%Y'))
        if cronograma:
            total_valor = round(sum(p['Valor'] for p in cronograma), 2)
            valor_presente_real = round(sum(p['Valor_Presente'] for p in cronograma), 2)
            cronograma.append({"Item": "TOTAL", "Tipo": "", "Data_Vencimento": "", "Dias": "", "Valor": total_valor, "Valor_Presente": valor_presente_real, "Desconto_Aplicado": round(total_valor - valor_presente_real, 2)})
        return cronograma
    except Exception as e: st.error(f"Erro inesperado ao gerar cronograma: {str(e)}."); return []

def gerar_pdf(cronograma, dados):
    try:
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Informações do Imóvel", ln=1, align='L'); pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Quadra: {dados.get('quadra', 'N/I')}", ln=1); pdf.cell(200, 10, txt=f"Lote: {dados.get('lote', 'N/I')}", ln=1); pdf.cell(200, 10, txt=f"Metragem: {dados.get('metragem', 'N/I')} m²", ln=1)
        pdf.ln(5); pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Simulação de Financiamento", ln=1, align='L'); pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Valor Total do Imóvel: {formatar_moeda(dados['valor_total'])}", ln=1); pdf.cell(200, 10, txt=f"Entrada: {formatar_moeda(dados['entrada'])}", ln=1); pdf.cell(200, 10, txt=f"Valor Financiado: {formatar_moeda(dados['valor_financiado'])}", ln=1); pdf.cell(200, 10, txt=f"Taxa Mensal Utilizada: {dados['taxa_mensal']:.3f}%", ln=1)
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
        info_df = pd.DataFrame({'Campo': ['Quadra', 'Lote', 'Metragem', 'Valor Total do Imóvel', 'Entrada', 'Valor Financiado', 'Taxa Mensal Utilizada'], 'Valor': [dados.get('quadra', 'N/I'), dados.get('lote', 'N/I'), f"{dados.get('metragem', 'N/I')} m²", formatar_moeda(dados.get('valor_total', 0)), formatar_moeda(dados.get('entrada', 0)), formatar_moeda(dados.get('valor_financiado', 0)), f"{dados.get('taxa_mensal', 0):.3f}%"]})
        df_cronograma_data = pd.DataFrame([p for p in cronograma if p['Item'] != 'TOTAL']).rename(columns={'Desconto_Aplicado': 'Juros'})
        total_row = next((p for p in cronograma if p['Item'] == 'TOTAL'), None)
        if total_row: total_row['Juros'] = total_row.get('Desconto_Aplicado')
        df_final = pd.concat([df_cronograma_data, pd.DataFrame([total_row])], ignore_index=True) if total_row else df_cronograma_data
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            info_df.to_excel(writer, sheet_name='Informações da Simulação', index=False)
            df_final[['Item', 'Tipo', 'Data_Vencimento', 'Valor', 'Valor_Presente', 'Juros']].to_excel(writer, sheet_name='Cronograma de Pagamentos', index=False)
        output.seek(0); return output
    except Exception: return BytesIO()

# --- Lógica da Tabela Mestra (com Cálculo Assertivo Original) ---
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

def gerar_tabela_todos_planos(valor_total, data_base, v_parcela_inf, v_balao_inf):
    resultados = []
    for plano in PLANOS_DISPONIVEIS:
        match_p = re.search(r'(\d+)\s*[Pp]arcelas', plano)
        qtd_parcelas = int(match_p.group(1)) if match_p else 0
        match_b = re.search(r'(\d+)\s*[Bb]al[õo]es', plano, re.IGNORECASE)
        qtd_baloes = int(match_b.group(1)) if match_b else 0
        match_e = re.search(r'(\d+)%\s*de\s*entrada', plano)
        pct_entrada = float(match_e.group(1))/100 if match_e else 0.10

        if 1 <= qtd_parcelas <= 36: taxa_mensal = 0.0
        elif 37 <= qtd_parcelas <= 48: taxa_mensal = 0.395
        elif 49 <= qtd_parcelas <= 60: taxa_mensal = 0.59
        elif 61 <= qtd_parcelas <= 156: taxa_mensal = 0.79
        else: taxa_mensal = 0.0
            
        taxas = calcular_taxas(taxa_mensal)
        entrada_total = valor_total * pct_entrada
        entrada_3x = entrada_total / 3
        valor_financiado = valor_total - entrada_total

        datas_p = [ajustar_data_vencimento(data_base, "mensal", i, data_base.day) for i in range(1, qtd_parcelas + 1)]
        datas_b = [ajustar_data_vencimento(data_base, "anual", i, data_base.day) for i in range(1, qtd_baloes + 1)]

        fator_vp_p = calcular_fator_vp(datas_p, data_base, taxas['diaria'])
        fator_vp_b = calcular_fator_vp(datas_b, data_base, taxas['diaria'])

        # CÁLCULO ASSERTIVO ORIGINAL (Usando a sua fórmula do formulário)
        if taxa_mensal == 0.0:
            if qtd_baloes > 0 and v_parcela_inf == 0 and v_balao_inf == 0:
                total_items = qtd_parcelas + qtd_baloes
                val_u = valor_financiado / total_items if total_items > 0 else 0
                str_p, str_b = formatar_moeda(val_u), formatar_moeda(val_u)
            else:
                if qtd_baloes > 0:
                    if v_parcela_inf > 0:
                        vp_rest = valor_financiado - (v_parcela_inf * qtd_parcelas)
                        str_p = formatar_moeda(v_parcela_inf)
                        str_b = formatar_moeda(vp_rest / qtd_baloes if qtd_baloes > 0 else 0)
                    elif v_balao_inf > 0:
                        vp_rest = valor_financiado - (v_balao_inf * qtd_baloes)
                        str_p = formatar_moeda(vp_rest / qtd_parcelas if qtd_parcelas > 0 else 0)
                        str_b = formatar_moeda(v_balao_inf)
                    else:
                        str_p, str_b = "Requer Input", "Requer Input"
                else:
                    str_p = formatar_moeda(valor_financiado / qtd_parcelas if qtd_parcelas > 0 else 0)
                    str_b = "-"
        else:
            if qtd_baloes > 0:
                if v_parcela_inf > 0:
                    vp_p = v_parcela_inf * fator_vp_p
                    vp_b = valor_financiado - vp_p
                    str_p = formatar_moeda(v_parcela_inf)
                    str_b = formatar_moeda(vp_b / fator_vp_b if fator_vp_b > 0 else 0)
                elif v_balao_inf > 0:
                    vp_b = v_balao_inf * fator_vp_b
                    vp_p = valor_financiado - vp_b
                    str_p = formatar_moeda(vp_p / fator_vp_p if fator_vp_p > 0 else 0)
                    str_b = formatar_moeda(v_balao_inf)
                else:
                    str_p, str_b = "Pendente (Informe Parcela/Balão acima)", "Pendente (Informe Parcela/Balão acima)"
            else:
                str_p = formatar_moeda(valor_financiado / fator_vp_p if fator_vp_p > 0 else 0)
                str_b = "-"

        nome_exibicao = f"{qtd_parcelas}x"
        if qtd_baloes > 0: nome_exibicao += f" + {qtd_baloes} Balões"

        resultados.append({
            "Plano": nome_exibicao,
            "Taxa (a.m.)": f"{taxa_mensal:.3f}%".replace('.', ','),
            "Entrada (%)": f"{int(pct_entrada*100)}%",
            "Entrada Total": formatar_moeda(entrada_total),
            "Sinal (Entrada em 3x)": formatar_moeda(entrada_3x),
            "Valor da Parcela": str_p,
            "Valor do Balão (Anual)": str_b,
            "Valor Financiado": formatar_moeda(valor_financiado)
        })
    return pd.DataFrame(resultados)

# --- FUNÇÃO PRINCIPAL DO APLICATIVO ---
def main():
    set_theme()
    st.write("\n")
    st.title("Simulador Imobiliária Celeste")
    
    df_lotes = carregar_dados_lotes()
    
    # 1. Seleção Básica (Para a Tabela)
    col1, col2, col3 = st.columns([2, 2, 2])
    quadras_disp = sorted(df_lotes['Quadra'].dropna().unique()) if not df_lotes.empty else []
    quadra_selecionada = col1.selectbox("Selecione a Quadra", options=[""] + list(quadras_disp))
    
    lote_selecionado = ""
    if quadra_selecionada:
        lotes_disp = df_lotes[df_lotes['Quadra'] == quadra_selecionada]['Lote'].dropna().unique()
        lote_selecionado = col2.selectbox("Selecione o Lote", options=[""] + list(lotes_disp))
    else:
        col2.selectbox("Selecione o Lote", options=[""], disabled=True)
        
    data_base = col3.date_input("Data de Início do Contrato", value=datetime.now(), format="DD/MM/YYYY")

    if quadra_selecionada and lote_selecionado:
        linha = df_lotes[(df_lotes['Quadra'] == quadra_selecionada) & (df_lotes['Lote'] == lote_selecionado)].iloc[0]
        valor_vista_bd = float(linha['Valor a Vista'])
        metragem = float(linha['Área em Metro Quadrado'])
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader(f"📍 Resumo do Imóvel Selecionado: QD {quadra_selecionada} / LT {lote_selecionado}")
        m1, m2 = st.columns(2)
        m1.metric("📐 Área Total", f"{metragem:.2f} m²")
        m2.metric("💰 Valor à Vista", formatar_moeda(valor_vista_bd))
        
        # TABELA AUTOMÁTICA
        st.markdown("---")
        st.markdown("### 📋 Tabela Resumo de Todos os Planos (Pronto para Print)")
        st.caption("ℹ️ Para que a tabela consiga calcular os planos **COM BALÃO**, informe o valor desejado para a Parcela OU para o Balão abaixo. Se deixar zerado, o sistema divide igual (se juros for 0%).")
        
        c_p, c_b = st.columns(2)
        v_parcela_tab = c_p.number_input("Valor Desejado da PARCELA (R$) (Opcional)", value=0.0, step=100.0)
        v_balao_tab = c_b.number_input("Valor Desejado do BALÃO (R$) (Opcional)", value=0.0, step=1000.0)
        
        data_calculo = datetime.combine(data_base, datetime.min.time())
        df_planos = gerar_tabela_todos_planos(valor_vista_bd, data_calculo, v_parcela_tab, v_balao_tab)
        st.dataframe(df_planos, use_container_width=True, hide_index=True)
        
        # O SEU SIMULADOR MANUAL ORIGINAL VOLTOU AQUI:
        st.markdown("---")
        with st.expander("🛠️ SIMULADOR DETALHADO ORIGINAL (Exportar PDF e Excel)", expanded=True):
            st.markdown("Esta área funciona **exatamente** como o seu código original. Utilize para gerar os cronogramas mês a mês e exportar os arquivos.")
            
            def reset_form(): 
                st.session_state.clear()
            
            with st.form("simulador_form_original"):
                col1_f, col2_f = st.columns(2)
                with col1_f:
                    # Preenche os dados automaticamente do BD, mas você pode editar se quiser!
                    valor_total_str = st.text_input("Valor Total do Imóvel (R$)", value=f"{valor_vista_bd:.2f}".replace('.', ','), key="valor_total_str")
                    entrada_str = st.text_input("Entrada (R$)", value=f"{(valor_vista_bd*0.10):.2f}".replace('.', ','), key="entrada_str")
                    data_input = st.date_input("Data de Entrada", value=datetime.now(), format="DD/MM/YYYY", key="data_input_f")
                    
                    # Taxa de Juros Manual (como era antes)
                    taxa_mensal_str = st.text_input("Taxa de Juros Mensal (%)", value="0,89", key="taxa_mensal_str", placeholder="Ex: 0,89")
                    modalidade = st.selectbox("Modalidade de Pagamento", ["mensal", "mensal + balão", "só balão anual", "só balão semestral"], key="modalidade")
                    
                    tipo_balao, agendamento_baloes, meses_baloes, mes_primeiro_balao = None, "Padrão", [], 12
                    
                    if "balão" in modalidade: 
                        if modalidade == "mensal + balão": tipo_balao = st.selectbox("Período Padrão do Balão:", ["anual", "semestral"], key="tipo_balao")
                        elif "anual" in modalidade: tipo_balao = "anual"
                        elif "semestral" in modalidade: tipo_balao = "semestral"

                        agendamento_baloes = st.selectbox("Agendamento dos Balões", ["Padrão", "A partir do 1º Vencimento", "Personalizado (Mês a Mês)"], key="agendamento_baloes")
                        if agendamento_baloes == "Personalizado (Mês a Mês)":
                            meses_baloes = st.multiselect("Selecione os meses dos balões:", options=list(range(1, 361)), key="meses_baloes")
                        elif agendamento_baloes == "A partir do 1º Vencimento":
                            mes_primeiro_balao = st.number_input("Mês de Vencimento do 1º Balão", min_value=1, value=(12 if tipo_balao == 'anual' else 6), step=1, key="mes_primeiro_balao")

                with col2_f:
                    qtd_parcelas, qtd_baloes = 0, 0
                    if not modalidade.startswith("só balão"): qtd_parcelas = st.number_input("Quantidade de Parcelas", min_value=0, step=1, key="qtd_parcelas")

                    if "balão" in modalidade:
                        if agendamento_baloes == "Personalizado (Mês a Mês)":
                            qtd_baloes = len(meses_baloes)
                            st.write(f"Quantidade de Balões: **{qtd_baloes}**")
                            if modalidade.startswith("só balão"): st.number_input("Quantidade de Balões", value=qtd_baloes, disabled=True, key="qtd_baloes_disabled")
                        elif modalidade.startswith("só balão"):
                            qtd_baloes = st.number_input("Quantidade de Balões", min_value=0, step=1, key="qtd_baloes_direto")
                        else:
                            qtd_baloes = atualizar_baloes(modalidade, qtd_parcelas, tipo_balao)
                            st.write(f"Quantidade de Balões: **{qtd_baloes}**")

                    valor_parcela_str = ""
                    if not modalidade.startswith("só balão"):
                        valor_parcela_str = st.text_input("Valor da Parcela (R$)", key="valor_parcela_str", placeholder="Deixe em branco para cálculo")

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
                with col_b1: submitted = st.form_submit_button("Calcular Cronograma")
                with col_b2: st.form_submit_button("Limpar Formulário", on_click=reset_form)
            
            # --- PROCESSAMENTO EXATO DA LÓGICA ORIGINAL ---
            if submitted:
                try:
                    valor_total = parse_currency(valor_total_str)
                    entrada = parse_currency(entrada_str)
                    valor_parcela = parse_currency(valor_parcela_str)
                    valor_balao = parse_currency(valor_balao_str)
                    
                    # Usa a faixa de juros pela quantidade de parcelas se houver, senao usa o manual
                    if 1 <= qtd_parcelas <= 36: taxa_mensal_para_calculo = 0.0
                    elif 37 <= qtd_parcelas <= 48: taxa_mensal_para_calculo = 0.395
                    elif 49 <= qtd_parcelas <= 60: taxa_mensal_para_calculo = 0.59
                    elif 61 <= qtd_parcelas <= 156: taxa_mensal_para_calculo = 0.79
                    else: taxa_mensal_para_calculo = parse_percentage(taxa_mensal_str)
                    
                    if valor_total <= 0 or entrada < 0 or valor_total <= entrada: 
                        st.error("Verifique os valores de 'Total do Imóvel' e 'Entrada'.")
                        st.stop()
                    
                    valor_financiado = round(max(valor_total - entrada, 0), 2)
                    taxas = calcular_taxas(taxa_mensal_para_calculo)
                    v_p_final, v_b_final = 0.0, 0.0
                    data_entrada = datetime.combine(data_input, datetime.min.time())
                    dia_vencimento = data_entrada.day
                    
                    # LOGICA DE DESCAPITALIZAÇÃO EXATA (IGUAL SEU CÓDIGO)
                    if taxa_mensal_para_calculo == 0.0:
                        vp_baloes_especiais = sum(baloes_especiais_input.values())
                        vp_restante = valor_financiado - vp_baloes_especiais
                        num_baloes_regulares = qtd_baloes - len(baloes_especiais_input)

                        if valor_parcela > 0: 
                            v_p_final = valor_parcela
                            vp_parcelas = v_p_final * qtd_parcelas
                            vp_restante -= vp_parcelas
                            if num_baloes_regulares > 0 and vp_restante > 0: v_b_final = round(vp_restante / num_baloes_regulares, 2)
                        elif valor_balao > 0: 
                            v_b_final = valor_balao
                            vp_baloes_reg = v_b_final * num_baloes_regulares
                            vp_restante -= vp_baloes_reg
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
                        if vp_restante < 0: st.error("O valor presente dos balões especiais excede o valor financiado."); st.stop()
                        
                        fator_vp_p = calcular_fator_vp(datas_p, data_entrada, taxas['diaria'])
                        fator_vp_b_reg = calcular_fator_vp(datas_b_regulares, data_entrada, taxas['diaria'])
                        
                        if valor_parcela > 0 and valor_balao == 0: 
                            v_p_final = valor_parcela
                            vp_das_parcelas = v_p_final * fator_vp_p
                            vp_para_baloes = vp_restante - vp_das_parcelas
                            if fator_vp_b_reg > 0 and vp_para_baloes > 0: v_b_final = round(vp_para_baloes / fator_vp_b_reg, 2)
                        elif valor_balao > 0 and valor_parcela == 0: 
                            v_b_final = valor_balao
                            vp_dos_baloes_reg = v_b_final * fator_vp_b_reg
                            vp_para_parcelas = vp_restante - vp_dos_baloes_reg
                            if fator_vp_p > 0 and vp_para_parcelas > 0: v_p_final = round(vp_para_parcelas / fator_vp_p, 2)
                        elif valor_parcela == 0 and valor_balao == 0: 
                            if fator_vp_p > 0 and fator_vp_b_reg == 0: v_p_final = round(vp_restante / fator_vp_p, 2) if fator_vp_p > 0 else 0
                            elif fator_vp_b_reg > 0 and fator_vp_p == 0: v_b_final = round(vp_restante / fator_vp_b_reg, 2) if fator_vp_b_reg > 0 else 0
                            else: st.error("Para cálculo automático, informe o valor da Parcela OU do Balão Padrão."); st.stop()
                        else: 
                            v_p_final = valor_parcela
                            v_b_final = valor_balao

                    cronograma = gerar_cronograma(valor_financiado, v_p_final, v_b_final, (qtd_parcelas or 0), qtd_baloes, modalidade, tipo_balao, data_entrada, taxas, agendamento_baloes=agendamento_baloes, meses_baloes=meses_baloes, mes_primeiro_balao=mes_primeiro_balao, baloes_especiais=baloes_especiais_input)
                    
                    st.subheader("Resultados da Simulação")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Valor Financiado", formatar_moeda(valor_financiado)); c2.metric("Taxa Mensal Utilizada", f"{taxa_mensal_para_calculo:.3f}%")
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
                            
                            st.subheader("Exportar Resultados")
                            export_data = {'valor_total': valor_total, 'entrada': entrada, 'taxa_mensal': taxa_mensal_para_calculo, 'valor_financiado': valor_financiado, 'quadra': quadra_selecionada, 'lote': lote_selecionado, 'metragem': metragem}
                            c1_exp, c2_exp = st.columns(2)
                            pdf_file = gerar_pdf(cronograma, export_data); c1_exp.download_button("Exportar para PDF", pdf_file, "simulacao.pdf", "application/pdf")
                            excel_file = gerar_excel(cronograma, export_data); c2_exp.download_button("Exportar para Excel", excel_file, "simulacao.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                except Exception as e:
                    st.error(f"Ocorreu um erro durante a simulação: {str(e)}. Por favor, verifique os valores inseridos e tente novamente.")

if __name__ == '__main__':
    main()
