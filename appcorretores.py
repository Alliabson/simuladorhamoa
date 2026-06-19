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

# --- Configuração da Página e Tema Customizado ---
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
        .dataframe td { text-align: center !important; border-bottom: 1px solid #444 !important; }
        .dataframe tr:hover { background-color: #333333 !important; }
        .stDownloadButton button {
            background-color: #4D6BFE !important; color: white !important; border: none !important; border-radius: 12px !important;
            padding: 10px 24px !important; font-weight: 600 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important; width: 100% !important;
        }
        .stDownloadButton button:hover { background-color: #FF4D4D !important; transform: translateY(-2px) !important; box-shadow: 0 4px 8px rgba(255, 77, 77, 0.2) !important; }
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

# --- Funções Matemáticas e Financeiras ---
def formatar_moeda(valor, simbolo=True):
    try:
        if valor is None or valor == '': return "R$ 0,00" if simbolo else "0,00"
        if isinstance(valor, str): valor = float(re.sub(r'\.', '', str(valor)).replace(',', '.'))
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

def calcular_valor_presente(valor_futuro, taxa_diaria, dias):
    if dias <= 0 or taxa_diaria <= 0: return float(valor_futuro)
    return round(float(valor_futuro) / ((1 + taxa_diaria) ** dias), 2)

def calcular_fator_vp(datas_vencimento, data_inicio, taxa_diaria):
    """ Calcula a soma dos fatores de descapitalização (equivalente a fórmula PGTO no Excel) """
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
    """ Lê a string do plano e descobre quantidades, entrada e taxa aplicável. """
    match_p = re.search(r'(\d+)\s*[Pp]arcelas', plano_str)
    qtd_parcelas = int(match_p.group(1)) if match_p else 0
    
    match_b = re.search(r'(\d+)\s*[Bb]al[õo]es', plano_str, re.IGNORECASE)
    qtd_baloes = int(match_b.group(1)) if match_b else 0
    
    match_e = re.search(r'(\d+)%\s*de\s*entrada', plano_str)
    pct_entrada = float(match_e.group(1))/100 if match_e else 0.10

    # Lógica de faixas de juros informada por você
    if 1 <= qtd_parcelas <= 36: taxa_mensal = 0.0
    elif 37 <= qtd_parcelas <= 48: taxa_mensal = 0.395
    elif 49 <= qtd_parcelas <= 60: taxa_mensal = 0.59
    elif 61 <= qtd_parcelas <= 156: taxa_mensal = 0.79
    else: taxa_mensal = 0.0
        
    return qtd_parcelas, qtd_baloes, pct_entrada, taxa_mensal

def gerar_tabela_todos_planos(valor_vista, data_base):
    resultados = []
    
    for plano in PLANOS_DISPONIVEIS:
        qtd_parcelas, qtd_baloes, pct_entrada, taxa_mensal = extrair_dados_plano(plano)
        taxas = calcular_taxas(taxa_mensal)
        
        # 1. Cálculos Base
        entrada_total = valor_vista * pct_entrada
        entrada_3x = entrada_total / 3
        valor_financiado_total = valor_vista - entrada_total
        
        # 2. Lógica Exata do seu Excel (47% do valor à vista para balões)
        if qtd_baloes > 0:
            vp_baloes = valor_vista * 0.47
            vp_parcelas = valor_vista - entrada_total - vp_baloes
        else:
            vp_baloes = 0
            vp_parcelas = valor_financiado_total

        # 3. Cálculo dos Fatores (Substitui o PGTO)
        datas_p = [ajustar_data_vencimento(data_base, "mensal", i, data_base.day) for i in range(1, qtd_parcelas + 1)]
        fator_vp_p = calcular_fator_vp(datas_p, data_base, taxas['diaria'])
        
        datas_b = [ajustar_data_vencimento(data_base, "anual", i, data_base.day) for i in range(1, qtd_baloes + 1)]
        fator_vp_b = calcular_fator_vp(datas_b, data_base, taxas['diaria'])

        # 4. Cálculo da Parcela e do Balão Financeiro Real
        valor_parcela = (vp_parcelas / fator_vp_p) if (qtd_parcelas > 0 and fator_vp_p > 0) else 0
        valor_balao = (vp_baloes / fator_vp_b) if (qtd_baloes > 0 and fator_vp_b > 0) else 0

        # Nomenclatura para exibir na tabela
        nome_exibicao = f"{qtd_parcelas}x"
        if qtd_baloes > 0: nome_exibicao += f" + {qtd_baloes} Balões"

        resultados.append({
            "Plano": nome_exibicao,
            "Taxa (a.m.)": f"{taxa_mensal:.3f}%".replace('.', ','),
            "Entrada (%)": f"{int(pct_entrada*100)}%",
            "Sinal (Entrada em 3x)": formatar_moeda(entrada_3x),
            "Valor da Parcela": formatar_moeda(valor_parcela),
            "Valor do Balão (Anual)": formatar_moeda(valor_balao) if qtd_baloes > 0 else "-",
            "Valor Financiado": formatar_moeda(valor_financiado_total)
        })
        
    return pd.DataFrame(resultados)

# --- Gerador do Cronograma Mensal e Exportações ---
def gerar_cronograma(valor_financiado, valor_parcela, valor_balao, qtd_parcelas, qtd_baloes, data_entrada, taxas):
    parcelas, baloes = [], []
    dia_vencimento = data_entrada.day

    for i in range(1, qtd_parcelas + 1):
        data_vencimento = ajustar_data_vencimento(data_entrada, "mensal", i, dia_vencimento)
        dias_comerciais = i * 30
        vp = calcular_valor_presente(valor_parcela, taxas['diaria'], dias_comerciais)
        parcelas.append({"Item": f"Parcela {i}", "Tipo": "Parcela", "Data_Vencimento": data_vencimento.strftime('%d/%m/%Y'), "Dias": dias_comerciais, "Valor": round(valor_parcela, 2), "Valor_Presente": round(vp, 2), "Desconto_Aplicado": round(valor_parcela - vp, 2)})

    for i in range(1, qtd_baloes + 1):
        data_vencimento = ajustar_data_vencimento(data_entrada, "anual", i, dia_vencimento)
        dias_comerciais = ((data_vencimento.year - data_entrada.year) * 12 + (data_vencimento.month - data_entrada.month)) * 30
        vp = calcular_valor_presente(valor_balao, taxas['diaria'], dias_comerciais)
        baloes.append({"Item": f"Balão {i}", "Tipo": "Balão", "Data_Vencimento": data_vencimento.strftime('%d/%m/%Y'), "Dias": dias_comerciais, "Valor": round(valor_balao, 2), "Valor_Presente": round(vp, 2), "Desconto_Aplicado": round(valor_balao - vp, 2)})

    cronograma = sorted(parcelas + baloes, key=lambda x: datetime.strptime(x['Data_Vencimento'], '%d/%m/%Y'))
    if cronograma:
        total_valor = round(sum(p['Valor'] for p in cronograma), 2)
        valor_presente_real = round(sum(p['Valor_Presente'] for p in cronograma), 2)
        cronograma.append({"Item": "TOTAL", "Tipo": "", "Data_Vencimento": "", "Dias": "", "Valor": total_valor, "Valor_Presente": valor_presente_real, "Desconto_Aplicado": round(total_valor - valor_presente_real, 2)})
    return cronograma

def gerar_pdf(cronograma, dados):
    try:
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Informações do Imóvel", ln=1, align='L'); pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Quadra: {dados.get('quadra', 'N/I')} | Lote: {dados.get('lote', 'N/I')} | Metragem: {dados.get('metragem', 'N/I')} m²", ln=1)
        pdf.ln(5); pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Simulação de Financiamento - Imobiliária Celeste", ln=1, align='L'); pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Plano Escolhido: {dados['nome_plano']}", ln=1)
        pdf.cell(200, 10, txt=f"Valor Total do Imóvel: {formatar_moeda(dados['valor_total'])}", ln=1)
        pdf.cell(200, 10, txt=f"Entrada Total: {formatar_moeda(dados['entrada'])}", ln=1)
        pdf.cell(200, 10, txt=f"Valor Financiado: {formatar_moeda(dados['valor_financiado'])}", ln=1)
        pdf.cell(200, 10, txt=f"Taxa Mensal Utilizada: {dados['taxa_mensal']:.3f}%", ln=1)
        pdf.ln(5); pdf.set_font("Arial", 'B', 11)
        
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
    except Exception as e: return BytesIO()

def gerar_excel(cronograma, dados):
    try:
        output = BytesIO()
        info_df = pd.DataFrame({'Campo': ['Quadra', 'Lote', 'Metragem', 'Valor Total do Imóvel', 'Entrada', 'Valor Financiado', 'Taxa Mensal Utilizada', 'Plano'], 'Valor': [dados.get('quadra', 'N/I'), dados.get('lote', 'N/I'), f"{dados.get('metragem', 'N/I')} m²", formatar_moeda(dados.get('valor_total', 0)), formatar_moeda(dados.get('entrada', 0)), formatar_moeda(dados.get('valor_financiado', 0)), f"{dados.get('taxa_mensal', 0):.3f}%", dados.get('nome_plano', '')]})
        df_cronograma_data = pd.DataFrame([p for p in cronograma if p['Item'] != 'TOTAL']).rename(columns={'Desconto_Aplicado': 'Juros'})
        total_row = next((p for p in cronograma if p['Item'] == 'TOTAL'), None)
        if total_row: total_row['Juros'] = total_row.get('Desconto_Aplicado')
        df_final = pd.concat([df_cronograma_data, pd.DataFrame([total_row])], ignore_index=True) if total_row else df_cronograma_data
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            info_df.to_excel(writer, sheet_name='Info Simulação', index=False)
            df_final[['Item', 'Tipo', 'Data_Vencimento', 'Valor', 'Valor_Presente', 'Juros']].to_excel(writer, sheet_name='Cronograma', index=False)
        output.seek(0); return output
    except Exception as e: return BytesIO()

# --- APP PRINCIPAL ---
def main():
    set_theme()
    st.write("\n")
    st.title("🏡 Simulador Imobiliária Celeste")
    st.markdown("Selecione a quadra e o lote abaixo para gerar automaticamente a tabela oficial com todas as opções de pagamento.")
    
    df_lotes = carregar_dados_lotes()
    st.markdown("---")
    
    # 1. Filtros
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

    # 2. Tela Automática (Se lote selecionado)
    if quadra_selecionada and lote_selecionado:
        linha = df_lotes[(df_lotes['Quadra'] == quadra_selecionada) & (df_lotes['Lote'] == lote_selecionado)].iloc[0]
        valor_vista_bd = float(linha['Valor a Vista'])
        metragem = float(linha['Área em Metro Quadrado'])
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader(f"📍 Resumo do Imóvel Selecionado: QD {quadra_selecionada} / LT {lote_selecionado}")
        m1, m2 = st.columns(2)
        m1.metric("📐 Área Total", f"{metragem:.2f} m²")
        m2.metric("💰 Valor à Vista", formatar_moeda(valor_vista_bd))
        
        st.markdown("<br>### 📋 Tabela Oficial de Planos (Pronto para Print)", unsafe_allow_html=True)
        st.caption("✅ **Automático:** Balões são calculados destinando 47% do Valor à Vista, e as parcelas com o saldo restante (regra oficial da imobiliária).")
        
        data_calculo = datetime.combine(data_base, datetime.min.time())
        df_planos = gerar_tabela_todos_planos(valor_vista_bd, data_calculo)
        
        st.dataframe(df_planos, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### 📄 Exportar Cronograma Detalhado (Mês a Mês)")
        st.markdown("Para gerar o cronograma de pagamentos e enviar ao cliente, escolha o plano que ele mais gostou:")
        
        plano_escolhido = st.selectbox("Selecione o Plano Definitivo:", PLANOS_DISPONIVEIS)
        
        if plano_escolhido:
            # Puxa os dados para calcular exatamente aquele plano e gerar o PDF
            qtd_p, qtd_b, pct_e, t_mensal = extrair_dados_plano(plano_escolhido)
            taxas_plano = calcular_taxas(t_mensal)
            entrada_plano = valor_vista_bd * pct_e
            valor_financiado_plano = valor_vista_bd - entrada_plano
            
            if qtd_b > 0:
                vp_b = valor_vista_bd * 0.47
                vp_p = valor_vista_bd - entrada_plano - vp_b
            else:
                vp_b = 0
                vp_p = valor_financiado_plano
                
            datas_p = [ajustar_data_vencimento(data_calculo, "mensal", i, data_calculo.day) for i in range(1, qtd_p + 1)]
            datas_b = [ajustar_data_vencimento(data_calculo, "anual", i, data_calculo.day) for i in range(1, qtd_b + 1)]
            
            f_vp_p = calcular_fator_vp(datas_p, data_calculo, taxas_plano['diaria'])
            f_vp_b = calcular_fator_vp(datas_b, data_calculo, taxas_plano['diaria'])
            
            valor_parcela_final = (vp_p / f_vp_p) if (qtd_p > 0 and f_vp_p > 0) else 0
            valor_balao_final = (vp_b / f_vp_b) if (qtd_b > 0 and f_vp_b > 0) else 0
            
            cronograma = gerar_cronograma(valor_financiado_plano, valor_parcela_final, valor_balao_final, qtd_p, qtd_b, data_calculo, taxas_plano)
            
            export_data = {
                'valor_total': valor_vista_bd, 'entrada': entrada_plano, 'taxa_mensal': t_mensal, 
                'valor_financiado': valor_financiado_plano, 'quadra': quadra_selecionada, 
                'lote': lote_selecionado, 'metragem': metragem, 'nome_plano': plano_escolhido
            }
            
            c1_exp, c2_exp = st.columns(2)
            pdf_file = gerar_pdf(cronograma, export_data)
            c1_exp.download_button("📥 Exportar PDF Detalhado", pdf_file, "simulacao_celeste.pdf", "application/pdf")
            
            excel_file = gerar_excel(cronograma, export_data)
            c2_exp.download_button("📥 Exportar Excel Detalhado", excel_file, "simulacao_celeste.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == '__main__':
    main()
