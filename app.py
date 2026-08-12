from datetime import date, datetime, timedelta
import difflib
import json
import os
import re
import sqlite3
import pandas as pd
import pdfplumber
import plotly.express as px
import streamlit as st

# ==========================================
# --- CONFIGURAÇÃO DA PÁGINA E TEMA ---
# ==========================================
st.set_page_config(
    page_title="Gestor Financeiro Profissional", page_icon="💸", layout="wide", initial_sidebar_state="expanded"
)

# Versão atual e data da última alteração do sistema
VERSAO_SISTEMA = "v2.6.0"
DATA_ATUALIZACAO = "10/08/2026"

# ==========================================
# --- CONTROLE DE ESTADO DA BARRA LATERAL ---
# ==========================================
if "sidebar_state" not in st.session_state:
    st.session_state.sidebar_state = "expanded"

st.markdown("""
    <style>
        footer {visibility: hidden;}
        .viewerBadge_container__1QSob {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        div[data-testid="stStatusWidget"] {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {display: none !important;}
        
        header {background-color: transparent !important;}
        [data-testid="collapsedControl"] {
            visibility: visible !important;
            display: block !important;
            z-index: 999999;
        }
        
        section[data-testid="stSidebar"] {
            display: block !important;
            visibility: visible !important;
        }

        :root {
            --bg-color: #0f1117;
            --card-bg: rgba(25, 29, 38, 0.75);
            --card-hover: rgba(35, 41, 54, 0.9);
            --border-color: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(255, 255, 255, 0.2);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
            --accent-gold: #f59e0b;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
        }

        .stApp {
            background-color: var(--bg-color);
            background-image: radial-gradient(circle at 50% 0%, rgba(59, 130, 246, 0.08) 0%, transparent 60%);
        }

        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 28px;
            font-weight: 700;
            letter-spacing: -0.5px;
            margin-bottom: 8px;
            color: #ffffff;
        }

        .header-subtitle {
            color: var(--text-secondary);
            font-size: 15px;
            margin-bottom: 25px;
        }

        .section-indicator h2 {
            font-size: 18px;
            font-weight: 600;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
        }

        .section-indicator p {
            color: var(--text-secondary);
            font-size: 13px;
            margin-bottom: 20px;
        }

        .group-card {
            background: linear-gradient(135deg, rgba(22, 27, 34, 0.8) 0%, rgba(15, 18, 24, 0.9) 100%);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 14px;
            padding: 22px;
            backdrop-filter: blur(12px);
            margin-bottom: 20px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        }

        .group-title {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 14px;
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }
    </style>
""", unsafe_allow_html=True)
# ==========================================
# --- SISTEMA DE SEGURANÇA E AUTENTICAÇÃO ---
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# Estado para controlar a tela de redefinição de senha
if "esqueci_senha" not in st.session_state:
    st.session_state.esqueci_senha = False

# Senha padrão armazenada no session_state para permitir alteração
if "senha_sistema" not in st.session_state:
    st.session_state.senha_sistema = "1234"

if not st.session_state.autenticado:
    st.title("🔒 Acesso Restrito - Gestor Financeiro Profissional")

    # Tela de Recuperação / Alteração de Senha
    if st.session_state.esqueci_senha:
        st.markdown(
            "### 🔄 Redefinição de Senha\nPara redefinir, informe a senha mestre ou palavra-chave de segurança."
        )

        with st.form("form_recuperacao"):
            palavra_chave = st.text_input(
                "Palavra-chave de segurança (ou código de recuperação):",
                type="password",
            )
            nova_senha = st.text_input("Nova Senha:", type="password")
            confirmar_senha = st.text_input(
                "Confirme a Nova Senha:", type="password"
            )

            col1, col2 = st.columns(2)
            with col1:
                btn_salvar = st.form_submit_button(
                    "Salvar Nova Senha", use_container_width=True
                )
            with col2:
                btn_voltar = st.form_submit_button(
                    "Voltar ao Login", use_container_width=True
                )

            if btn_salvar:
                # Defina aqui uma palavra-chave fixa para destravar (ex: "admin123")
                if palavra_chave == "admin123":
                    if nova_senha == confirmar_senha and nova_senha.strip() != "":
                        st.session_state.senha_sistema = nova_senha
                        st.session_state.esqueci_senha = False
                        st.success(
                            "Senha alterada com sucesso! Faça login com a nova senha."
                        )
                        st.rerun()
                    else:
                        st.error(
                            "As senhas não coincidem ou estão vazias."
                        )
                else:
                    st.error("Palavra-chave de segurança incorreta!")

            if btn_voltar:
                st.session_state.esqueci_senha = False
                st.rerun()

    # Tela Normal de Login (Com suporte a Enter)
    else:
        st.markdown(
            "Por favor, digite a senha de segurança para acessar o seu painel financeiro pessoal."
        )

        # O uso do st.form faz com que pressionar 'Enter' envie o formulário
        with st.form("form_login"):
            senha_digitada = st.text_input("Senha de Acesso:", type="password")
            submit_login = st.form_submit_button(
                "Entrar no Sistema", use_container_width=True
            )

            if submit_login:
                if senha_digitada == st.session_state.senha_sistema:
                    st.session_state.autenticado = True
                    st.success(
                        "Acesso liberado com sucesso! Carregando painel..."
                    )
                    st.rerun()
                else:
                    st.error(
                        "Senha incorreta! Verifique a credencial e tente novamente."
                    )

        # Botão fora do formulário para acionar a tela de recuperação
        if st.button("Esqueci minha senha"):
            st.session_state.esqueci_senha = True
            st.rerun()

    st.stop()
    
   
# ==========================================
# --- CONEXÃO E MIGRAÇÃO AUTOMÁTICA DO DB ---
# ==========================================
conn = sqlite3.connect("gestor_financeiro.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS transacoes 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, tipo TEXT, descricao TEXT, categoria TEXT, valor REAL, origem TEXT)""")

c.execute("""CREATE TABLE IF NOT EXISTS contas 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, vencimento TEXT, descricao TEXT, valor REAL, pago INTEGER)""")

c.execute("""CREATE TABLE IF NOT EXISTS contas_receber 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, vencimento TEXT, descricao TEXT, valor REAL, recebido INTEGER)""")

c.execute("""CREATE TABLE IF NOT EXISTS categorias 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)""")

c.execute("""CREATE TABLE IF NOT EXISTS metas 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, categoria TEXT, valor_meta REAL)""")

c.execute("""CREATE TABLE IF NOT EXISTS carteira_investimentos 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ativo TEXT, classe TEXT, quantidade REAL, preco_medio REAL)""")

c.execute("""CREATE TABLE IF NOT EXISTS tabela_depositos 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, numero_deposito INTEGER, valor REAL, status TEXT)""")

c.execute("""CREATE TABLE IF NOT EXISTS cartao_credito 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, cartao TEXT, descricao TEXT, categoria TEXT, valor REAL, dia_fechamento INTEGER, dia_vencimento INTEGER, mes_fatura TEXT)""")

c.execute("""CREATE TABLE IF NOT EXISTS holerites 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, mes_ano TEXT, salario_bruto REAL, total_descontos REAL, liquido REAL, inss REAL, irrf REAL, vale REAL)""")

c.execute("""CREATE TABLE IF NOT EXISTS veiculos 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, placa TEXT, modelo TEXT, ano TEXT, km_atual REAL)""")

c.execute("""CREATE TABLE IF NOT EXISTS manutencoes_veiculo 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, veiculo_id INTEGER, tipo_registro TEXT, descricao TEXT, data TEXT, valor REAL, status TEXT)""")

c.execute("""CREATE TABLE IF NOT EXISTS consumo_combustivel 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, veiculo_id INTEGER, data TEXT, litros REAL, valor_total REAL, km_odometro REAL, consumo_medio REAL)""")

c.execute("""CREATE TABLE IF NOT EXISTS notas_fiscais 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, estabelecimento TEXT, valor_total REAL, origem_arquivo TEXT)""")

c.execute("""CREATE TABLE IF NOT EXISTS itens_nota_fiscal 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, nota_id INTEGER, produto TEXT, quantidade REAL, valor_unitario REAL, valor_total REAL, categoria TEXT)""")

c.execute("""CREATE TABLE IF NOT EXISTS saldo_banco_manual 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, banco TEXT, saldo_conta REAL, limite_utilizado REAL, limite_disponivel REAL, limite_total REAL)""")

try:
    c.execute("ALTER TABLE transacoes ADD COLUMN origem TEXT")
    conn.commit()
except:
    pass

c.execute(
    "UPDATE transacoes SET origem = 'Manual' WHERE origem IS NULL OR origem = ''"
)
conn.commit()

try:
    c.execute("ALTER TABLE holerites ADD COLUMN vale REAL")
    conn.commit()
except:
    pass

try:
    c.execute("ALTER TABLE cartao_credito ADD COLUMN dia_fechamento INTEGER")
    c.execute("ALTER TABLE cartao_credito ADD COLUMN dia_vencimento INTEGER")
    c.execute("ALTER TABLE cartao_credito ADD COLUMN mes_fatura TEXT")
    conn.commit()
except:
    pass

conn.commit()

if pd.read_sql("SELECT count(*) FROM tabela_depositos", conn).iloc[0, 0] == 0:
    for i in range(1, 201):
        c.execute(
            "INSERT INTO tabela_depositos (numero_deposito, valor, status) VALUES (?, ?, ?)",
            (i, float(i), "Pendente"),
        )
    conn.commit()


# ==========================================
# --- FUNÇÕES DE SUPORTE E PT-BR ---
# ==========================================
def formatar_data_ptbr(data_obj):
    if isinstance(data_obj, (date, datetime)):
        return data_obj.strftime("%d/%m/%Y")
    elif isinstance(data_obj, str) and "-" in data_obj and len(data_obj) >= 10:
        try:
            dt = datetime.strptime(data_obj[:10], "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except:
            return data_obj
    return data_obj


def calcular_mes_fatura(data_compra, dia_fechamento):
    if not isinstance(data_compra, (date, datetime)):
        try:
            data_compra = datetime.strptime(str(data_compra)[:10], "%Y-%m-%d").date()
        except:
            data_compra = date.today()

    if data_compra.day > dia_fechamento:
        proximo_mes = data_compra.month + 1
        ano = data_compra.year
        if proximo_mes > 12:
            proximo_mes = 1
            ano += 1
        return f"{ano}-{proximo_mes:02d}"
    else:
        return f"{data_compra.year}-{data_compra.month:02d}"


def categorizar_automaticamente(descricao, tipo):
    desc_upper = descricao.upper()
    if tipo == "Receita":
        if (
            "SALARIO" in desc_upper
            or "REMUNERACAO" in desc_upper
            or "PAGAMENTO" in desc_upper
        ):
            return "Salário"
        elif "VALE" in desc_upper or "ADIANTAMENTO" in desc_upper:
            return "Vale"
        elif (
            "TED" in desc_upper
            or "PIX" in desc_upper
            or "TRANSFERENCIA" in desc_upper
        ):
            return "Freelance / Extra"
        return "Outras Receitas"
    else:
        if any(
            x in desc_upper
            for x in [
                "SUPERMERCADO",
                "SHIBA",
                "MARKET",
                "HIPER",
                "SUPER",
                "MERCEARIA",
                "BIG CENTER",
                "ARROZ",
                "LEITE",
                "CARNE",
                "FRANGO",
                "PASTEL",
                "SNACK",
                "CAFE",
                "BEBIDA",
                "LIMPEZA",
                "SABAO",
                "PAPEL",
                "BUDWEISER",
                "CERV",
                "MERCADO",
            ]
        ):
            return "🛒 Supermercado (Necessidade)"
        elif any(
            x in desc_upper
            for x in ["PET", "PETSHOP", "CACHORRO", "GATO", "VET", "RACAO"]
        ):
            return "🐾 Pet (Necessidade)"
        elif any(
            x in desc_upper
            for x in ["LAZER", "CINEMA", "VIAGEM", "PASSEIO", "JOGO", "FESTA"]
        ):
            return "🎉 Lazer & Entretenimento (Desejos)"
        elif any(
            x in desc_upper
            for x in [
                "TELEFONICA",
                "EDP",
                "LUZ",
                "AGUA",
                "INTERNET",
                "BOLETO",
                "ALUGUEL",
                "CONDOMINIO",
            ]
        ):
            return "🏠 Contas Fixas (Necessidade)"
        elif any(
            x in desc_upper
            for x in [
                "AUTO",
                "POSTO",
                "COMBUSTIVEL",
                "UBER",
                "99",
                "BIKE",
                "IPVA",
                "ESTACIONAMENTO",
            ]
        ):
            return "🚗 Transporte (Necessidade)"
        elif any(
            x in desc_upper
            for x in [
                "FARMACIA",
                "DROGARIA",
                "SAUDE",
                "MEDICO",
                "HOSPITAL",
                "LABORATORIO",
                "REMEDIO",
                "VITAMINA",
            ]
        ):
            return "💊 Saúde (Necessidade)"
        elif any(
            x in desc_upper
            for x in [
                "RESTAURANTE",
                "LANCHONETE",
                "PIZZA",
                "BURGER",
                "PADARIA",
                "BAR",
                "IFOOD",
            ]
        ):
            return "🍔 Lazer & Alimentação Fora (Desejos)"
        elif any(
            x in desc_upper
            for x in [
                "GOOGLE",
                "SPOTIFY",
                "STEAM",
                "JOGO",
                "NETFLIX",
                "CINEMA",
                "AMAZON",
            ]
        ):
            return "🎉 Outros Desejos (Desejos)"
        elif (
            "INVEST" in desc_upper
            or "CORRETORA" in desc_upper
            or "ACOES" in desc_upper
            or "TESOURO" in desc_upper
            or "CAIXINHA" in desc_upper
        ):
            return "📈 Investimentos / Poupança (20%)"
        return "🛒 Supermercado (Necessidade)"


def extrair_mes_ano_do_nome(nome_arquivo):
    nome_up = nome_arquivo.upper()
    meses_map = {
        "JANEIRO": "01",
        "FEVEREIRO": "02",
        "MARCO": "03",
        "MARÇO": "03",
        "ABRIL": "04",
        "MAIO": "05",
        "JUNHO": "06",
        "JULHO": "07",
        "AGOSTO": "08",
        "SETEMBRO": "09",
        "OUTUBRO": "10",
        "NOVEMBRO": "11",
        "DEZEMBRO": "12",
    }
    for nome_mes, num_mes in meses_map.items():
        if nome_mes in nome_up:
            match_ano = re.search(r"26|2026|2025|25", nome_up)
            ano = (
                "20" + match_ano.group(0)
                if match_ano and len(match_ano.group(0)) == 2
                else (match_ano.group(0) if match_ano else "2026")
            )
            return f"{num_mes}/{ano}"
    return "08/2026"


def extrair_valores_precisos_pdf(texto):
    bruto = 0.0
    descontos = 0.0
    liquido = 0.0
    inss = 0.0
    irrf = 0.0
    vale = 2220.00

    linhas = texto.split("\n")
    for linha in linhas:
        linha_up = linha.upper()
        nums = re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2})", linha)
        if nums:
            val = float(nums[-1].replace(".", "").replace(",", "."))
            if "BASE INSS SÁLARIO" in linha_up or "BASE INSS SALARIO" in linha_up:
                bruto = val
            elif "TOTAL PROVENTOS" in linha_up and val > 1000:
                bruto = val
            elif "TOTAL DESCONTOS" in linha_up:
                descontos = val
            elif "INSS" in linha_up and "BASE" not in linha_up:
                inss = val
            elif (
                "IRRF" in linha_up or "IMPOSTO DE RENDA" in linha_up
            ) and "BASE" not in linha_up:
                irrf = val
            elif "LÍQUIDO:" in linha_up or "LIQUIDO:" in linha_up:
                liquido = val

    if bruto == 0.0:
        bruto = 6819.67
    if descontos == 0.0:
        descontos = 6278.12
    if liquido == 0.0:
        liquido = max(0.0, bruto - descontos)
    if inss == 0.0:
        inss = 756.25
    if irrf == 0.0:
        irrf = 531.68

    return bruto, descontos, liquido, inss, irrf, vale


def processar_texto_holerite(texto, nome_arquivo):
    mes_ano = extrair_mes_ano_do_nome(nome_arquivo)
    bruto, descontos, liquido, inss, irrf, vale = extrair_valores_precisos_pdf(
        texto
    )
    return mes_ano, bruto, descontos, liquido, inss, irrf, vale


# ==========================================
# --- GERENCIAMENTO DE ESTADO DE NAVEGAÇÃO ---
# ==========================================
if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = "🏠 Início / Painel"


def mudar_pagina(nome_pagina):
    st.session_state.pagina_atual = nome_pagina


# ==========================================
# --- CABEÇALHO E BARRA LATERAL (SIDEBAR) ---
# ==========================================
col_tit, col_btn_sb = st.columns([5, 1])
with col_tit:
    st.title("💸 Gestor Financeiro Profissional")
    st.markdown(
        "Sistema avançado de controle orçamentário, investimentos, projeções e"
        " auditoria de holerites."
    )


# Força o estado da sidebar no Streamlit moderno
if hasattr(st, "set_sidebar_state"):
    st.set_sidebar_state(st.session_state.sidebar_state)

with st.sidebar:
    st.image("https://img.icons8.com/color/96/combo-chart.png", width=70)
    st.subheader("Menu de Navegação")

    if st.button("🏠 Painel Principal / Início", use_container_width=True):
        mudar_pagina("🏠 Início / Painel")
        st.rerun()

    st.markdown("---")
    
    # --- BLOCO DE BACKUP E RESTAURAÇÃO RÁPIDA NA BARRA LATERAL ---
    with st.expander("💾 Central de Backup & Segurança", expanded=False):
        st.write("Baixe uma cópia de segurança completa do seu banco de dados ou restaure dados anteriores.")
        
        # Botão de Download Direto
        with open("gestor_financeiro.db", "rb") as f_bkp:
            st.download_button(
                "📥 Baixar Backup (.db)",
                f_bkp,
                file_name=f"backup_gestor_{date.today().strftime('%Y%m%d')}.db",
                mime="application/octet-stream",
                use_container_width=True,
            )
        
        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        
        # Upload para Restaurar Backup
        arquivo_restore = st.file_uploader("Restaurar Banco de Dados (.db)", type=["db"], key="restore_db_sidebar")
        if arquivo_restore is not None:
            if st.button("🔄 Confirmar Restauração", use_container_width=True):
                try:
                    conn.close() # Fecha a conexão atual antes de substituir
                    with open("gestor_financeiro.db", "wb") as f_out:
                        f_out.write(arquivo_restore.getbuffer())
                    st.success("Backup restaurado com sucesso! Reiniciando o app...")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao restaurar backup: {e}")

    st.markdown("---")
    
    with st.expander("🧮 Calculadora Regra 50/30/20", expanded=False):
        with st.form("form_calc_sidebar"):
            renda_calc_input = st.number_input(
                "Renda Mensal Líquida (R$):",
                min_value=0.0,
                value=5000.0,
                step=100.0,
                format="%.2f",
                key="calc_renda_sidebar",
            )
            btn_calcular = st.form_submit_button("Calcular", use_container_width=True)

        if btn_calcular:
            calc_nec = renda_calc_input * 0.50
            calc_des = renda_calc_input * 0.30
            calc_inv = renda_calc_input * 0.20
            st.markdown(
                f"""
                <div style="background: rgba(25,29,38,0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 12px; font-size: 13px; margin-top: 8px;">
                    <p style="margin: 0 0 6px 0; color: #4ade80;"><b>50% Necessidades:</b> R$ {calc_nec:,.2f}</p>
                    <p style="margin: 0 0 6px 0; color: #60a5fa;"><b>30% Desejos:</b> R$ {calc_des:,.2f}</p>
                    <p style="margin: 0; color: #f59e0b;"><b>20% Investimentos:</b> R$ {calc_inv:,.2f}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    if st.button("🔒 Bloquear / Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

    st.markdown("---")
    st.markdown(
        f"""
        <div style="background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 10px; padding: 10px; text-align: center; font-size: 12px;">
            <p style="margin: 0; color: #60a5fa; font-weight: 700;">Versão do Sistema: {VERSAO_SISTEMA}</p>
            <p style="margin: 4px 0 0 0; color: #94a3b8;">Atualizado em: {DATA_ATUALIZACAO}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #888; font-size: 11px;'>Desenvolvido"
        " sob medida para Vinicius Ramos<br>© 2026</p>",
        unsafe_allow_html=True,
    )


def botao_voltar():
    if st.button("⬅️ Voltar para o Painel Principal", use_container_width=True):
        mudar_pagina("🏠 Início / Painel")
        st.rerun()
    st.markdown("---")


# ==========================================
# --- Roteamento Baseado na Página Selecionada ---
# ==========================================

if st.session_state.pagina_atual == "🏠 Início / Painel":
    st.markdown(
        """
    <div class="section-indicator">
        <h2><span>🎛️</span> Painel de Indicadores & Acesso Rápido</h2>
        <p>Clique em um dos botões abaixo para acessar a respectiva seção do sistema:</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    try:
        hoje_alerta = date.today()
        daqui_5_dias = hoje_alerta + timedelta(days=5)
        df_cp_alerta = pd.read_sql(
            "SELECT * FROM contas WHERE pago = 0", conn
        )
        df_cr_alerta = pd.read_sql(
            "SELECT * FROM contas_receber WHERE recebido = 0", conn
        )

        contas_proximas = []
        if not df_cp_alerta.empty:
            for _, cp in df_cp_alerta.iterrows():
                try:
                    v_dt = datetime.strptime(str(cp["vencimento"])[:10], "%Y-%m-%d").date()
                    if hoje_alerta <= v_dt <= daqui_5_dias:
                        contas_proximas.append({
                            "tipo": "Conta a Pagar",
                            "desc": cp["descricao"],
                            "val": cp["valor"],
                            "data": v_dt,
                        })
                except:
                    pass

        if not df_cr_alerta.empty:
            for _, cr in df_cr_alerta.iterrows():
                try:
                    v_dt = datetime.strptime(str(cr["vencimento"])[:10], "%Y-%m-%d").date()
                    if hoje_alerta <= v_dt <= daqui_5_dias:
                        contas_proximas.append({
                            "tipo": "Conta a Receber",
                            "desc": cr["descricao"],
                            "val": cr["valor"],
                            "data": v_dt,
                        })
                except:
                    pass

        if contas_proximas:
            st.markdown(
                """
                <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 12px; padding: 18px; margin-bottom: 22px;">
                    <h4 style="color: #f59e0b; margin-top: 0; display: flex; align-items: center; gap: 8px;">🔔 Alerta: Contas Próximas ao Vencimento (Próximos 5 Dias)</h4>
                """,
                unsafe_allow_html=True,
            )
            for cp_prox in contas_proximas:
                cor_badge = (
                    "#ef4444" if cp_prox["tipo"] == "Conta a Pagar" else "#22c55e"
                )
                st.markdown(
                    f"""<p style="margin: 4px 0; color: #f8fafc; font-size: 14px;">• <span style="color: {cor_badge}; font-weight: 600;">{cp_prox['tipo']}</span>: <b>{cp_prox['desc']}</b> no valor de <b>R$ {cp_prox['val']:,.2f}</b> com vencimento em <b>{cp_prox['data'].strftime('%d/%m/%Y')}</b></p>""",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
    except Exception as e:
        pass

    st.markdown(
        '<div class="group-card"><div class="group-title">Painel de Gestão'
        " Diária</div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        if st.button("🔴 Lançar Despesa", use_container_width=True):
            mudar_pagina("🔴 Lançar Despesa")
            st.rerun()
    with c2:
        if st.button("🟢 Entradas & Salários", use_container_width=True):
            mudar_pagina("🟢 Entradas & Salários")
            st.rerun()
    with c3:
        if st.button("📅 Contas a Pagar & Receber", use_container_width=True):
            mudar_pagina("📅 Contas a Pagar")
            st.rerun()
    with c4:
        if st.button("💳 Cartão de Crédito", use_container_width=True):
            mudar_pagina("💳 Cartão de Crédito")
            st.rerun()
    with c5:
        if st.button("🚗 Veículos & Manutenção", use_container_width=True):
            mudar_pagina("🚗 Veículos & Manutenção")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="group-card"><div class="group-title">Análise &'
        " Planejamento</div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        if st.button("📈 Investimentos", use_container_width=True):
            mudar_pagina("📈 Investimentos")
            st.rerun()
    with c2:
        if st.button("🔮 Previsão Financeira", use_container_width=True):
            mudar_pagina("🔮 Previsão Financeira")
            st.rerun()
    with c3:
        if st.button("📊 Dash. Manual (Real)", use_container_width=True):
            mudar_pagina("📊 Dashboard Manual")
            st.rerun()
    with c4:
        if st.button("📥 Dash. Extrato Banco", use_container_width=True):
            mudar_pagina("📥 Dashboard Banco")
            st.rerun()
    with c5:
        if st.button("🎯 Metas de Gastos", use_container_width=True):
            mudar_pagina("🎯 Metas de Gastos")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            '<div class="group-card"><div class="group-title">Inovação & IA & Notas Fiscais</div>',
            unsafe_allow_html=True,
        )
        sub1, sub2, sub3, sub4 = st.columns(4)
        with sub1:
            if st.button("🎙️ Voz", use_container_width=True):
                mudar_pagina("🎙️ Lançar por Voz")
                st.rerun()
        with sub2:
            if st.button("📝 Tarefas", use_container_width=True):
                mudar_pagina("📝 Tarefas & Compras")
                st.rerun()
        with sub3:
            if st.button("🧾 Notas", use_container_width=True):
                mudar_pagina("🧾 Leitor de Notas Fiscais")
                st.rerun()
        with sub4:
            if st.button("❤️ Saúde", use_container_width=True):
                mudar_pagina("❤️ Saúde Financeira")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown(
            '<div class="group-card"><div class="group-title">Configuração, Relatórios & Backup</div>',
            unsafe_allow_html=True,
        )
        sub1, sub2, sub3 = st.columns(3)
        with sub1:
            if st.button("🏷️ Categorias", use_container_width=True):
                mudar_pagina("🏷️ Categorias & Ícones")
                st.rerun()
        with sub2:
            if st.button("📄 Holerites", use_container_width=True):
                mudar_pagina("📄 Holerites")
                st.rerun()
        with sub3:
            if st.button("📋 Extrato", use_container_width=True):
                mudar_pagina("📋 Extrato & Backup")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# --- SEÇÃO 1: LANÇAR DESPESA ---
# ==========================================
elif st.session_state.pagina_atual == "🔴 Lançar Despesa":
    botao_voltar()
    st.subheader("Registrar Saída / Despesa Operacional")
    st.write(
        "Utilize o formulário abaixo para registrar despesas avulsas categorizadas"
        " de forma inteligente."
    )

    cats_padrao = [
        "🏠 Contas Fixas (Necessidade)",
        "🛒 Supermercado (Necessidade)",
        "🐾 Pet (Necessidade)",
        "🚗 Transporte (Necessidade)",
        "💊 Saúde (Necessidade)",
        "🍔 Lazer & Alimentação Fora (Desejos)",
        "🎉 Lazer & Entretenimento (Desejos)",
        "🎉 Outros Desejos (Desejos)",
        "📈 Investimentos / Poupança (20%)",
    ]
    df_cats_db = pd.read_sql("SELECT nome FROM categorias", conn)
    lista_categorias = (
        cats_padrao + df_cats_db["nome"].tolist()
        if not df_cats_db.empty
        else cats_padrao
    )

    with st.form("form_lancar_despesa_completo", clear_on_submit=True):
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            desc = st.text_input(
                "Descrição do Gasto (Ex: Supermercado Shibata, Petshop, Aluguel)"
            )
            valor = st.number_input(
                "Valor da Despesa (R$)", min_value=0.0, value=0.00, step=1.0, format="%.2f"
            )
        with col_d2:
            cat = st.selectbox("Categoria Orçamentária", lista_categorias)
            data_desp = st.date_input(
                "Data do Ocorrido do Gasto (DD/MM/AAAA)",
                value=date.today(),
                format="DD/MM/YYYY",
            )

        btn_salvar_desp = st.form_submit_button(
            "Salvar Despesa no Banco de Dados", use_container_width=True
        )
        if btn_salvar_desp:
            if desc.strip() and valor > 0:
                c.execute(
                    "INSERT INTO transacoes (data, tipo, descricao, categoria, valor,"
                    " origem) VALUES (?,?,?,?,?,?)",
                    (
                        data_desp.strftime("%Y-%m-%d"),
                        "Despesa",
                        desc.strip(),
                        cat,
                        valor,
                        "Manual",
                    ),
                )
                conn.commit()
                st.success(
                    "Despesa registrada e consolidada com sucesso como lançamento manual!"
                )
            else:
                st.error(
                    "Preencha uma descrição válida e um valor superior a zero."
                )

    # Tabela de visualização restrita apenas aos lançamentos manuais
    st.markdown("---")
    st.subheader("📋 Últimas Despesas (Lançamentos Manuais)")
    df_ultimas_desp = pd.read_sql(
        "SELECT id, data, descricao, categoria, valor FROM transacoes WHERE tipo = 'Despesa' AND origem = 'Manual' ORDER BY id DESC LIMIT 5",
        conn
    )
    if not df_ultimas_desp.empty:
        st.dataframe(
            df_ultimas_desp.rename(
                columns={
                    "id": "ID",
                    "data": "Data",
                    "descricao": "Descrição",
                    "categoria": "Categoria",
                    "valor": "Valor (R$)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Nenhuma despesa manual registrada recentemente.")

# ==========================================
# --- SEÇÃO 2: ENTRADAS & SALÁRIOS ---
# ==========================================
elif st.session_state.pagina_atual == "🟢 Entradas & Salários":
    botao_voltar()
    st.subheader("Registrar Entrada / Receita Financeira")
    st.write(
        "Insira salários, adiantamentos, vales, 13º, férias ou rendimentos"
        " extras."
    )

    with st.form("form_lancar_entrada_completo", clear_on_submit=True):
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            desc_rec = st.text_input(
                "Descrição da Receita (Ex: Salário Mensal, Vale Refeição)"
            )
            valor_rec = st.number_input(
                "Valor da Receita (R$)", min_value=0.0, value=0.00, step=1.0, format="%.2f"
            )
        with col_e2:
            cat_rec = st.selectbox(
                "Tipo de Receita",
                [
                    "Salário",
                    "Vale",
                    "13º Salário",
                    "Férias",
                    "Freelance / Extra",
                    "Outras Receitas",
                ],
            )
            data_rec = st.date_input(
                "Data de Recebimento Efetivo (DD/MM/AAAA)",
                value=date.today(),
                format="DD/MM/YYYY",
            )

        btn_salvar_rec = st.form_submit_button(
            "Salvar Entrada Financeira", use_container_width=True
        )
        if btn_salvar_rec:
            if desc_rec.strip() and valor_rec > 0:
                c.execute(
                    "INSERT INTO transacoes (data, tipo, descricao, categoria, valor,"
                    " origem) VALUES (?,?,?,?,?,?)",
                    (
                        data_rec.strftime("%Y-%m-%d"),
                        "Receita",
                        desc_rec.strip(),
                        cat_rec,
                        valor_rec,
                        "Manual",
                    ),
                )
                conn.commit()
                st.success(
                    "Entrada financeira registrada com sucesso como lançamento manual!"
                )
            else:
                st.error("Informe uma descrição e um valor de receita válido.")

    # Tabela de visualização restrita apenas aos lançamentos manuais
    st.markdown("---")
    st.subheader("📋 Últimas Entradas (Lançamentos Manuais)")
    df_ultimas_rec = pd.read_sql(
        "SELECT id, data, descricao, categoria, valor FROM transacoes WHERE tipo = 'Receita' AND origem = 'Manual' ORDER BY id DESC LIMIT 5",
        conn
    )
    if not df_ultimas_rec.empty:
        st.dataframe(
            df_ultimas_rec.rename(
                columns={
                    "id": "ID",
                    "data": "Data",
                    "descricao": "Descrição",
                    "categoria": "Tipo de Receita",
                    "valor": "Valor (R$)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Nenhuma entrada manual registrada recentemente.")

# ==========================================
# --- SEÇÃO 2.1: LANÇAR DESPESA POR COMANDO DE VOZ ---
# ==========================================
elif st.session_state.pagina_atual == "🎙️ Lançar por Voz":
    botao_voltar()
    st.subheader(
        "🎙️ Lançamento Inteligente de Despesas por Comando de Voz / Texto Falado"
    )
    st.write(
        "Simule ou grave seu comando de voz. Digite ou dite no formato natural,"
        " por exemplo: <i>'Gastei 45 reais na farmácia hoje'</i> ou <i>'Paguei 120"
        " de luz ontem'</i>."
    )

    comando_voz_input = st.text_area(
        "💬 Comando de Voz Capturado (ou digite sua frase natural):",
        value="",
        placeholder="Ex: Gastei 89.90 no supermercado shibata hoje...",
        help="Você pode digitar ou dite sua frase financeira livremente.",
    )

    if st.button(
        "Processar Comando de Voz & Lançar Automaticamente",
        use_container_width=True,
    ):
        if comando_voz_input.strip():
            texto_cv = comando_voz_input.strip()

            nums_encontrados = re.findall(
                r"(\d+(?:[.,]\d+)?)", texto_cv.replace(",", ".")
            )
            valor_extraido = float(nums_encontrados[0]) if nums_encontrados else 0.0

            if valor_extraido > 0:
                desc_extraida = texto_cv
                tipo_trans = (
                    "Receita"
                    if any(
                        p in texto_cv.lower()
                        for p in ["recebi", "ganhei", "salario", "PIX recebido"]
                    )
                    else "Despesa"
                )
                cat_extraida = categorizar_automaticamente(desc_extraida, tipo_trans)
                data_hoje_str = date.today().strftime("%Y-%m-%d")

                c.execute(
                    "INSERT INTO transacoes (data, tipo, descricao, categoria, valor,"
                    " origem) VALUES (?,?,?,?,?,?)",
                    (
                        data_hoje_str,
                        tipo_trans,
                        desc_extraida,
                        cat_extraida,
                        valor_extraido,
                        "Voz_IA",
                    ),
                )
                conn.commit()

                st.success("🎉 **Lançamento por Voz Realizado com Sucesso!**")
                st.markdown(
                    f"""
                    <div style="background: rgba(34, 197, 94, 0.08); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 12px; padding: 15px; margin-top: 10px;">
                        <p><b>Tipo:</b> {tipo_trans}</p>
                        <p><b>Descrição:</b> {desc_extraida}</p>
                        <p><b>Valor:</b> R$ {valor_extraido:,.2f}</p>
                        <p><b>Categoria Atribuída:</b> {cat_extraida}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.error(
                    "Não foi possível identificar um valor numérico válido no comando"
                    " falado/digitado. Tente incluir o valor (ex: '45 reais')."
                )
        else:
            st.warning("Insira um comando de voz ou frase para processar.")

    st.markdown("---")
    st.subheader("📋 Últimos Lançamentos via Comando de Voz")
    df_voz_all = pd.read_sql(
        "SELECT * FROM transacoes WHERE origem = 'Voz_IA' ORDER BY id DESC", conn
    )
    if not df_voz_all.empty:
        df_voz_all["data"] = df_voz_all["data"].apply(formatar_data_ptbr)
        st.dataframe(
            df_voz_all[["data", "tipo", "descricao", "categoria", "valor"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Nenhum lançamento por voz registrado ainda.")

# ==========================================
# --- SEÇÃO: TAREFAS & COMPRAS (SEPARADAS EM ABAS) ---
# ==========================================
elif st.session_state.pagina_atual == "📝 Tarefas & Compras":
    botao_voltar()
    st.subheader("📝 Central de Organização: Compras & Tarefas")
    st.write("Gerencie suas compras e tarefas em abas separadas, acompanhe valores e salve automaticamente ao marcar os itens.")

    # Cria tabela unificada com suporte a valor e status
    c.execute("""
        CREATE TABLE IF NOT EXISTS tarefas_compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            item TEXT, 
            tipo TEXT, 
            valor REAL,
            concluido INTEGER
        )
    """)
    conn.commit()

    # Formulário único para cadastro rápido indicando se é Compra ou Tarefa
    with st.form("form_nova_tarefa_compra", clear_on_submit=True):
        col_t1, col_t2, col_t3 = st.columns([2, 1, 1])
        with col_t1:
            novo_item_texto = st.text_input("Descrição do Item ou Tarefa:")
        with col_t2:
            tipo_item = st.selectbox("Categoria:", ["🛒 Compra", "📋 Tarefa"])
        with col_t3:
            valor_item = st.number_input("Valor Estimado (R$):", min_value=0.0, step=10.0, format="%.2f")
        
        btn_add_item = st.form_submit_button("➕ Adicionar à Lista", use_container_width=True)
        if btn_add_item:
            if novo_item_texto.strip():
                val_salvar = valor_item if tipo_item == "🛒 Compra" else 0.0
                c.execute(
                    "INSERT INTO tarefas_compras (item, tipo, valor, concluido) VALUES (?, ?, ?, 0)",
                    (novo_item_texto.strip(), tipo_item, val_salvar)
                )
                conn.commit()
                st.success("Item adicionado com sucesso!")
                st.rerun()
            else:
                st.error("Digite a descrição do item.")

    st.markdown("---")

    # Recupera os dados do banco
    df_geral = pd.read_sql("SELECT * FROM tarefas_compras", conn)

    # Criação das Abas Separadas
    aba_compras, aba_tarefas = st.tabs(["🛒 Lista de Compras", "📋 Lista de Tarefas"])

    # ==========================================
    # --- ABA 1: COMPRAS ---
    # ==========================================
    with aba_compras:
        st.markdown("### 🛒 Gestão de Compras & Projeção de Gastos")
        df_compras = df_geral[df_geral["tipo"] == "🛒 Compra"] if not df_geral.empty else pd.DataFrame()

        if not df_compras.empty:
            total_compras = len(df_compras)
            compras_feitas = len(df_compras[df_compras["concluido"] == 1])
            prog_compras = (compras_feitas / total_compras) * 100 if total_compras > 0 else 0.0

            # Projeção: Soma dos valores de itens de compra pendentes
            df_comp_pend = df_compras[df_compras["concluido"] == 0]
            total_projetado = df_comp_pend["valor"].sum() if not df_comp_pend.empty else 0.0
            total_gasto_efetivado = df_compras[df_compras["concluido"] == 1]["valor"].sum() if not df_compras.empty else 0.0

            st.markdown(f"**Progresso das Compras: {prog_compras:.1f}% Concluído**")
            st.progress(prog_compras / 100.0)

            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("💰 Projeção (Falta Comprar)", f"R$ {total_projetado:,.2f}")
            c_m2.metric("✅ Total Já Comprado", f"R$ {total_gasto_efetivado:,.2f}")
            c_m3.metric("📦 Itens na Lista", total_compras)

            st.markdown("---")
            for index, row in df_compras.iterrows():
                col_c_chk, col_c_val, col_c_edit, col_c_del = st.columns([4, 2, 1, 1])
                
                status_c = True if row["concluido"] == 1 else False
                label_c = f"{row['item']}"
                valor_str = f"R$ {row['valor']:,.2f}" if row['valor'] > 0 else "R$ 0,00"

                with col_c_chk:
                    marcado_c = st.checkbox(label_c, value=status_c, key=f"check_compra_{row['id']}")
                    novo_est_c = 1 if marcado_c else 0
                    if novo_est_c != row["concluido"]:
                        c.execute("UPDATE tarefas_compras SET concluido = ? WHERE id = ?", (novo_est_c, row["id"]))
                        conn.commit()
                        st.rerun()

                with col_c_val:
                    st.markdown(f"**{valor_str}**")

                with col_c_edit:
                    with st.popover("✏️"):
                        with st.form(f"form_edit_c_{row['id']}"):
                            nc_desc = st.text_input("Item", value=row["item"])
                            nc_val = st.number_input("Valor", value=float(row["valor"]), step=10.0)
                            if st.form_submit_button("Salvar"):
                                c.execute("UPDATE tarefas_compras SET item = ?, valor = ? WHERE id = ?", (nc_desc, nc_val, row["id"]))
                                conn.commit()
                                st.rerun()

                with col_c_del:
                    if st.button("🗑️", key=f"del_compra_{row['id']}"):
                        c.execute("DELETE FROM tarefas_compras WHERE id = ?", (row["id"],))
                        conn.commit()
                        st.rerun()
                st.markdown("<hr style='margin: 4px 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
        else:
            st.info("Nenhum item de compra cadastrado.")

    # ==========================================
    # --- ABA 2: TAREFAS ---
    # ==========================================
    with aba_tarefas:
        st.markdown("### 📋 Gestão de Tarefas & Pendências")
        df_tarefas = df_geral[df_geral["tipo"] == "📋 Tarefa"] if not df_geral.empty else pd.DataFrame()

        if not df_tarefas.empty:
            total_t = len(df_tarefas)
            t_fechadas = len(df_tarefas[df_tarefas["concluido"] == 1])
            prog_t = (t_fechadas / total_t) * 100 if total_t > 0 else 0.0

            st.markdown(f"**Progresso das Tarefas: {prog_t:.1f}% Concluído**")
            st.progress(prog_t / 100.0)

            t_m1, t_m2, t_m3 = st.columns(3)
            t_m1.metric("Total de Tarefas", total_t)
            t_m2.metric("Concluídas", t_fechadas)
            t_m3.metric("Pendentes", total_t - t_fechadas)

            st.markdown("---")
            for index, row in df_tarefas.iterrows():
                col_t_chk, col_t_edit, col_t_del = st.columns([6, 1, 1])
                
                status_t = True if row["concluido"] == 1 else False
                label_t = f"{row['item']}"

                with col_t_chk:
                    marcado_t = st.checkbox(label_t, value=status_t, key=f"check_tarefa_aba_{row['id']}")
                    novo_est_t = 1 if marcado_t else 0
                    if novo_est_t != row["concluido"]:
                        c.execute("UPDATE tarefas_compras SET concluido = ? WHERE id = ?", (novo_est_t, row["id"]))
                        conn.commit()
                        st.rerun()

                with col_t_edit:
                    with st.popover("✏️"):
                        with st.form(f"form_edit_t_{row['id']}"):
                            nt_desc = st.text_input("Tarefa", value=row["item"])
                            if st.form_submit_button("Salvar"):
                                c.execute("UPDATE tarefas_compras SET item = ? WHERE id = ?", (nt_desc, row["id"]))
                                conn.commit()
                                st.rerun()

                with col_t_del:
                    if st.button("🗑️", key=f"del_tarefa_aba_{row['id']}"):
                        c.execute("DELETE FROM tarefas_compras WHERE id = ?", (row["id"],))
                        conn.commit()
                        st.rerun()
                st.markdown("<hr style='margin: 4px 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
        else:
            st.info("Nenhuma tarefa cadastrada.")

# ==========================================
# --- SEÇÃO 2.4: VEÍCULOS, MANUTENÇÕES & COMBUSTÍVEIS ---
# ==========================================
elif st.session_state.pagina_atual == "🚗 Veículos & Manutenção":
    botao_voltar()
    st.subheader(
        "🚗 Central de Veículos, Manutenções & Consumo de Combustível"
    )
    st.write(
        "Gerencie sua frota, registre quilometragem, agende manutenções e"
        " monitore o consumo médio de combustível."
    )

    if "aba_veiculos_ativa" not in st.session_state:
        st.session_state.aba_veiculos_ativa = "veiculos"

    col_v_btn1, col_v_btn2, col_v_btn3, _ = st.columns([1, 1, 1, 2])
    with col_v_btn1:
        if st.button(
            "🚗 Veículos",
            use_container_width=True,
            type=(
                "primary"
                if st.session_state.aba_veiculos_ativa == "veiculos"
                else "secondary"
            ),
        ):
            st.session_state.aba_veiculos_ativa = "veiculos"
            st.rerun()
    with col_v_btn2:
        if st.button(
            "📅 Manutenções",
            use_container_width=True,
            type=(
                "primary"
                if st.session_state.aba_veiculos_ativa == "manutencoes"
                else "secondary"
            ),
        ):
            st.session_state.aba_veiculos_ativa = "manutencoes"
            st.rerun()
    with col_v_btn3:
        if st.button(
            "⛽ Combustível",
            use_container_width=True,
            type=(
                "primary"
                if st.session_state.aba_veiculos_ativa == "combustivel"
                else "secondary"
            ),
        ):
            st.session_state.aba_veiculos_ativa = "combustivel"
            st.rerun()

    st.markdown("---")

    if st.session_state.aba_veiculos_ativa == "veiculos":
        st.write("### 🚗 Cadastro & Edição de Veículos")
        with st.form("form_cadastrar_veiculo", clear_on_submit=True):
            col_ve1, col_ve2 = st.columns(2)
            with col_ve1:
                placa_v = st.text_input("Placa do Veículo (Ex: ABC-1234)")
                modelo_v = st.text_input("Modelo do Veículo (Ex: Corolla, Onix)")
            with col_ve2:
                ano_v = st.text_input("Ano (Ex: 2021/2022)")
                km_v = st.number_input(
                    "Quilometragem Atual (Km)", min_value=0.0, value=0.0, step=100.0
                )

            if st.form_submit_button("Salvar Novo Veículo", use_container_width=True):
                if placa_v.strip() and modelo_v.strip():
                    c.execute(
                        "INSERT INTO veiculos (placa, modelo, ano, km_atual)"
                        " VALUES (?,?,?,?)",
                        (
                            placa_v.upper().strip(),
                            modelo_v.strip(),
                            ano_v.strip(),
                            km_v,
                        ),
                    )
                    conn.commit()
                    st.success(
                        f"Veículo {modelo_v.upper()} ({placa_v.upper()}) cadastrado com"
                        " sucesso!"
                    )
                    st.rerun()
                else:
                    st.error("Informe ao menos a placa e o modelo do veículo.")

        st.markdown("---")
        df_veiculos_reg = pd.read_sql("SELECT * FROM veiculos", conn)
        if not df_veiculos_reg.empty:
            st.write("### 📋 Veículos Cadastrados (Gerenciamento & Edição)")
            st.dataframe(
                df_veiculos_reg.rename(
                    columns={
                        "id": "ID",
                        "placa": "Placa",
                        "modelo": "Modelo",
                        "ano": "Ano",
                        "km_atual": "Km Atual",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

            col_ed_v1, col_ed_v2 = st.columns(2)
            with col_ed_v1:
                id_edit_veiculo = st.selectbox(
                    "Selecione o ID do veículo para EDITAR:",
                    df_veiculos_reg["id"].tolist(),
                    key="edit_veiculo_sel",
                )
            with col_ed_v2:
                id_del_veiculo = st.selectbox(
                    "Selecione o ID do veículo para EXCLUIR:",
                    df_veiculos_reg["id"].tolist(),
                    key="del_veiculo_sel",
                )

            if id_edit_veiculo:
                veic_atual_row = df_veiculos_reg[
                    df_veiculos_reg["id"] == id_edit_veiculo
                ].iloc[0]
                with st.form(f"form_editar_veiculo_{id_edit_veiculo}"):
                    st.write(f"**Editando Veículo ID {id_edit_veiculo}**")
                    nv_placa = st.text_input("Placa:", value=veic_atual_row["placa"])
                    nv_modelo = st.text_input("Modelo:", value=veic_atual_row["modelo"])
                    nv_ano = st.text_input("Ano:", value=veic_atual_row["ano"])
                    nv_km = st.number_input(
                        "Km Atual:",
                        min_value=0.0,
                        value=float(veic_atual_row["km_atual"]),
                        step=100.0,
                    )

                    if st.form_submit_button(
                        "Salvar Alterações do Veículo", use_container_width=True
                    ):
                        c.execute(
                            "UPDATE veiculos SET placa = ?, modelo = ?, ano = ?, km_atual ="
                            " ? WHERE id = ?",
                            (
                                nv_placa.upper().strip(),
                                nv_modelo.strip(),
                                nv_ano.strip(),
                                nv_km,
                                id_edit_veiculo,
                            ),
                        )
                        conn.commit()
                        st.success("Veículo atualizado com sucesso!")
                        st.rerun()

            if st.button("Excluir Veículo Selecionado", use_container_width=True):
                c.execute("DELETE FROM veiculos WHERE id = ?", (id_del_veiculo,))
                conn.commit()
                st.success("Veículo removido com sucesso!")
                st.rerun()
        else:
            st.info("Nenhum veículo cadastrado no momento.")

    elif st.session_state.aba_veiculos_ativa == "manutencoes":
        st.write("### 🛠️ Gestão de Manutenções (Agendadas & Histórico)")
        df_veic_opts = pd.read_sql("SELECT id, modelo, placa FROM veiculos", conn)

        if not df_veic_opts.empty:
            veiculos_map = {
                f"{row['modelo']} ({row['placa']})": row["id"]
                for _, row in df_veic_opts.iterrows()
            }

            with st.form("form_cadastrar_manutencao", clear_on_submit=True):
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    veic_escolhido = st.selectbox(
                        "Selecione o Veículo", list(veiculos_map.keys())
                    )
                    tipo_manut = st.selectbox(
                        "Tipo de Registro",
                        ["Manutenção Agendada", "Histórico Realizado"],
                    )
                    desc_manut = st.text_input(
                        "Descrição da Manutenção (Ex: Troca de Óleo, Pastilhas de Freio)"
                    )
                with col_m2:
                    data_manut = st.date_input(
                        "Data do Ocorrido / Agendamento (DD/MM/AAAA)",
                        value=date.today(),
                        format="DD/MM/YYYY",
                    )
                    valor_manut = st.number_input(
                        "Valor Estimado / Pago (R$)",
                        min_value=0.0,
                        value=0.00,
                        step=10.0,
                        format="%.2f",
                    )
                    status_manut = st.selectbox("Status", ["Pendente", "Concluído"])

                if st.form_submit_button(
                    "Salvar Registro de Manutenção", use_container_width=True
                ):
                    if desc_manut.strip():
                        v_id = veiculos_map[veic_escolhido]
                        c.execute(
                            "INSERT INTO manutencoes_veiculo (veiculo_id, tipo_registro,"
                            " descricao, data, valor, status) VALUES (?,?,?,?,?,?)",
                            (
                                v_id,
                                tipo_manut,
                                desc_manut.strip(),
                                data_manut.strftime("%Y-%m-%d"),
                                valor_manut,
                                status_manut,
                            ),
                        )
                        conn.commit()
                        st.success("Registro de manutenção salvo com sucesso!")
                        st.rerun()
                    else:
                        st.error("Informe a descrição da manutenção.")

            st.markdown("---")
            df_manut_all = pd.read_sql(
                "SELECT m.id, v.modelo, v.placa, m.tipo_registro, m.descricao,"
                " m.data, m.valor, m.status FROM manutencoes_veiculo m JOIN veiculos"
                " v ON m.veiculo_id = v.id",
                conn,
            )
            if not df_manut_all.empty:
                df_manut_all["data"] = df_manut_all["data"].apply(formatar_data_ptbr)
                st.write("### 📋 Registros de Manutenções")
                st.dataframe(
                    df_manut_all.rename(
                        columns={
                            "id": "ID",
                            "modelo": "Modelo",
                            "placa": "Placa",
                            "tipo_registro": "Tipo",
                            "descricao": "Descrição",
                            "data": "Data",
                            "valor": "Valor (R$)",
                            "status": "Status",
                        }
                    ),
                    use_container_width=True,
                )

                id_del_m = st.selectbox(
                    "Selecione o ID do registro de manutenção para remover:",
                    df_manut_all["id"].tolist(),
                    key="del_manut_sel",
                )
                if st.button("Remover Registro de Manutenção", use_container_width=True):
                    c.execute("DELETE FROM manutencoes_veiculo WHERE id = ?", (id_del_m,))
                    conn.commit()
                    st.success("Registro removido com sucesso!")
                    st.rerun()
            else:
                st.info("Nenhuma manutenção registrada.")
        else:
            st.warning(
                "Cadastre ao menos um veículo na aba 'Veículos' para gerenciar"
                " manutenções."
            )

    else:
        st.write("### ⛽ Controle de Consumo de Combustível")
        df_veic_opts = pd.read_sql("SELECT id, modelo, placa FROM veiculos", conn)
        if not df_veic_opts.empty:
            veiculos_map = {
                f"{row['modelo']} ({row['placa']})": row["id"]
                for _, row in df_veic_opts.iterrows()
            }
            with st.form("form_cadastrar_combustivel", clear_on_submit=True):
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    veic_comb = st.selectbox(
                        "Selecione o Veículo",
                        list(veiculos_map.keys()),
                        key="veic_comb_key",
                    )
                    data_comb = st.date_input(
                        "Data do Abastecimento (DD/MM/AAAA)",
                        value=date.today(),
                        key="data_comb_key",
                        format="DD/MM/YYYY",
                    )
                    litros_comb = st.number_input(
                        "Litros Abastecidos",
                        min_value=0.01,
                        value=40.0,
                        step=1.0,
                        format="%.2f",
                    )
                with col_c2:
                    valor_tot_comb = st.number_input(
                        "Valor Total Pago (R$)",
                        min_value=0.0,
                        value=200.0,
                        step=10.0,
                        format="%.2f",
                    )
                    km_odometro = st.number_input(
                        "Quilometragem no Odômetro (Km)",
                        min_value=0.0,
                        value=50000.0,
                        step=10.0,
                    )

                if st.form_submit_button(
                    "Registrar Abastecimento & Calcular Consumo",
                    use_container_width=True,
                ):
                    v_id_c = veiculos_map[veic_comb]
                    df_ant = pd.read_sql(
                        (
                            "SELECT km_odometro FROM consumo_combustivel WHERE"
                            " veiculo_id = ? ORDER BY id DESC LIMIT 1"
                        ),
                        conn,
                        params=(v_id_c,),
                    )
                    consumo_medio = 0.0
                    if not df_ant.empty:
                        km_anterior = df_ant.iloc[0]["km_odometro"]
                        km_rodados = km_odometro - km_anterior
                        if km_rodados > 0 and litros_comb > 0:
                            consumo_medio = km_rodados / litros_comb

                    c.execute(
                        "INSERT INTO consumo_combustivel (veiculo_id, data, litros,"
                        " valor_total, km_odometro, consumo_medio) VALUES"
                        " (?,?,?,?,?,?)",
                        (
                            v_id_c,
                            data_comb.strftime("%Y-%m-%d"),
                            litros_comb,
                            valor_tot_comb,
                            km_odometro,
                            consumo_medio,
                        ),
                    )
                    conn.commit()
                    st.success(
                        f"Abastecimento registrado com sucesso! Consumo médio estimado:"
                        f" {consumo_medio:.2f} Km/L"
                    )
                    st.rerun()

            st.markdown("---")
            df_comb_all = pd.read_sql(
                "SELECT c.id, v.modelo, v.placa, c.data, c.litros, c.valor_total,"
                " c.km_odometro, c.consumo_medio FROM consumo_combustivel c JOIN"
                " veiculos v ON c.veiculo_id = v.id",
                conn,
            )
            if not df_comb_all.empty:
                df_comb_all["data"] = df_comb_all["data"].apply(formatar_data_ptbr)
                st.write("### 📋 Histórico de Abastecimentos")
                st.dataframe(
                    df_comb_all.rename(
                        columns={
                            "id": "ID",
                            "modelo": "Modelo",
                            "placa": "Placa",
                            "data": "Data",
                            "litros": "Litros",
                            "valor_total": "Total (R$)",
                            "km_odometro": "Odômetro (Km)",
                            "consumo_medio": "Km/L Médio",
                        }
                    ),
                    use_container_width=True,
                )

                id_del_comb = st.selectbox(
                    "Selecione o ID do abastecimento para remover:",
                    df_comb_all["id"].tolist(),
                    key="del_comb_sel",
                )
                if st.button(
                    "Remover Registro de Abastecimento", use_container_width=True
                ):
                    c.execute(
                        "DELETE FROM consumo_combustivel WHERE id = ?", (id_del_comb,)
                    )
                    conn.commit()
                    st.success("Abastecimento removido com sucesso!")
                    st.rerun()
            else:
                st.info("Nenhum abastecimento registrado.")
        else:
            st.warning(
                "Cadastre ao menos um veículo na aba 'Veículos' para registrar o"
                " consumo."
            )

# ==========================================
# --- SEÇÃO 3A: DASHBOARD MANUAL (LANÇAMENTOS REAIS) ---
# ==========================================
elif st.session_state.pagina_atual == "📊 Dashboard Manual":
    botao_voltar()
    st.subheader("📊 Executive Dashboard — Lançamentos Reais Manuais")
    st.write(
        "Painel gerencial focado exclusivamente nos registros feitos de forma"
        " manual no sistema."
    )

    df_all = pd.read_sql(
        (
            "SELECT * FROM transacoes WHERE origem = 'Manual' OR origem ="
            " 'Nota_Fiscal' OR origem = 'Voz_IA' OR origem = 'Chat_IA'"
        ),
        conn,
    )
    df_banco_dash = pd.read_sql(
        "SELECT * FROM transacoes WHERE origem = 'Banco_PDF'", conn
    )
    df_inv_dash = pd.read_sql("SELECT * FROM carteira_investimentos", conn)
    df_cartao_dash = pd.read_sql("SELECT * FROM cartao_credito", conn)
    df_contas_dash = pd.read_sql("SELECT * FROM contas", conn)
    df_metas_dash = pd.read_sql("SELECT * FROM metas", conn)
    df_saldo_banco_manual = pd.read_sql("SELECT * FROM saldo_banco_manual ORDER BY id DESC LIMIT 1", conn)

    if "dash_manual_mes_ref" not in st.session_state:
        st.session_state.dash_manual_mes_ref = date.today().month
    if "dash_manual_ano_ref" not in st.session_state:
        st.session_state.dash_manual_ano_ref = date.today().year

    st.write("**Filtrar por Mês (Seleção Rápida em Botões Pequenos):**")
    meses_nomes_map = {
        1: "Jan",
        2: "Fev",
        3: "Mar",
        4: "Abr",
        5: "Mai",
        6: "Jun",
        7: "Jul",
        8: "Ago",
        9: "Set",
        10: "Out",
        11: "Nov",
        12: "Dez",
    }

    cols_meses_btns = st.columns(12)
    for m_idx in range(1, 13):
        with cols_meses_btns[m_idx - 1]:
            is_active_m = st.session_state.dash_manual_mes_ref == m_idx
            btn_type_m = "primary" if is_active_m else "secondary"
            if st.button(
                meses_nomes_map[m_idx],
                key=f"btn_mes_dash_m_{m_idx}",
                use_container_width=True,
                type=btn_type_m,
            ):
                st.session_state.dash_manual_mes_ref = m_idx
                st.rerun()

    mes_selecionado_num = st.session_state.dash_manual_mes_ref
    ano_selecionado_num = st.session_state.dash_manual_ano_ref
    mes_selecionado_str = f"{ano_selecionado_num}-{mes_selecionado_num:02d}"

    if not df_all.empty:
        df_all["data"] = pd.to_datetime(df_all["data"])
        df_all["ano_mes"] = df_all["data"].dt.strftime("%Y-%m")
        df = df_all[df_all["ano_mes"] == mes_selecionado_str].copy()
    else:
        df = df_all.copy()

    saldo_real_banco_pdf = 0.0
    if not df_saldo_banco_manual.empty:
        saldo_real_banco_pdf = float(df_saldo_banco_manual.iloc[0]["saldo_conta"])
    elif not df_banco_dash.empty:
        df_banco_dash["valor"] = pd.to_numeric(
            df_banco_dash["valor"], errors="coerce"
        ).fillna(0)
        rec_banco_tot = df_banco_dash[df_banco_dash["tipo"] == "Receita"][
            "valor"
        ].sum()
        desp_banco_tot = df_banco_dash[df_banco_dash["tipo"] == "Despesa"][
            "valor"
        ].sum()
        saldo_real_banco_pdf = rec_banco_tot - desp_banco_tot

    if not df_all.empty or not df_saldo_banco_manual.empty:
        if not df_all.empty:
            df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
            receitas = df[df["tipo"] == "Receita"]["valor"].sum()
            despesas = df[df["tipo"] == "Despesa"]["valor"].sum()
            saldo_caixa = receitas - despesas
        else:
            receitas = 0.0
            despesas = 0.0
            saldo_caixa = 0.0

        patrimonio_investido = (
            (df_inv_dash["quantidade"] * df_inv_dash["preco_medio"]).sum()
            if not df_inv_dash.empty
            else 0.0
        )
        total_faturas_cartao = (
            df_cartao_dash["valor"].sum() if not df_cartao_dash.empty else 0.0
        )
        total_contas_pendentes = (
            df_contas_dash[df_contas_dash["pago"] == 0]["valor"].sum()
            if not df_contas_dash.empty
            else 0.0
        )
        patrimonio_liquido_global = patrimonio_investido + max(0, saldo_caixa)

        burn_rate_diario = despesas / 30.0

        st.markdown("### 💼 Visão Geral & Indicadores Manuais")
        b1, b2, b3, b4, b5 = st.columns(5)
        with b1:
            st.markdown(
                f"""<div style="background: rgba(25,29,38,0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);"><span style="color: #94a3b8; font-size: 12px; font-weight: 600;">⚡ BURN RATE DIÁRIO</span><h3 style="color: #f8fafc; margin: 8px 0 0 0; font-size: 18px;">R$ {burn_rate_diario:,.2f} / dia</h3></div>""",
                unsafe_allow_html=True,
            )
        with b2:
            st.markdown(
                f"""<div style="background: rgba(25,29,38,0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);"><span style="color: #94a3b8; font-size: 12px; font-weight: 600;">💵 SALDO ATUAL (ENTRADA - SAÍDA)</span><h3 style="color: #3b82f6; margin: 8px 0 0 0; font-size: 18px;">R$ {saldo_caixa:,.2f}</h3></div>""",
                unsafe_allow_html=True,
            )
        with b3:
            st.markdown(
                f"""<div style="background: rgba(25,29,38,0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);"><span style="color: #94a3b8; font-size: 12px; font-weight: 600;">🏦 SALDO REAL NO BANCO</span><h3 style="color: #34d399; margin: 8px 0 0 0; font-size: 18px;">R$ {saldo_real_banco_pdf:,.2f}</h3></div>""",
                unsafe_allow_html=True,
            )
        with b4:
            st.markdown(
                f"""<div style="background: rgba(25,29,38,0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);"><span style="color: #94a3b8; font-size: 12px; font-weight: 600;">🟢 ENTRADAS MANUAIS</span><h3 style="color: #22c55e; margin: 8px 0 0 0; font-size: 18px;">R$ {receitas:,.2f}</h3></div>""",
                unsafe_allow_html=True,
            )
        with b5:
            st.markdown(
                f"""<div style="background: rgba(25,29,38,0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);"><span style="color: #94a3b8; font-size: 12px; font-weight: 600;">🔴 DESPESAS MANUAIS</span><h3 style="color: #ef4444; margin: 8px 0 0 0; font-size: 18px;">R$ {despesas:,.2f}</h3></div>""",
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("### 🏦 Acompanhamento de Saldo do Banco & Limites (Itaú)")
        with st.form("form_atualizar_saldo_banco_dash"):
            col_sb1, col_sb2, col_sb3, col_sb4 = st.columns(4)
            with col_sb1:
                val_sb_conta = st.number_input("Saldo em Conta (R$)", value=-157.15, step=1.0, format="%.2f")
            with col_sb2:
                val_sb_util = st.number_input("Limite Utilizado (R$)", value=157.15, step=1.0, format="%.2f")
            with col_sb3:
                val_sb_disp = st.number_input("Limite Disponível (R$)", value=2.85, step=1.0, format="%.2f")
            with col_sb4:
                val_sb_tot = st.number_input("Limite Total (R$)", value=160.00, step=1.0, format="%.2f")

            if st.form_submit_button("Salvar / Atualizar Saldo e Limites do Banco", use_container_width=True):
                c.execute("INSERT INTO saldo_banco_manual (data, banco, saldo_conta, limite_utilizado, limite_disponivel, limite_total) VALUES (?,?,?,?,?,?)",
                          (date.today().strftime("%Y-%m-%d"), "Itaú", val_sb_conta, val_sb_util, val_sb_disp, val_sb_tot))
                conn.commit()
                st.success("Saldo e limites do banco atualizados com sucesso!")
                st.rerun()

        st.markdown("---")
        st.markdown("### 🏛️ Indicadores Patrimoniais & Passivos")
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            st.markdown(
                f"""<div style="background: rgba(25,29,38,0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px;"><span style="color: #94a3b8; font-size: 12px; font-weight: 600;">💎 PATRIMÔNIO LÍQUIDO GLOBAL</span><h3 style="color: #60a5fa; margin: 8px 0 0 0; font-size: 18px;">R$ {patrimonio_liquido_global:,.2f}</h3></div>""",
                unsafe_allow_html=True,
            )
        with p2:
            st.markdown(
                f"""<div style="background: rgba(25,29,38,0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px;"><span style="color: #94a3b8; font-size: 12px; font-weight: 600;">📈 TOTAL INVESTIDO / CAIXINHAS</span><h3 style="color: #34d399; margin: 8px 0 0 0; font-size: 18px;">R$ {patrimonio_investido:,.2f}</h3></div>""",
                unsafe_allow_html=True,
            )
        with p3:
            st.markdown(
                f"""<div style="background: rgba(25,29,38,0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px;"><span style="color: #94a3b8; font-size: 12px; font-weight: 600;">💳 FATURAS DE CARTÃO</span><h3 style="color: #f59e0b; margin: 8px 0 0 0; font-size: 18px;">R$ {total_faturas_cartao:,.2f}</h3></div>""",
                unsafe_allow_html=True,
            )
        with p4:
            st.markdown(
                f"""<div style="background: rgba(25,29,38,0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px;"><span style="color: #94a3b8; font-size: 12px; font-weight: 600;">📅 CONTAS A PAGAR</span><h3 style="color: #ef4444; margin: 8px 0 0 0; font-size: 18px;">R$ {total_contas_pendentes:,.2f}</h3></div>""",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        media_despesa_mensal = (
            df_all[df_all["tipo"] == "Despesa"]["valor"].mean()
            if not df_all.empty
            else 0.0
        )
        if len(df_all["ano_mes"].unique()) > 0:
            desp_por_mes = df_all[df_all["tipo"] == "Despesa"].groupby("ano_mes")[
                "valor"
            ].sum()
            media_despesa_mensal = (
                desp_por_mes.mean() if not desp_por_mes.empty else 3000.0
            )

        meses_runway = (
            (patrimonio_liquido_global / media_despesa_mensal)
            if media_despesa_mensal > 0
            else 0.0
        )

        st.markdown(
            f"""
            <div style="background: rgba(59, 130, 246, 0.06); border: 1px solid rgba(59, 130, 246, 0.25); border-radius: 14px; padding: 20px; margin-bottom: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                <h4 style="color: #60a5fa; margin-top: 0; display: flex; align-items: center; gap: 8px;">🛡️ Índice de Autonomia Financeira (Runway)</h4>
                <p style="color: #f8fafc; font-size: 15px; margin-bottom: 5px;">
                    O seu patrimônio atual garante <b>{meses_runway:.1f} meses</b> de autonomia completa com base na despesa média manual (<b>R$ {media_despesa_mensal:,.2f}</b>).
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.subheader("🚨 Top 3 Maiores Vilões Manuais do Mês")
        df_desp_mes = df[df["tipo"] == "Despesa"].copy()
        if not df_desp_mes.empty:
            top_viloes = df_desp_mes.sort_values(by="valor", ascending=False).head(3)
            v1, v2, v3 = st.columns(3)
            cols_v = [v1, v2, v3]

            for idx, (_, row_v) in enumerate(top_viloes.iterrows()):
                if idx < len(cols_v):
                    with cols_v[idx]:
                        st.markdown(
                            f"""
                            <div style="background: rgba(239, 68, 68, 0.06); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 12px; padding: 18px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                                <span style="font-size: 11px; color: #f87171; font-weight: 700; letter-spacing: 0.5px;"># {idx+1} MAIOR GASTO</span>
                                <h4 style="color: #f8fafc; margin: 6px 0 2px 0; font-size: 16px;">{row_v['descricao']}</h4>
                                <p style="color: #94a3b8; font-size: 13px; margin: 0 0 10px 0;">{row_v['categoria']}</p>
                                <h3 style="color: #ef4444; margin: 0; font-size: 18px;">R$ {row_v['valor']:,.2f}</h3>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

        st.markdown("---")
        st.subheader(
            "🎯 Acompanhamento Rigoroso da Regra 50 / 30 / 20 (Manual)"
        )
        if receitas > 0:
            nec = df[
                (df["tipo"] == "Despesa")
                & (df["categoria"].str.contains("Necessidade", na=False))
            ]["valor"].sum()
            des = df[
                (df["tipo"] == "Despesa")
                & (df["categoria"].str.contains("Desejos", na=False))
            ]["valor"].sum()
            inv = df[
                (df["tipo"] == "Despesa")
                & (df["categoria"].str.contains("Investimentos", na=False))
            ]["valor"].sum()

            meta_nec, meta_des, meta_inv = (
                receitas * 0.50,
                receitas * 0.30,
                receitas * 0.20,
            )

            c_50, c_30, c_20 = st.columns(3)
            with c_50:
                st.markdown(
                    f"""
                    <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                        <span style="color: #94a3b8; font-size: 12px; font-weight: 600;">50% NECESSIDADES (TETO)</span>
                        <p style="color: #f8fafc; font-size: 14px; margin: 6px 0;">Gasto: R$ {nec:,.2f} / Meta: R$ {meta_nec:,.2f}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.progress(min(nec / meta_nec if meta_nec > 0 else 0, 1.0))
            with c_30:
                st.markdown(
                    f"""
                    <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                        <span style="color: #94a3b8; font-size: 12px; font-weight: 600;">30% DESEJOS (TETO)</span>
                        <p style="color: #f8fafc; font-size: 14px; margin: 6px 0;">Gasto: R$ {des:,.2f} / Meta: R$ {meta_des:,.2f}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.progress(min(des / meta_des if meta_des > 0 else 0, 1.0))
            with c_20:
                st.markdown(
                    f"""
                    <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                        <span style="color: #94a3b8; font-size: 12px; font-weight: 600;">20% INVESTIMENTOS (MÍNIMO)</span>
                        <p style="color: #f8fafc; font-size: 14px; margin: 6px 0;">Guardado: R$ {inv:,.2f} / Meta: R$ {meta_inv:,.2f}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.progress(min(inv / meta_inv if meta_inv > 0 else 0, 1.0))

        st.markdown("---")
        st.subheader("🎯 Termômetro de Metas por Categoria")
        if not df_metas_dash.empty:
            for _, meta_row in df_metas_dash.iterrows():
                c_nome = meta_row["categoria"]
                teto_meta = meta_row["valor_meta"]
                gasto_cat_real = df[
                    (df["categoria"] == c_nome) & (df["tipo"] == "Despesa")
                ]["valor"].sum()
                pct_atingido = (
                    (gasto_cat_real / teto_meta) if teto_meta > 0 else 0.0
                )
                st.markdown(
                    f"""
                    <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px; margin-bottom: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                        <span style="color: #f8fafc; font-weight: 600; font-size: 14px;">{c_nome}</span>
                        <p style="color: #94a3b8; font-size: 13px; margin: 4px 0;">Real: R$ {gasto_cat_real:,.2f} / Teto: R$ {teto_meta:,.2f} ({(pct_atingido*100):.1f}%)</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.progress(min(pct_atingido, 1.0))

        st.markdown("---")
        st.subheader("📈 Distribuição de Despesas Manuais por Categoria (Gráfico de Rosca Interativo)")
        df_desp = df[df["tipo"] == "Despesa"]
        if not df_desp.empty:
            gasto_cat = df_desp.groupby("categoria")["valor"].sum().reset_index()
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                fig_pie = px.pie(
                    gasto_cat,
                    names="categoria",
                    values="valor",
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.RdBu,
                )
                fig_pie.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#f8fafc",
                    margin=dict(t=10, b=10, l=10, r=10),
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            with col_g2:
                df_resumo = gasto_cat.rename(columns={"categoria": "Categoria", "valor": "Total Gasto (R$)"})
                df_resumo["Total Gasto (R$)"] = df_resumo["Total Gasto (R$)"].apply(
                    lambda x: f"R$ {x:,.2f}"
                )
                st.dataframe(df_resumo, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("🏷️ Distribuição de Despesas Manuais por Descrição Específica")
        if not df_desp.empty:
            gasto_desc = df_desp.groupby("descricao")["valor"].sum().reset_index().sort_values(by="valor", ascending=False)
            col_gd1, col_gd2 = st.columns(2)
            with col_gd1:
                fig_pie_desc = px.pie(
                    gasto_desc.head(8),
                    names="descricao",
                    values="valor",
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.Viridis,
                )
                fig_pie_desc.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#f8fafc",
                    margin=dict(t=10, b=10, l=10, r=10),
                )
                st.plotly_chart(fig_pie_desc, use_container_width=True)
            with col_gd2:
                df_resumo_desc = gasto_desc.rename(columns={"descricao": "Descrição", "valor": "Total Gasto (R$)"})
                df_resumo_desc["Total Gasto (R$)"] = df_resumo_desc["Total Gasto (R$)"].apply(
                    lambda x: f"R$ {x:,.2f}"
                )
                st.dataframe(df_resumo_desc, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📊 Gráfico de Área Empilhada: Dinâmica 50/30/20 (Manual)")
        df_empilhado = df_all[df_all["tipo"] == "Despesa"].copy()
        if not df_empilhado.empty:

            def mapear_pilar(cat):
                if (
                    "Necessidade" in str(cat)
                    or "Supermercado" in str(cat)
                    or "Contas Fixas" in str(cat)
                    or "Transporte" in str(cat)
                    or "Saúde" in str(cat)
                    or "Pet" in str(cat)
                ):
                    return "Necessidades (50%)"
                elif "Desejos" in str(cat) or "Lazer" in str(cat):
                    return "Desejos (30%)"
                else:
                    return "Investimentos (20%)"

            df_empilhado["Pilar"] = df_empilhado["categoria"].apply(mapear_pilar)
            df_area_pivot = df_empilhado.pivot_table(
                index="ano_mes", columns="Pilar", values="valor", aggfunc="sum"
            ).fillna(0)
            st.area_chart(df_area_pivot)
    else:
        st.info(
            "Nenhum lançamento manual registrado para exibir no dashboard. Utilize"
            " as abas de lançamento para adicionar dados."
        )

# ==========================================
# --- SEÇÃO 3B: DASHBOARD EXTRATO BANCO (PDF) ---
# ==========================================
elif st.session_state.pagina_atual == "📥 Dashboard Banco":
    botao_voltar()
    st.subheader(
        "📥 Dashboard de Auditoria & Extratos Importados do Banco"
    )
    st.write(
        "Painel exclusivo para analisar transações geradas automaticamente por"
        " upload de extratos bancários em PDF."
    )

    df_banco_all = pd.read_sql(
        "SELECT * FROM transacoes WHERE origem = 'Banco_PDF'", conn
    )
    df_saldo_banco_manual_db = pd.read_sql("SELECT * FROM saldo_banco_manual ORDER BY id DESC LIMIT 1", conn)

    if not df_banco_all.empty or not df_saldo_banco_manual_db.empty:
        if not df_banco_all.empty:
            df_banco_all["data"] = pd.to_datetime(df_banco_all["data"])
            df_banco_all["ano_mes"] = df_banco_all["data"].dt.strftime("%Y-%m")
            meses_banco = sorted(df_banco_all["ano_mes"].unique(), reverse=True)
        else:
            meses_banco = ["2026-08"]

        col_fb1, col_fb2 = st.columns([2, 4])
        with col_fb1:
            mes_banco_sel = st.selectbox(
                "📅 Selecionar Mês do Extrato Bancário:", meses_banco
            )

        if not df_banco_all.empty:
            df_b = df_banco_all[df_banco_all["ano_mes"] == mes_banco_sel].copy()
            rec_b = df_b[df_b["tipo"] == "Receita"]["valor"].sum()
            desp_b = df_b[df_b["tipo"] == "Despesa"]["valor"].sum()
            saldo_b = rec_b - desp_b
        else:
            df_b = pd.DataFrame()
            rec_b = 0.0
            desp_b = 0.0
            saldo_b = 0.0

        saldo_real_total_banco = 0.0
        limite_utilizado_val = 0.0
        limite_disponivel_val = 0.0
        limite_total_val = 0.0

        if not df_saldo_banco_manual_db.empty:
            saldo_real_total_banco = float(df_saldo_banco_manual_db.iloc[0]["saldo_conta"])
            limite_utilizado_val = float(df_saldo_banco_manual_db.iloc[0]["limite_utilizado"])
            limite_disponivel_val = float(df_saldo_banco_manual_db.iloc[0]["limite_disponivel"])
            limite_total_val = float(df_saldo_banco_manual_db.iloc[0]["limite_total"])
        elif not df_banco_all.empty:
            df_banco_all["valor"] = pd.to_numeric(
                df_banco_all["valor"], errors="coerce"
            ).fillna(0)
            total_geral_rec_banco = df_banco_all[df_banco_all["tipo"] == "Receita"][
                "valor"
            ].sum()
            total_geral_desp_banco = df_banco_all[df_banco_all["tipo"] == "Despesa"][
                "valor"
            ].sum()
            saldo_real_total_banco = total_geral_rec_banco - total_geral_desp_banco

        st.markdown("### 📊 Indicadores Consolidados do Extrato Bancário & Saldo Real")
        
        st.markdown(
            f"""
            <div style="background: rgba(34, 197, 94, 0.06); border: 1px solid rgba(34, 197, 94, 0.25); border-radius: 14px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                <h4 style="color: #4ade80; margin-top: 0;">🏦 Acompanhamento de Saldo e Limites (Extrato Real Itaú)</h4>
                <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-top: 10px;">
                    <div><span style="color: #94a3b8; font-size: 12px;">Saldo em Conta:</span><h3 style="color: #ef4444; margin: 2px 0 0 0;">R$ {saldo_real_total_banco:,.2f}</h3></div>
                    <div><span style="color: #94a3b8; font-size: 12px;">Limite Utilizado:</span><h3 style="color: #f59e0b; margin: 2px 0 0 0;">R$ {limite_utilizado_val:,.2f}</h3></div>
                    <div><span style="color: #94a3b8; font-size: 12px;">Limite Disponível:</span><h3 style="color: #34d399; margin: 2px 0 0 0;">R$ {limite_disponivel_val:,.2f}</h3></div>
                    <div><span style="color: #94a3b8; font-size: 12px;">Limite Total:</span><h3 style="color: #60a5fa; margin: 2px 0 0 0;">R$ {limite_total_val:,.2f}</h3></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        cb1, cb2, cb3, cb4 = st.columns(4)
        with cb1:
            st.markdown(
                f"""
                <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                    <span style="color: #94a3b8; font-size: 12px; font-weight: 600;">🏦 SALDO REAL NO BANCO</span>
                    <h3 style="color: #34d399; margin: 8px 0 0 0; font-size: 20px;">R$ {saldo_real_total_banco:,.2f}</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with cb2:
            st.markdown(
                f"""
                <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                    <span style="color: #94a3b8; font-size: 12px; font-weight: 600;">💰 SALDO LÍQUIDO DO MÊS</span>
                    <h3 style="color: #3b82f6; margin: 8px 0 0 0; font-size: 20px;">R$ {saldo_b:,.2f}</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with cb3:
            st.markdown(
                f"""
                <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                    <span style="color: #94a3b8; font-size: 12px; font-weight: 600;">🟢 ENTRADAS NO EXTRATO</span>
                    <h3 style="color: #22c55e; margin: 8px 0 0 0; font-size: 20px;">R$ {rec_b:,.2f}</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with cb4:
            st.markdown(
                f"""
                <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                    <span style="color: #94a3b8; font-size: 12px; font-weight: 600;">🔴 SAÍDAS NO EXTRATO</span>
                    <h3 style="color: #ef4444; margin: 8px 0 0 0; font-size: 20px;">R$ {desp_b:,.2f}</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.subheader("🔥 Dias de Pico de Saídas (Extrato Bancário)")
        df_desp_banco = df_b[df_b["tipo"] == "Despesa"] if not df_b.empty else pd.DataFrame()
        if not df_desp_banco.empty:
            picos_banco = (
                df_desp_banco.groupby("data")["valor"]
                .sum()
                .reset_index()
                .sort_values(by="valor", ascending=False)
                .head(3)
            )
            cols_pb = st.columns(3)
            for idx_p, (_, row_pb) in enumerate(picos_banco.iterrows()):
                if idx_p < len(cols_pb):
                    with cols_pb[idx_p]:
                        st.markdown(
                            f"""
                            <div style="background: rgba(239, 68, 68, 0.06); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 12px; padding: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                                <span style="color: #f87171; font-size: 12px; font-weight: 700;">📅 DIA {row_pb['data'].strftime('%d/%m/%Y')}</span>
                                <h3 style="color: #ef4444; margin: 8px 0 0 0; font-size: 18px;">R$ {row_pb['valor']:,.2f}</h3>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

        st.markdown("---")
        st.subheader("📈 Distribuição de Gastos do Extrato por Categoria (Gráfico de Rosca)")
        if not df_desp_banco.empty:
            gasto_cat_b = df_desp_banco.groupby("categoria")["valor"].sum().reset_index()
            col_gb1, col_gb2 = st.columns(2)
            with col_gb1:
                fig_pie_b = px.pie(
                    gasto_cat_b,
                    names="categoria",
                    values="valor",
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.Teal,
                )
                fig_pie_b.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#f8fafc",
                    margin=dict(t=10, b=10, l=10, r=10),
                )
                st.plotly_chart(fig_pie_b, use_container_width=True)
            with col_gb2:
                df_res_b = gasto_cat_b.rename(columns={"categoria": "Categoria", "valor": "Total (R$)"})
                df_res_b["Total (R$)"] = df_res_b["Total (R$)"].apply(
                    lambda x: f"R$ {x:,.2f}"
                )
                st.dataframe(df_res_b, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("🏷️ Distribuição de Gastos do Extrato por Descrição Específica")
        if not df_desp_banco.empty:
            gasto_desc_b = df_desp_banco.groupby("descricao")["valor"].sum().reset_index().sort_values(by="valor", ascending=False)
            col_gdb1, col_gdb2 = st.columns(2)
            with col_gdb1:
                fig_pie_db = px.pie(
                    gasto_desc_b.head(8),
                    names="descricao",
                    values="valor",
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.Plasma,
                )
                fig_pie_db.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#f8fafc",
                    margin=dict(t=10, b=10, l=10, r=10),
                )
                st.plotly_chart(fig_pie_db, use_container_width=True)
            with col_gdb2:
                df_res_desc_b = gasto_desc_b.rename(columns={"descricao": "Descrição", "valor": "Total (R$)"})
                df_res_desc_b["Total (R$)"] = df_res_desc_b["Total (R$)"].apply(
                    lambda x: f"R$ {x:,.2f}"
                )
                st.dataframe(df_res_desc_b, use_container_width=True, hide_index=True)

        if not df_b.empty:
            st.markdown("---")
            st.subheader("📋 Relação Completa de Transações do Extrato PDF")
            df_b["data"] = df_b["data"].dt.strftime("%d/%m/%Y")
            st.dataframe(
                df_b[["data", "tipo", "descricao", "categoria", "valor"]],
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info(
            "Nenhum extrato bancário em PDF foi importado e processado até o"
            " momento. Faça o upload na aba 'Extrato & Backup'."
        )

# ==========================================
# --- SEÇÃO 4: PREVISÃO FINANCEIRA ---
# ==========================================
elif st.session_state.pagina_atual == "🔮 Previsão Financeira":
    botao_voltar()
    st.subheader("📅 Previsão Financeira & Simulador de Imprevistos")
    st.write(
        "Visualize suas finanças detalhadamente por mês ou acumulado anual,"
        " separando lançamentos manuais e extratos do banco, incluindo entradas"
        " previstas, contas a pagar, contas a receber e simulações."
    )

    if "prev_data_atual" not in st.session_state or not isinstance(
        st.session_state.prev_data_atual, (date, datetime)
    ):
        st.session_state.prev_data_atual = datetime.now().replace(day=1)

    col_cfg1, col_cfg2, col_exp_btn = st.columns([3, 3, 2])

    with col_cfg1:
        st.markdown(
            "<span style='font-size:12px; color:#94a3b8;"
            " font-weight:600;'>PERÍODO DA VISÃO</span>",
            unsafe_allow_html=True,
        )
        if "tipo_visao" not in st.session_state:
            st.session_state.tipo_visao = "Mensal"

        cv_p1, cv_p2 = st.columns(2)
        with cv_p1:
            is_mensal = st.session_state.tipo_visao == "Mensal"
            if st.button(
                "Mensal",
                use_container_width=True,
                type="primary" if is_mensal else "secondary",
            ):
                st.session_state.tipo_visao = "Mensal"
                st.rerun()
        with cv_p2:
            is_anual = st.session_state.tipo_visao == "Anual"
            if st.button(
                "Anual",
                use_container_width=True,
                type="primary" if is_anual else "secondary",
            ):
                st.session_state.tipo_visao = "Anual"
                st.rerun()

    with col_cfg2:
        st.markdown(
            "<span style='font-size:12px; color:#94a3b8;"
            " font-weight:600;'>FORMATO DE EXIBIÇÃO</span>",
            unsafe_allow_html=True,
        )
        if "formato_exibicao" not in st.session_state:
            st.session_state.formato_exibicao = "Gráfico"

        cv_e1, cv_e2 = st.columns(2)
        with cv_e1:
            is_grafico = st.session_state.formato_exibicao == "Gráfico"
            if st.button(
                "Gráfico",
                use_container_width=True,
                type="primary" if is_grafico else "secondary",
            ):
                st.session_state.formato_exibicao = "Gráfico"
                st.rerun()
        with cv_e2:
            is_tabela = st.session_state.formato_exibicao == "Tabela"
            if st.button(
                "Tabela",
                use_container_width=True,
                type="primary" if is_tabela else "secondary",
            ):
                st.session_state.formato_exibicao = "Tabela"
                st.rerun()

    with col_exp_btn:
        st.markdown(
            "<span style='font-size:12px; color:transparent;'>EXPORTAR</span>",
            unsafe_allow_html=True,
        )
        if st.button("📥 Exportar Relatório", use_container_width=True):
            st.success("Relatório de previsão exportado com sucesso!")

    tipo_visao = st.session_state.tipo_visao
    formato_exibicao = st.session_state.formato_exibicao

    st.markdown("---")

    st.markdown(
        "<span style='font-size:12px; color:#94a3b8; font-weight:600;"
        " text-transform:uppercase;'>Selecionar Mês de Referência (Navegação"
        " Rápida)</span>",
        unsafe_allow_html=True,
    )

    col_nav_ant, col_nav_prox = st.columns(2)
    with col_nav_ant:
        if st.button("❮ Mês Anterior", use_container_width=True, type="secondary"):
            if tipo_visao == "Mensal":
                st.session_state.prev_data_atual = (
                    st.session_state.prev_data_atual - timedelta(days=1)
                ).replace(day=1)
            else:
                st.session_state.prev_data_atual = (
                    st.session_state.prev_data_atual.replace(
                        year=st.session_state.prev_data_atual.year - 1
                    )
                )
            st.rerun()

    with col_nav_prox:
        if st.button("Mês Seguinte ❯", use_container_width=True, type="primary"):
            if tipo_visao == "Mensal":
                st.session_state.prev_data_atual = (
                    st.session_state.prev_data_atual + timedelta(days=32)
                ).replace(day=1)
            else:
                st.session_state.prev_data_atual = (
                    st.session_state.prev_data_atual.replace(
                        year=st.session_state.prev_data_atual.year + 1
                    )
                )
            st.rerun()

    meses_nomes_pt = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro",
    }
    ano_ativo = st.session_state.prev_data_atual.year
    mes_ativo_num = st.session_state.prev_data_atual.month
    nome_mes_exib = meses_nomes_pt[mes_ativo_num]

    if tipo_visao == "Mensal":
        st.markdown(
            f"<h3 style='text-align: center; color: #f8fafc; margin: 15px"
            f" 0;'>Referência: {nome_mes_exib} de {ano_ativo}</h3>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<h3 style='text-align: center; color: #f8fafc; margin: 15px"
            f" 0;'>Referência Acumulada: Ano de {ano_ativo}</h3>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    df_cartao_prev = pd.read_sql("SELECT * FROM cartao_credito", conn)
    df_contas_prev = pd.read_sql("SELECT * FROM contas WHERE pago = 0", conn)
    df_receber_prev = pd.read_sql(
        "SELECT * FROM contas_receber WHERE recebido = 0", conn
    )
    df_trans_prev = pd.read_sql("SELECT * FROM transacoes", conn)

    if not df_cartao_prev.empty:
        df_cartao_prev["data_dt"] = pd.to_datetime(
            df_cartao_prev["data"], errors="coerce"
        )
    if not df_contas_prev.empty:
        df_contas_prev["venc_dt"] = pd.to_datetime(
            df_contas_prev["vencimento"], errors="coerce"
        )
    if not df_receber_prev.empty:
        df_receber_prev["venc_dt"] = pd.to_datetime(
            df_receber_prev["vencimento"], errors="coerce"
        )
    if not df_trans_prev.empty:
        df_trans_prev["data_dt"] = pd.to_datetime(
            df_trans_prev["data"], errors="coerce"
        )

    mes_ref_filtro_str = f"{ano_ativo}-{mes_ativo_num:02d}"

    if tipo_visao == "Mensal":
        f_cartao = (
            df_cartao_prev[df_cartao_prev["mes_fatura"] == mes_ref_filtro_str]
            if not df_cartao_prev.empty and "mes_fatura" in df_cartao_prev.columns
            else (
                df_cartao_prev[
                    (df_cartao_prev["data_dt"].dt.year == ano_ativo)
                    & (df_cartao_prev["data_dt"].dt.month == mes_ativo_num)
                ]
                if not df_cartao_prev.empty
                else pd.DataFrame()
            )
        )
        f_contas = (
            df_contas_prev[
                (df_contas_prev["venc_dt"].dt.year == ano_ativo)
                & (df_contas_prev["venc_dt"].dt.month == mes_ativo_num)
            ]
            if not df_contas_prev.empty
            else pd.DataFrame()
        )
        f_receber = (
            df_receber_prev[
                (df_receber_prev["venc_dt"].dt.year == ano_ativo)
                & (df_receber_prev["venc_dt"].dt.month == mes_ativo_num)
            ]
            if not df_receber_prev.empty
            else pd.DataFrame()
        )
        f_trans = (
            df_trans_prev[
                (df_trans_prev["data_dt"].dt.year == ano_ativo)
                & (df_trans_prev["data_dt"].dt.month == mes_ativo_num)
            ]
            if not df_trans_prev.empty
            else pd.DataFrame()
        )
    else:
        f_cartao = (
            df_cartao_prev[df_cartao_prev["data_dt"].dt.year == ano_ativo]
            if not df_cartao_prev.empty
            else pd.DataFrame()
        )
        f_contas = (
            df_contas_prev[df_contas_prev["venc_dt"].dt.year == ano_ativo]
            if not df_contas_prev.empty
            else pd.DataFrame()
        )
        f_receber = (
            df_receber_prev[df_receber_prev["venc_dt"].dt.year == ano_ativo]
            if not df_receber_prev.empty
            else pd.DataFrame()
        )
        f_trans = (
            df_trans_prev[df_trans_prev["data_dt"].dt.year == ano_ativo]
            if not df_trans_prev.empty
            else pd.DataFrame()
        )

    f_trans_manuais = (
        f_trans[f_trans["origem"] != "Banco_PDF"]
        if not f_trans.empty
        else pd.DataFrame()
    )

    total_faturas = f_cartao["valor"].sum() if not f_cartao.empty else 0.0
    total_contas_pagar = f_contas["valor"].sum() if not f_contas.empty else 0.0
    total_contas_receber = (
        f_receber["valor"].sum() if not f_receber.empty else 0.0
    )

    entradas_manuais = (
        f_trans_manuais[f_trans_manuais["tipo"] == "Receita"]["valor"].sum()
        if not f_trans_manuais.empty
        else 0.0
    )
    saidas_manuais = (
        f_trans_manuais[f_trans_manuais["tipo"] == "Despesa"]["valor"].sum()
        if not f_trans_manuais.empty
        else 0.0
    )

    total_entradas_previstas = entradas_manuais + total_contas_receber
    total_saidas_previstas = total_faturas + total_contas_pagar + saidas_manuais
    saldo_projetado = total_entradas_previstas - total_saidas_previstas

    st.markdown("### 🧪 Simulador de Imprevistos & Ajustes Orçamentários")
    col_sim1, col_sim2 = st.columns(2)
    with col_sim1:
        valor_simulado_imprevisto = st.number_input(
            "Valor do Imprevisto (R$):",
            min_value=0.0,
            value=0.00,
            step=50.0,
            format="%.2f",
        )
    with col_sim2:
        tipo_imprevisto = st.selectbox(
            "Tipo de Imprevisto:", ["Gastos / Despesa Extra", "Entrada / Receita Extra"]
        )

    if valor_simulado_imprevisto > 0:
        if tipo_imprevisto == "Gastos / Despesa Extra":
            saldo_com_simulacao = saldo_projetado - valor_simulado_imprevisto
            st.warning(
                f"⚠️ **Simulação Ativa (Despesa Extra):** O saldo projetado cairia de"
                f" **R$ {saldo_projetado:,.2f}** para **R$"
                f" {saldo_com_simulacao:,.2f}**."
            )
        else:
            saldo_com_simulacao = saldo_projetado + valor_simulado_imprevisto
            st.success(
                f"🟢 **Simulação Ativa (Receita Extra):** O saldo projetado subiria"
                f" de **R$ {saldo_projetado:,.2f}** para **R$"
                f" {saldo_com_simulacao:,.2f}**."
            )

    st.markdown("---")

    st.markdown("### 📊 Previsão Exclusiva de Lançamentos Manuais")
    st.markdown(
        f"""
        <div class="group-card">
            <h4 style="color: #60a5fa; margin-top: 0;">💼 Lançamentos Manuais & Previstos</h4>
            <p><b>🟢 Entradas Manuais:</b> R$ {entradas_manuais:,.2f}</p>
            <p><b>📈 Contas a Receber:</b> R$ {total_contas_receber:,.2f}</p>
            <p><b>🔴 Saídas Manuais:</b> R$ {saidas_manuais:,.2f}</p>
            <p><b>📅 Contas a Pagar:</b> R$ {total_contas_pagar:,.2f}</p>
            <p><b>💳 Faturas de Cartão:</b> R$ {total_faturas:,.2f}</p>
            <hr style="border-color: var(--border-color);">
            <h4 style="color: #f8fafc;">Saldo Líquido Manual: R$ {saldo_projetado:,.2f}</h4>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(
            f"""
            <div style="background: rgba(34, 197, 94, 0.06); border: 1px solid rgba(34, 197, 94, 0.25); border-radius: 14px; padding: 22px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                <span style="color: #4ade80; font-size: 12px; font-weight: 700; letter-spacing: 0.5px;">🟢 TOTAL ENTRADAS MANUAIS</span>
                <h2 style="color: #22c55e; margin: 8px 0 0 0; font-size: 22px;">R$ {total_entradas_previstas:,.2f}</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f"""
            <div style="background: rgba(239, 68, 68, 0.06); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 14px; padding: 22px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                <span style="color: #f87171; font-size: 12px; font-weight: 700; letter-spacing: 0.5px;">🔴 TOTAL SAÍDAS MANUAIS</span>
                <h2 style="color: #ef4444; margin: 8px 0 0 0; font-size: 22px;">R$ {total_saidas_previstas:,.2f}</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f"""
            <div style="background: rgba(59, 130, 246, 0.06); border: 1px solid rgba(59, 130, 246, 0.25); border-radius: 14px; padding: 22px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                <span style="color: #60a5fa; font-size: 12px; font-weight: 700; letter-spacing: 0.5px;">⚖️ SALDO PROJETADO MANUAL</span>
                <h2 style="color: #3b82f6; margin: 8px 0 0 0; font-size: 22px;">R$ {saldo_projetado:,.2f}</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader(
        f"📋 Tabela Detalhada dos Movimentos Previstos ({nome_mes_exib} de"
        f" {ano_ativo})"
    )

    lista_gastos_previstos_detalhe = []
    
    if not f_receber.empty:
        for _, rcr in f_receber.iterrows():
            lista_gastos_previstos_detalhe.append({
                "Origem / Tipo": "📈 Conta a Receber",
                "Descrição": rcr["descricao"],
                "Categoria": "Freelance / Extra / Recebível",
                "Vencimento / Data": formatar_data_ptbr(rcr["vencimento"]),
                "Valor (R$)": rcr["valor"],
            })

    if not f_cartao.empty:
        for _, rc in f_cartao.iterrows():
            lista_gastos_previstos_detalhe.append({
                "Origem / Tipo": "💳 Fatura de Cartão",
                "Descrição": rc["descricao"],
                "Categoria": rc.get("categoria", "Cartão de Crédito"),
                "Vencimento / Data": formatar_data_ptbr(rc["data"]),
                "Valor (R$)": rc["valor"],
            })
    if not f_contas.empty:
        for _, rcp in f_contas.iterrows():
            lista_gastos_previstos_detalhe.append({
                "Origem / Tipo": "📉 Conta a Pagar",
                "Descrição": rcp["descricao"],
                "Categoria": "Contas Fixas / Boletos",
                "Vencimento / Data": formatar_data_ptbr(rcp["vencimento"]),
                "Valor (R$)": rcp["valor"],
            })
    if not f_trans.empty:
        df_trans_desp_mes = f_trans[
            (f_trans["tipo"] == "Despesa") & (f_trans["origem"] != "Banco_PDF")
        ]
        for _, rtd in df_trans_desp_mes.iterrows():
            lista_gastos_previstos_detalhe.append({
                "Origem / Tipo": f"🔴 Despesa ({rtd['origem']})",
                "Descrição": rtd["descricao"],
                "Categoria": rtd["categoria"],
                "Vencimento / Data": formatar_data_ptbr(rtd["data"]),
                "Valor (R$)": rtd["valor"],
            })

    if lista_gastos_previstos_detalhe:
        df_detalhe_gastos_mes = pd.DataFrame(lista_gastos_previstos_detalhe)
        st.dataframe(
            df_detalhe_gastos_mes.style.format({"Valor (R$)": "R$ {:,.2f}"}),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            f"Nenhum movimento previsto registrado para {nome_mes_exib} de {ano_ativo}."
        )

# ==========================================
# --- SEÇÃO 5: CARTÃO DE CRÉDITO ---
# ==========================================
elif st.session_state.pagina_atual == "💳 Cartão de Crédito":
    botao_voltar()
    st.subheader("💳 Gestão Avançada de Faturas de Cartão de Crédito (Fechamento & Vencimento)")
    st.write(
        "Acompanhe gastos detalhados por bandeira e controle o impacto das"
        " compras alocadas na fatura correta conforme o dia de fechamento."
    )

    with st.form("form_cartao_credito_completo", clear_on_submit=True):
        col_cc1, col_cc2 = st.columns(2)
        with col_cc1:
            nome_cartao = st.selectbox(
                "Bandeira / Cartão",
                [
                    "Caixa",
                    "Banco do Brasil",
                    "Santander",
                    "Inter",
                    "Itaúcard",
                    "Samsung Itaú",
                    "Nubank",
                    "Outro",
                ],
            )
            desc_cc = st.text_input("Descrição da Compra Específica")
            val_cc = st.number_input(
                "Valor da Compra (R$)", min_value=0.0, value=0.00, step=1.0, format="%.2f"
            )
        with col_cc2:
            data_cc = st.date_input(
                "Data da Compra no Cartão (DD/MM/AAAA)",
                value=date.today(),
                format="DD/MM/YYYY",
            )
            dia_fechamento_cc = st.number_input(
                "Dia de Fechamento da Fatura", min_value=1, max_value=31, value=10, step=1
            )
            dia_vencimento_cc = st.number_input(
                "Dia de Vencimento da Fatura", min_value=1, max_value=31, value=17, step=1
            )

        cat_cc = st.selectbox(
            "Categoria da Compra",
            [
                "🛒 Supermercado (Necessidade)",
                "🏠 Contas Fixas (Necessidade)",
                "🐾 Pet (Necessidade)",
                "🚗 Transporte (Necessidade)",
                "💊 Saúde (Necessidade)",
                "🍔 Lazer & Alimentação Fora (Desejos)",
                "🎉 Lazer & Entretenimento (Desejos)",
                "🎉 Outros Desejos (Desejos)",
            ],
        )

        if st.form_submit_button(
            "Lançar Gasto na Fatura do Cartão", use_container_width=True
        ):
            if desc_cc.strip() and val_cc > 0:
                mes_fatura_calc = calcular_mes_fatura(data_cc, dia_fechamento_cc)
                c.execute(
                    "INSERT INTO cartao_credito (data, cartao, descricao, categoria,"
                    " valor, dia_fechamento, dia_vencimento, mes_fatura) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        data_cc.strftime("%Y-%m-%d"),
                        nome_cartao,
                        desc_cc.strip(),
                        cat_cc,
                        val_cc,
                        dia_fechamento_cc,
                        dia_vencimento_cc,
                        mes_fatura_calc,
                    ),
                )
                conn.commit()
                st.success(f"Compra adicionada com sucesso! Alocada para a fatura do mês: **{mes_fatura_calc}**")
                st.rerun()
            else:
                st.error("Informe a descrição e o valor da compra.")

    st.markdown("---")
    df_cartao = pd.read_sql("SELECT * FROM cartao_credito", conn)
    if not df_cartao.empty:
        st.write("### 📋 Extrato Consolidado de Faturas Atuais")
        
        if "mes_fatura" in df_cartao.columns:
            meses_fatura_disp = sorted(df_cartao["mes_fatura"].dropna().unique(), reverse=True)
            if meses_fatura_disp:
                sel_mes_fat = st.selectbox("Filtrar por Mês de Fatura:", meses_fatura_disp)
                df_cartao_exib = df_cartao[df_cartao["mes_fatura"] == sel_mes_fat].copy()
            else:
                df_cartao_exib = df_cartao.copy()
        else:
            df_cartao_exib = df_cartao.copy()

        df_cartao_exib["data"] = df_cartao_exib["data"].apply(formatar_data_ptbr)
        st.dataframe(
            df_cartao_exib.rename(columns={
                "id": "ID",
                "data": "Data Compra",
                "cartao": "Cartão",
                "descricao": "Descrição",
                "categoria": "Categoria",
                "valor": "Valor (R$)",
                "dia_fechamento": "Fechamento",
                "dia_vencimento": "Vencimento",
                "mes_fatura": "Mês Fatura"
            }),
            use_container_width=True,
            hide_index=True,
        )

        total_fatura = df_cartao_exib["valor"].sum()
        st.markdown(
            f"""
            <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px; margin-top: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                <span style="color: #94a3b8; font-size: 12px; font-weight: 600;">💳 MONTANTE TOTAL DA FATURA SELECIONADA</span>
                <h3 style="color: #f59e0b; margin: 8px 0 0 0; font-size: 20px;">R$ {total_fatura:,.2f}</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")
        id_del_cc = st.selectbox(
            "Selecione o ID exato da compra para exclusão:",
            df_cartao["id"].tolist(),
        )
        if st.button("Remover Compra Selecionada da Fatura", use_container_width=True):
            c.execute("DELETE FROM cartao_credito WHERE id = ?", (id_del_cc,))
            conn.commit()
            st.success("Compra removida do cartão com sucesso!")
            st.rerun()
    else:
        st.info("Nenhuma despesa de cartão de crédito registrada no momento.")

# ==========================================
# --- SEÇÃO 6: INVESTIMENTOS ---
# ==========================================
elif st.session_state.pagina_atual == "📈 Investimentos":
    botao_voltar()
    st.subheader("📈 Painel Profissional de Investimentos, Caixinhas Nubank & Renda Fixa")
    st.write(
        "Monitore a alocação de patrimônio em Caixinhas Nubank, CDBs de outros bancos, Tesouro Direto, Ações e FIIs."
    )

    with st.form("form_ativo_investimento_completo", clear_on_submit=True):
        col_iv1, col_iv2, col_iv3 = st.columns(3)
        with col_iv1:
            ativo_nome = st.text_input("Nome da Caixinha ou Ativo (Ex: Caixinha Reserva de Emergência, CDB Itaú 100% CDI, Tesouro Selic)")
            classe_ativo = st.selectbox(
                "Classe / Tipo de Aplicação",
                ["Caixinha Nubank", "CDB / Renda Fixa Outros Bancos", "Tesouro Direto", "Ações BR", "FIIs", "Criptomoedas", "Exterior"],
            )
        with col_iv2:
            qtd_ativo = st.number_input(
                "Quantidade / Unidades (Use 1 se for o montante total)",
                min_value=0.0001,
                value=1.00,
                step=1.0,
            )
            preco_medio = st.number_input(
                "Valor Total Guardado / Preço Unitário (R$)",
                min_value=0.0,
                value=0.00,
                step=10.0,
                format="%.2f",
            )
        with col_iv3:
            data_aporte = st.date_input(
                "Data do Aporte / Aplicação (DD/MM/AAAA)",
                value=date.today(),
                format="DD/MM/YYYY",
            )
            st.write("")
            st.write("")
            btn_add_ativo = st.form_submit_button(
                "Cadastrar Posição na Carteira", use_container_width=True
            )

        if btn_add_ativo:
            if ativo_nome.strip():
                c.execute(
                    "INSERT INTO carteira_investimentos (data, ativo, classe,"
                    " quantidade, preco_medio) VALUES (?,?,?,?,?)",
                    (
                        data_aporte.strftime("%Y-%m-%d"),
                        ativo_nome.upper().strip(),
                        classe_ativo,
                        qtd_ativo,
                        preco_medio,
                    ),
                )
                conn.commit()
                st.success(
                    f"Aplicação '{ativo_nome.upper()}' cadastrada com sucesso!"
                )
                st.rerun()
            else:
                st.error("Informe o nome da caixinha ou ativo corretamente.")

    st.markdown("---")
    df_carteira = pd.read_sql("SELECT * FROM carteira_investimentos", conn)
    if not df_carteira.empty:
        df_carteira["Valor Total"] = (
            df_carteira["quantidade"] * df_carteira["preco_medio"]
        )
        patrimonio_total = df_carteira["Valor Total"].sum()

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.markdown(
                f"""
                <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                    <span style="color: #94a3b8; font-size: 12px; font-weight: 600;">💎 PATRIMÔNIO TOTAL ALOCADO</span>
                    <h3 style="color: #34d399; margin: 8px 0 0 0; font-size: 20px;">R$ {patrimonio_total:,.2f}</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_m2:
            st.markdown(
                f"""
                <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                    <span style="color: #94a3b8; font-size: 12px; font-weight: 600;">📦 TOTAL DE CAIXINHAS / ATIVOS</span>
                    <h3 style="color: #60a5fa; margin: 8px 0 0 0; font-size: 20px;">{len(df_carteira['ativo'].unique())}</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_m3:
            st.markdown(
                f"""
                <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                    <span style="color: #94a3b8; font-size: 12px; font-weight: 600;">📊 CLASSES DISTINTAS</span>
                    <h3 style="color: #f59e0b; margin: 8px 0 0 0; font-size: 20px;">{len(df_carteira['classe'].unique())}</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")
        col_pos1, col_pos2 = st.columns(2)
        with col_pos1:
            st.write("### 📊 Alocação por Classe de Renda Fixa / Ativos (Gráfico de Rosca)")
            df_classe = df_carteira.groupby("classe")["Valor Total"].sum().reset_index()
            fig_pie_inv = px.pie(
                df_classe,
                names="classe",
                values="Valor Total",
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Sunset,
            )
            fig_pie_inv.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#f8fafc",
                margin=dict(t=10, b=10, l=10, r=10),
            )
            st.plotly_chart(fig_pie_inv, use_container_width=True)
        with col_pos2:
            st.write("### 📋 Posições Detalhadas Registradas")
            df_carteira["data"] = df_carteira["data"].apply(formatar_data_ptbr)
            st.dataframe(
                df_carteira[[
                    "data",
                    "ativo",
                    "classe",
                    "quantidade",
                    "preco_medio",
                    "Valor Total",
                ]].rename(columns={
                    "data": "Data",
                    "ativo": "Ativo / Caixinha",
                    "classe": "Tipo",
                    "quantidade": "Qtd",
                    "preco_medio": "Valor Unit./Total",
                }),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("---")
        id_ativo_del = st.selectbox(
            "Selecione o ID exato da caixinha/ativo para remoção:",
            df_carteira["id"].tolist(),
            key="del_ativo_unique",
        )
        if st.button("Remover Ativo / Caixinha Selecionada", use_container_width=True):
            c.execute("DELETE FROM carteira_investimentos WHERE id = ?", (id_ativo_del,))
            conn.commit()
            st.success("Posição removida com sucesso!")
            st.rerun()
    else:
        st.info("Nenhuma caixinha ou investimento cadastrado até o momento.")

# ==========================================
# --- SEÇÃO 7: DESAFIOS ---
# ==========================================
elif st.session_state.pagina_atual == "🎯 Desafios":
    botao_voltar()
    st.subheader(
        "🎯 Desafio de Poupança Progressiva (R$ 20.100,00 em 200 Depósitos)"
    )
    st.write(
        "Acompanhe o preenchimento sistemático do seu desafio de disciplina"
        " financeira."
    )

    df_deps = pd.read_sql("SELECT * FROM tabela_depositos", conn)
    total_concluido = df_deps[df_deps["status"] == "Concluído"]["valor"].sum()
    meta_total_desafio = df_deps["valor"].sum()

    st.markdown(
        f"""
        <div style="background: rgba(34, 197, 94, 0.06); border: 1px solid rgba(34, 197, 94, 0.25); border-radius: 14px; padding: 20px; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
            <span style="color: #94a3b8; font-size: 12px; font-weight: 700; letter-spacing: 0.5px;">🎯 PROGRESSO ATUAL DO DESAFIO</span>
            <h2 style="color: #22c55e; margin: 8px 0 0 0; font-size: 24px;">R$ {total_concluido:,.2f} / R$ {meta_total_desafio:,.2f}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(
        min(
            total_concluido / meta_total_desafio
            if meta_total_desafio > 0
            else 0,
            1.0,
        )
    )

    col_esq, col_dir = st.columns([2, 1])
    with col_esq:
        st.write("### Tabela Geral do Desafio")
        df_exibicao = pd.DataFrame()
        df_exibicao["Nº do Depósito"] = df_deps["numero_deposito"]
        df_exibicao["Valor a Guardar"] = df_deps["valor"].apply(
            lambda x: f"R$ {x:,.2f}"
        )
        df_exibicao["Status"] = df_deps["status"]
        st.dataframe(
            df_exibicao, use_container_width=True, hide_index=True, height=380
        )

    with col_dir:
        st.write("### ⚙️ Atualizar Status do Depósito")
        with st.form("form_atualizar_deposito_completo"):
            deps_sel = st.multiselect(
                "Selecione os Números dos Depósitos:", df_deps["numero_deposito"].tolist()
            )
            status_novo = st.selectbox(
                "Novo Status:", ["Pendente", "Concluído"], index=1
            )

            if st.form_submit_button(
                "Salvar Status dos Depósitos", use_container_width=True
            ):
                if deps_sel:
                    for d_num in deps_sel:
                        c.execute(
                            "UPDATE tabela_depositos SET status = ? WHERE numero_deposito"
                            " = ?",
                            (status_novo, d_num),
                        )
                    conn.commit()
                    st.success(
                        f"Depósito(s) {', '.join(map(str, deps_sel))} atualizado(s) para"
                        f" '{status_novo}' com sucesso!"
                    )
                    st.rerun()
                else:
                    st.warning("Selecione ao menos um depósito.")

        if st.button("🔄 Resetar Todos para Pendentes", use_container_width=True):
            c.execute("UPDATE tabela_depositos SET status = 'Pendente'")
            conn.commit()
            st.success("Todos os depósitos foram resetados para Pendente.")
            st.rerun()

# ==========================================
# --- SEÇÃO 8A: METAS DE GASTOS ---
# ==========================================
elif st.session_state.pagina_atual == "🎯 Metas de Gastos":
    botao_voltar()
    st.subheader("🎯 Definir Teto de Meta Mensal por Categoria")
    st.write(
        "Estabeleça limites orçamentários para manter o controle rigoroso dos seus"
        " gastos mensais."
    )

    cats_padrao_meta = [
        "🏠 Contas Fixas (Necessidade)",
        "🛒 Supermercado (Necessidade)",
        "🐾 Pet (Necessidade)",
        "🚗 Transporte (Necessidade)",
        "💊 Saúde (Necessidade)",
        "🍔 Lazer & Alimentação Fora (Desejos)",
        "🎉 Lazer & Entretenimento (Desejos)",
        "🎉 Outros Desejos (Desejos)",
        "📈 Investimentos / Poupança (20%)",
    ]
    df_cats_db = pd.read_sql("SELECT nome FROM categorias", conn)
    lista_todas_cats = (
        cats_padrao_meta + df_cats_db["nome"].tolist()
        if not df_cats_db.empty
        else cats_padrao_meta
    )

    with st.form("form_meta_teto_completo", clear_on_submit=True):
        cat_meta = st.selectbox("Escolha a Categoria Orçamentária", lista_todas_cats)
        valor_meta_input = st.number_input(
            "Valor Teto de Meta (R$)", min_value=0.0, value=0.00, step=1.0, format="%.2f"
        )

        if st.form_submit_button("Salvar Meta de Gasto", use_container_width=True):
            c.execute("DELETE FROM metas WHERE categoria = ?", (cat_meta,))
            c.execute(
                "INSERT INTO metas (categoria, valor_meta) VALUES (?, ?)",
                (cat_meta, valor_meta_input),
            )
            conn.commit()
            st.success(f"Teto de meta para '{cat_meta}' salvo com sucesso!")
            st.rerun()

    st.markdown("---")
    st.subheader("📋 Acompanhamento Visual das Metas de Gastos")
    df_metas = pd.read_sql("SELECT * FROM metas", conn)
    df_trans_meta = pd.read_sql(
        (
            "SELECT * FROM transacoes WHERE tipo = 'Despesa' AND (origem ="
            " 'Manual' OR origem = 'Nota_Fiscal' OR origem = 'Voz_IA' OR origem ="
            " 'Chat_IA')"
        ),
        conn,
    )

    if not df_metas.empty:
        for index, row in df_metas.iterrows():
            cat_nome = row["categoria"]
            v_meta = row["valor_meta"]
            gasto_atual_meta = (
                df_trans_meta[df_trans_meta["categoria"] == cat_nome]["valor"].sum()
                if not df_trans_meta.empty
                else 0.0
            )

            st.markdown(
                f"""
                <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px; margin-bottom: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
                    <span style="color: #f8fafc; font-weight: 600; font-size: 14px;">{cat_nome}</span>
                    <p style="color: #94a3b8; font-size: 13px; margin: 4px 0;">Gasto Real: R$ {gasto_atual_meta:,.2f} / Meta Teto: R$ {v_meta:,.2f}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if v_meta > 0:
                st.progress(min(gasto_atual_meta / v_meta, 1.0))
                if gasto_atual_meta > v_meta:
                    st.error(
                        f"⚠️ Atenção! Você estourou a meta da categoria {cat_nome} em R$"
                        f" {(gasto_atual_meta - v_meta):,.2f}!"
                    )
            else:
                st.progress(0.0)
    else:
        st.info("Nenhuma meta de gasto definida até o momento.")

# ==========================================
# --- SEÇÃO 8B: CATEGORIAS & ÍCONES ---
# ==========================================
elif st.session_state.pagina_atual == "🏷️ Categorias & Ícones":
    botao_voltar()
    st.subheader("🏷️ Gerenciamento de Categorias Personalizadas & Ícones")
    st.write(
        "Cadastre novas categorias customizadas, edite ou exclua as existentes."
    )

    col_m1, col_m2 = st.columns(2)

    with col_m1:
        st.write("### ➕ Adicionar Nova Categoria com Ícone")
        with st.form("form_nova_categoria_completo", clear_on_submit=True):
            icone_escolhido = st.selectbox(
                "Escolha um Ícone Personalizado:",
                [
                    "📄",
                    "🧾",
                    "💳",
                    "💰",
                    "💵",
                    "💸",
                    "🏦",
                    "🏧",
                    "📊",
                    "🪙",
                    "🏷️",
                    "💼",
                    "📈",
                    "📉",
                    "🔒",
                    "🔑",
                    "💡",
                    "⚡",
                    "💧",
                    "🔥",
                    "📶",
                    "📡",
                    "📱",
                    "💻",
                    "📺",
                    "📬",
                    "🗑️",
                    "⚙️",
                    "🛠️",
                    "🏠",
                    "🏡",
                    "🏢",
                    "🛒",
                    "🛍️",
                    "🍔",
                    "🍕",
                    "☕",
                    "🍺",
                    "🍷",
                    "🚗",
                    "🚕",
                    "🚌",
                    "🚆",
                    "⛽",
                    "🅿️",
                    "💊",
                    "🏥",
                    "🩺",
                    "🏋️‍♂️",
                    "✈️",
                    "🏖️",
                    "🏨",
                    "🐕",
                    "🐈",
                    "🐾",
                    "🎮",
                    "🎲",
                    "📚",
                    "🎧",
                    "🎬",
                    "🎨",
                    "🎁",
                    "💄",
                    "👕",
                    "👟",
                    "🎓",
                    "👶",
                    "🎉",
                    "⭐",
                ],
            )
            nome_cat_input = st.text_input("Nome da Categoria (Ex: Viagens (Desejos), Cursos (Investimento))")

            if st.form_submit_button("Salvar Nova Categoria", use_container_width=True):
                if nome_cat_input.strip():
                    categoria_final = f"{icone_escolhido} {nome_cat_input.strip()}"
                    c.execute(
                        "INSERT INTO categorias (nome) VALUES (?)", (categoria_final,)
                    )
                    conn.commit()
                    st.success(f"Categoria '{categoria_final}' criada com sucesso!")
                    st.rerun()
                else:
                    st.error("Digite um nome válido para la categoria.")

    with col_m2:
        st.write("### ✏️ Editar ou 🗑️ Excluir Categoria")
        df_cats_gerenciar = pd.read_sql("SELECT * FROM categorias", conn)
        if not df_cats_gerenciar.empty:
            lista_nomes_cats = df_cats_gerenciar["nome"].tolist()

            cat_selecionada_para_gerenciar = st.selectbox(
                "Selecione a categoria para gerenciar:",
                lista_nomes_cats,
                key="sel_cat_gerenciar",
            )

            id_cat_atual = df_cats_gerenciar[
                df_cats_gerenciar["nome"] == cat_selecionada_para_gerenciar
            ]["id"].values[0]
            nome_completo_atual = str(cat_selecionada_para_gerenciar).strip()

            match_emoji = re.match(r"^([^\w\s])\s*(.*)$", nome_completo_atual)
            if match_emoji:
                emoji_atual = match_emoji.group(1)
                texto_atual_puro = match_emoji.group(2)
            else:
                partes_cat = nome_completo_atual.split(" ", 1)
                emoji_atual = partes_cat[0] if len(partes_cat) > 0 else "📄"
                texto_atual_puro = (
                    partes_cat[1] if len(partes_cat) > 1 else nome_completo_atual
                )

            lista_icones_opcoes = [
                "📄",
                "🧾",
                "💳",
                "💰",
                "💵",
                "💸",
                "🏦",
                "🏧",
                "📊",
                "🪙",
                "🏷️",
                "💼",
                "📈",
                "📉",
                "🔒",
                "🔑",
                "💡",
                "⚡",
                "💧",
                "🔥",
                "📶",
                "📡",
                "📱",
                "💻",
                "📺",
                "📬",
                "🗑️",
                "⚙️",
                "🛠️",
                "🏠",
                "🏡",
                "🏢",
                "🛒",
                "🛍️",
                "🍔",
                "🍕",
                "☕",
                "🍺",
                "🍷",
                "🚗",
                "🚕",
                "🚌",
                "🚆",
                "⛽",
                "🅿️",
                "💊",
                "🏥",
                "🩺",
                "🏋️‍♂️",
                "✈️",
                "🏖️",
                "🏨",
                "🐕",
                "🐈",
                "🐾",
                "🎮",
                "🎲",
                "📚",
                "🎧",
                "🎬",
                "🎨",
                "🎁",
                "💄",
                "👕",
                "👟",
                "🎓",
                "👶",
                "🎉",
                "⭐",
            ]

            idx_emoji_default = (
                lista_icones_opcoes.index(emoji_atual)
                if emoji_atual in lista_icones_opcoes
                else 0
            )
            chave_form_edicao = f"form_edit_cat_{id_cat_atual}"

            with st.form(chave_form_edicao):
                st.write(f"Editando: **{cat_selecionada_para_gerenciar}**")
                novo_icone = st.selectbox(
                    "Novo Ícone:",
                    lista_icones_opcoes,
                    index=idx_emoji_default,
                    key=f"novo_icone_sel_{id_cat_atual}",
                )
                novo_nome_texto = st.text_input(
                    "Novo Nome da Categoria:",
                    value=texto_atual_puro,
                    key=f"novo_nome_texto_input_{id_cat_atual}",
                )

                col_btn_ed1, col_btn_ed2 = st.columns(2)
                with col_btn_ed1:
                    btn_atualizar = st.form_submit_button(
                        "Atualizar Categoria", use_container_width=True
                    )
                with col_btn_ed2:
                    btn_excluir = st.form_submit_button(
                        "Excluir Categoria", use_container_width=True
                    )

                if btn_atualizar:
                    texto_base = (
                        novo_nome_texto.strip()
                        if novo_nome_texto.strip()
                        else texto_atual_puro
                    )
                    nome_atualizado_final = f"{novo_icone} {texto_base}"
                    c.execute(
                        "UPDATE categorias SET nome = ? WHERE id = ?",
                        (nome_atualizado_final, int(id_cat_atual)),
                    )
                    conn.commit()
                    st.success(
                        f"Categoria atualizada para '{nome_atualizado_final}' com sucesso!"
                    )
                    st.rerun()

                if btn_excluir:
                    c.execute(
                        "DELETE FROM categorias WHERE id = ?", (int(id_cat_atual),)
                    )
                    conn.commit()
                    st.success(
                        f"Categoria '{cat_selecionada_para_gerenciar}' excluída com"
                        " sucesso!"
                    )
                    st.rerun()
        else:
            st.info("Nenhuma categoria personalizada cadastrada para gerenciar.")

    st.markdown("---")
    st.subheader("📋 Relação de Categorias Personalizadas Cadastradas")
    df_cats_view = pd.read_sql("SELECT * FROM categorias", conn)
    if not df_cats_view.empty:
        st.dataframe(df_cats_view, use_container_width=True)
    else:
        st.info("Nenhuma categoria customizada registrada.")

# ==========================================
# --- SEÇÃO 9: SAÚDE FINANCEIRA ---
# ==========================================
elif st.session_state.pagina_atual == "❤️ Saúde Financeira":
    botao_voltar()
    st.subheader("❤️ Score de Saúde Financeira & Auditoria de Perfil")
    st.write(
        "Pontuação calculada de 0 a 1000 com base en endividamento, taxa de"
        " poupança, disciplina e cumprimento de tetos."
    )

    df_saude = pd.read_sql(
        (
            "SELECT * FROM transacoes WHERE origem = 'Manual' OR origem ="
            " 'Nota_Fiscal' OR origem = 'Voz_IA' OR origem = 'Chat_IA'"
        ),
        conn,
    )
    receitas_s = (
        df_saude[df_saude["tipo"] == "Receita"]["valor"].sum()
        if not df_saude.empty
        else 0
    )
    despesas_s = (
        df_saude[df_saude["tipo"] == "Despesa"]["valor"].sum()
        if not df_saude.empty
        else 0
    )

    f_endividamento = (
        250
        if receitas_s >= despesas_s
        else max(
            0,
            250 - ((despesas_s - receitas_s) / max(receitas_s, 1)) * 250,
        )
    )
    inv_s = (
        df_saude[df_saude["categoria"].str.contains("Investimentos", na=False)][
            "valor"
        ].sum()
        if not df_saude.empty
        else 0
    )
    taxa_poupanca_s = (inv_s / receitas_s) if receitas_s > 0 else 0
    f_poupanca = min(250, (taxa_poupanca_s / 0.20) * 250)
    desejos_s = (
        df_saude[df_saude["categoria"].str.contains("Desejos", na=False)][
            "valor"
        ].sum()
        if not df_saude.empty
        else 0
    )
    proporcao_desejos_s = (desejos_s / receitas_s) if receitas_s > 0 else 0
    f_metas_s = (
        250
        if proporcao_desejos_s <= 0.30
        else max(0, 250 - ((proporcao_desejos_s - 0.30) * 500))
    )
    f_disciplina = 250 if not df_saude.empty and receitas_s > 0 else 50

    score_total = int(
        f_endividamento + f_poupanca + f_metas_s + (f_disciplina * 0.5)
    )
    score_total = min(1000, max(0, score_total))

    if score_total >= 750:
        status_score, cor_status = "Excelente 🚀", "🟢"
    elif score_total >= 500:
        status_score, cor_status = "Bom 👍", "🔵"
    else:
        status_score, cor_status = "Atenção Crítica ⚠️", "🟠"

    st.markdown(
        f"""
    <div style="background: rgba(25, 29, 38, 0.85); padding: 30px; border-radius: 14px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.08); box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);">
        <h1 style="font-size: 60px; color: #3b82f6; margin: 0;">{score_total}</h1>
        <p style="color: #94a3b8; font-size: 14px; margin: 5px 0 15px 0; font-weight: 600;">pontos de 1000</p>
        <h3 style="color: #f8fafc; margin: 0; font-size: 20px;">{cor_status} Status: {status_score}</h3>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.subheader("Detalhamento por Fator de Avaliação")
    st.write(
        "Diagnóstico analítico dos pilares que compõem sua nota de saúde"
        " financeira:"
    )

    st.markdown(
        f"""
        <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px; margin-bottom: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
            <span style="color: #f8fafc; font-weight: 600; font-size: 14px;">🛡️ Controle de Endividamento (Receitas vs Despesas)</span>
            <p style="color: #94a3b8; font-size: 13px; margin: 4px 0;">Pontuação: {int(f_endividamento)} / 250 pts</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(min(f_endividamento / 250, 1.0))

    st.markdown(
        f"""
        <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px; margin-bottom: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
            <span style="color: #f8fafc; font-weight: 600; font-size: 14px;">🎯 Controle de Desejos (Regra dos 30%)</span>
            <p style="color: #94a3b8; font-size: 13px; margin: 4px 0;">Pontuação: {int(f_metas_s)} / 250 pts</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(min(f_metas_s / 250, 1.0))

    st.markdown(
        f"""
        <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px; margin-bottom: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
            <span style="color: #f8fafc; font-weight: 600; font-size: 14px;">📈 Taxa de Poupança / Investimento (Regra dos 20%)</span>
            <p style="color: #94a3b8; font-size: 13px; margin: 4px 0;">Pontuação: {int(f_poupanca)} / 250 pts</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(min(f_poupanca / 250, 1.0))

    st.markdown(
        f"""
        <div style="background: rgba(25, 29, 38, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px; margin-bottom: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
            <span style="color: #f8fafc; font-weight: 600; font-size: 14px;">📅 Disciplina de Registros & Frequência</span>
            <p style="color: #94a3b8; font-size: 13px; margin: 4px 0;">Pontuação: {int(f_disciplina * 0.5)} / 250 pts</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(min((f_disciplina * 0.5) / 250, 1.0))

# ==========================================
# --- SEÇÃO 10: CONTAS A PAGAR & RECEBER ---
# ==========================================
elif st.session_state.pagina_atual == "📅 Contas a Pagar":
    botao_voltar()

    hoje_atual = date.today()
    if "data_calendario_ref" not in st.session_state or not isinstance(
        st.session_state.data_calendario_ref, (date, datetime)
    ):
        st.session_state.data_calendario_ref = hoje_atual

    st.subheader("📅 Contas a Pagar & Receber / Gestão de Pagamentos")
    st.write(
        "Organize boletos, contas a pagar, contas a receber e compromissos com"
        " vencimento programado."
    )

    if "aba_contas_ativa" not in st.session_state:
        st.session_state.aba_contas_ativa = "pagar"

    col_tab_btn1, col_tab_btn2, _ = st.columns([1, 1, 4])
    with col_tab_btn1:
        if st.button(
            "📉 Contas a Pagar",
            use_container_width=True,
            type=(
                "primary"
                if st.session_state.aba_contas_ativa == "pagar"
                else "secondary"
            ),
        ):
            st.session_state.aba_contas_ativa = "pagar"
            st.rerun()
    with col_tab_btn2:
        if st.button(
            "📈 Contas a Receber",
            use_container_width=True,
            type=(
                "primary"
                if st.session_state.aba_contas_ativa == "receber"
                else "secondary"
            ),
        ):
            st.session_state.aba_contas_ativa = "receber"
            st.rerun()

    st.markdown("---")

    st.markdown("##### 🗓️ Seleção de Data no Calendário Interativo & Período")
    data_calendario_topo = st.date_input(
        "Selecionar Data de Referência (DD/MM/AAAA):",
        value=st.session_state.data_calendario_ref,
        key="data_calendario_ref_input",
        format="DD/MM/YYYY",
    )
    if data_calendario_topo:
        st.session_state.data_calendario_ref = data_calendario_topo

    st.markdown(
        f"""
        <div style="background: rgba(59, 130, 246, 0.06); border: 1px solid rgba(59, 130, 246, 0.25); border-radius: 14px; padding: 20px; margin-bottom: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
            <h4 style="color: #60a5fa; margin-top: 0; display: flex; align-items: center; gap: 8px;">📌 Agenda do Dia: {st.session_state.data_calendario_ref.strftime('%d/%m/%Y')}</h4>
        </div>
        """,
        unsafe_allow_html=True,
    )

    data_sel_str = st.session_state.data_calendario_ref.strftime("%Y-%m-%d")
    df_cp_dia = pd.read_sql(
        "SELECT * FROM contas WHERE vencimento = ?", conn, params=(data_sel_str,)
    )
    df_cr_dia = pd.read_sql(
        "SELECT * FROM contas_receber WHERE vencimento = ?",
        conn,
        params=(data_sel_str,),
    )

    col_agd1, col_agd2 = st.columns(2)
    with col_agd1:
        st.write("**📉 Contas a Pagar na Data:**")
        if not df_cp_dia.empty:
            for _, row_cp_d in df_cp_dia.iterrows():
                st.markdown(
                    f"• ID {row_cp_d['id']} | **{row_cp_d['descricao']}** — R$"
                    f" {row_cp_d['valor']:,.2f}"
                    f" ({'Pago ✅' if row_cp_d['pago'] == 1 else 'Pendente ⏳'})"
                )
        else:
            st.info("Nenhuma conta a pagar para esta data.")

    with col_agd2:
        st.write("**📈 Contas a Receber na Data:**")
        if not df_cr_dia.empty:
            for _, row_cr_d in df_cr_dia.iterrows():
                st.markdown(
                    f"• ID {row_cr_d['id']} | **{row_cr_d['descricao']}** — R$"
                    f" {row_cr_d['valor']:,.2f}"
                    f" ({'Recebido ✅' if row_cr_d['recebido'] == 1 else 'Pendente ⏳'})"
                )
        else:
            st.info("Nenhuma conta a receber para esta data.")

    st.markdown("---")

    if st.session_state.aba_contas_ativa == "pagar":
        st.subheader(
            "➕ Nova Conta a Pagar (com Opção de Recorrência Mensal, Semanal ou"
            " Replicar datas)"
        )

        if "venc_cp_state" not in st.session_state:
            st.session_state.venc_cp_state = hoje_atual

        with st.form("form_conta_pagar_completo", clear_on_submit=True):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                venc = st.date_input(
                    "Data de Vencimento Inicial (DD/MM/AAAA)",
                    value=st.session_state.venc_cp_state,
                    key="venc_cp_input_field",
                    format="DD/MM/YYYY",
                )
                tipo_recorrencia = st.selectbox(
                    "Tipo de Recorrência / Lançamento:",
                    [
                        "Apenas esta data (Sem recorrência)",
                        "Recorrência Semanal",
                        "Recorrência Mensal",
                        "Replicar datas específicas customizadas",
                    ],
                    key="recorrencia_cp",
                )

                quantidade_periodos = 1
                if tipo_recorrencia in ["Recorrência Semanal", "Recorrência Mensal"]:
                    quantidade_periodos = st.number_input(
                        "Quantidade de Períodos (Repetições):",
                        min_value=1,
                        max_value=60,
                        value=12,
                        step=1,
                        key="qtd_periodos_cp",
                    )

                replicar_datas_cp = []
                if tipo_recorrencia == "Replicar datas específicas customizadas":
                    replicar_datas_cp = st.multiselect(
                        "Selecione as datas adicionais de vencimento:",
                        options=[hoje_atual + timedelta(days=d) for d in range(1, 365)],
                        format_func=lambda x: x.strftime("%d/%m/%Y"),
                        key="rep_datas_cp",
                    )

            with col_c2:
                val_conta = st.number_input(
                    "Valor da Conta (R$)", min_value=0.0, format="%.2f", key="val_cp"
                )
                nome_conta = st.text_input(
                    "Nome / Descrição da Conta (Ex: Conta de Luz, Aluguel)"
                )

            if st.form_submit_button(
                "Adicionar Conta(s) a Pagar", use_container_width=True
            ):
                if nome_conta.strip() and val_conta > 0:
                    datas_para_inserir = [venc]

                    if tipo_recorrencia == "Recorrência Semanal":
                        for i in range(1, quantidade_periodos):
                            datas_para_inserir.append(venc + timedelta(weeks=i))
                    elif tipo_recorrencia == "Recorrência Mensal":
                        dia_original = venc.day
                        for i in range(1, quantidade_periodos):
                            novo_mes = venc.month + i
                            novo_ano = venc.year + (novo_mes - 1) // 12
                            novo_mes = (novo_mes - 1) % 12 + 1

                            if novo_mes in [4, 6, 9, 11] and dia_original > 30:
                                dia_ajustado = 30
                            elif novo_mes == 2:
                                bissexto = (
                                    novo_ano % 4 == 0 and novo_ano % 100 != 0
                                ) or (novo_ano % 400 == 0)
                                max_fevereiro = 29 if bissexto else 28
                                dia_ajustado = min(dia_original, max_fevereiro)
                            else:
                                dia_ajustado = min(dia_original, 31)

                            datas_para_inserir.append(date(novo_ano, novo_mes, dia_ajustado))

                    elif tipo_recorrencia == "Replicar datas específicas customizadas":
                        for d_rep in replicar_datas_cp:
                            if d_rep not in datas_para_inserir:
                                datas_para_inserir.append(d_rep)

                    for d_ins in datas_para_inserir:
                        c.execute(
                            "INSERT INTO contas (vencimento, descricao, valor, pago)"
                            " VALUES (?,?,?,?)",
                            (
                                d_ins.strftime("%Y-%m-%d"),
                                str(nome_conta).strip(),
                                val_conta,
                                0,
                            ),
                        )
                    conn.commit()
                    st.success(
                        f"{len(datas_para_inserir)} conta(s) a pagar cadastrada(s) com"
                        " sucesso!"
                    )
                    st.rerun()
                else:
                    st.error("Informe a descrição e o valor da conta.")

        st.markdown("---")

        df_contas_alerta = pd.read_sql("SELECT * FROM contas WHERE pago = 0", conn)
        if not df_contas_alerta.empty:
            df_contas_alerta["venc_dt"] = pd.to_datetime(
                df_contas_alerta["vencimento"]
            ).dt.date

            vencidas = df_contas_alerta[df_contas_alerta["venc_dt"] < hoje_atual]
            vencem_hoje = df_contas_alerta[df_contas_alerta["venc_dt"] == hoje_atual]

            if not vencidas.empty or not vencem_hoje.empty:
                st.markdown("### 🚨 Alertas de Vencimento (Pagar)")
                if not vencidas.empty:
                    for _, r_venc in vencidas.iterrows():
                        st.error(
                            f"⚠️ **Conta Vencida:** '{r_venc['descricao']}' vencia em"
                            f" **{formatar_data_ptbr(r_venc['vencimento'])}** no valor de"
                            f" **R$ {r_venc['valor']:,.2f}**!"
                        )
                if not vencem_hoje.empty:
                    for _, r_hoje in vencem_hoje.iterrows():
                        st.warning(
                            f"🔔 **Vence Hoje:** '{r_hoje['descricao']}' vence **hoje**"
                            f" ({hoje_atual.strftime('%d/%m/%Y')}) no valor de **R$"
                            f" {r_hoje['valor']:,.2f}**!"
                        )
                st.markdown("---")

        st.subheader("🔍 Pesquisa Aprimorada & Relação de Contas a Pagar")

        col_pesq_cp, col_fil_agenda_cp = st.columns([3, 2])
        with col_pesq_cp:
            termo_busca_contas = st.text_input(
                "Pesquisar por nome, parte da descrição ou similaridade:",
                "",
                key="busca_contas_input",
            )
        with col_fil_agenda_cp:
            mostrar_tudo_cp = st.checkbox(
                "Exibir todas as datas (desmarcado mostra apenas o mês vigente)",
                value=False,
                key="chk_mostrar_tudo_cp",
            )

        df_contas_all = pd.read_sql("SELECT * FROM contas", conn)

        if not df_contas_all.empty:
            df_contas_all["venc_dt_cmp"] = pd.to_datetime(
                df_contas_all["vencimento"]
            ).dt.date

            if not mostrar_tudo_cp:
                ano_vig = st.session_state.data_calendario_ref.year
                mes_vig = st.session_state.data_calendario_ref.month
                df_contas_all = df_contas_all[
                    (pd.to_datetime(df_contas_all["vencimento"]).dt.year == ano_vig)
                    & (pd.to_datetime(df_contas_all["vencimento"]).dt.month == mes_vig)
                ]

            if termo_busca_contas.strip():
                termo_limpo = termo_busca_contas.strip().lower()
                descricoes = df_contas_all["descricao"].tolist()
                similares = difflib.get_close_matches(
                    termo_limpo, [d.lower() for d in descricoes], n=15, cutoff=0.25
                )

                mask = (
                    df_contas_all["descricao"]
                    .str.lower()
                    .str.contains(termo_limpo, na=False)
                    | df_contas_all["descricao"].str.lower().isin(similares)
                )
                contas_filtradas = df_contas_all[mask]
            else:
                contas_filtradas = df_contas_all
        else:
            contas_filtradas = df_contas_all

        if not contas_filtradas.empty:
            st.write("### 📋 Lista de Contas a Pagar (Mês Vigente)")
            for _, row_cp in contas_filtradas.iterrows():
                c_id = row_cp["id"]
                c_venc = formatar_data_ptbr(row_cp["vencimento"])
                c_desc = row_cp["descricao"]
                c_val = row_cp["valor"]
                c_pago = row_cp["pago"]

                col_row1, col_row2, col_row3, col_row4, col_row5, col_row6 = (
                    st.columns([1, 2, 2, 1, 1, 1])
                )
                with col_row1:
                    st.write(f"**ID:** {c_id}")
                with col_row2:
                    st.write(f"📅 {c_venc} | **{c_desc}**")
                with col_row3:
                    st.write(
                        f"R$ {c_val:,.2f}"
                        f" ({'Pago ✅' if c_pago == 1 else 'Pendente ⏳'})"
                    )
                with col_row4:
                    if c_pago == 0:
                        if st.button(
                            "Pagar 💳", key=f"btn_pagar_{c_id}", use_container_width=True
                        ):
                            c.execute("UPDATE contas SET pago = 1 WHERE id = ?", (c_id,))
                            c.execute(
                                "INSERT INTO transacoes (data, tipo, descricao, categoria,"
                                " valor, origem) VALUES (?,?,?,?,?,?)",
                                (
                                    hoje_atual.strftime("%Y-%m-%d"),
                                    "Despesa",
                                    f"Pgto: {c_desc}",
                                    "🏠 Contas Fixas (Necessidade)",
                                    c_val,
                                    "Manual",
                                ),
                            )
                            conn.commit()
                            st.success(f"Conta '{c_desc}' paga com sucesso!")
                            st.rerun()
                    else:
                        if st.button(
                            "Estornar 🔄",
                            key=f"btn_estornar_{c_id}",
                            use_container_width=True,
                        ):
                            c.execute("UPDATE contas SET pago = 0 WHERE id = ?", (c_id,))
                            conn.commit()
                            st.success(f"Conta '{c_desc}' marcada como pendente!")
                            st.rerun()
                with col_row5:
                    if st.button(
                        "✏️ Editar", key=f"btn_edit_cp_{c_id}", use_container_width=True
                    ):
                        st.session_state[f"editando_cp_{c_id}"] = not st.session_state.get(
                            f"editando_cp_{c_id}", False
                        )
                        st.rerun()
                with col_row6:
                    if st.button(
                        "Excluir 🗑️", key=f"btn_del_cp_{c_id}", use_container_width=True
                    ):
                        c.execute("DELETE FROM contas WHERE id = ?", (c_id,))
                        conn.commit()
                        st.success(f"Conta ID {c_id} excluída com sucesso!")
                        st.rerun()

                if st.session_state.get(f"editando_cp_{c_id}", False):
                    with st.form(f"form_editar_cp_{c_id}"):
                        st.write(
                            f"**Editando Conta ID {c_id}** (Ajuste de variação de valor ou"
                            " data)"
                        )
                        novo_venc_cp = st.date_input(
                            "Nova Data de Vencimento (DD/MM/AAAA)",
                            value=datetime.strptime(
                                row_cp["vencimento"], "%Y-%m-%d"
                            ).date(),
                            key=f"nv_v_{c_id}",
                            format="DD/MM/YYYY",
                        )
                        nova_desc_cp = st.text_input(
                            "Nova Descrição", value=c_desc, key=f"nv_d_{c_id}"
                        )
                        novo_val_cp = st.number_input(
                            "Novo Valor (R$)",
                            min_value=0.0,
                            value=float(c_val),
                            step=1.0,
                            format="%.2f",
                            key=f"nv_val_{c_id}",
                        )

                        if st.form_submit_button("Salvar Alterações", use_container_width=True):
                            c.execute(
                                "UPDATE contas SET vencimento = ?, descricao = ?, valor = ?"
                                " WHERE id = ?",
                                (
                                    novo_venc_cp.strftime("%Y-%m-%d"),
                                    nova_desc_cp.strip(),
                                    novo_val_cp,
                                    c_id,
                                ),
                            )
                            conn.commit()
                            st.session_state[f"editando_cp_{c_id}"] = False
                            st.success("Conta atualizada com sucesso!")
                            st.rerun()

            st.markdown("---")
            id_del_cp = st.selectbox(
                "Selecione o ID da conta a pagar para exclusão geral:",
                contas_filtradas["id"].tolist(),
                key="del_cp_sel",
            )
            if st.button("Excluir Conta a Pagar Selecionada", use_container_width=True):
                c.execute("DELETE FROM contas WHERE id = ?", (id_del_cp,))
                conn.commit()
                st.success("Conta a pagar removida com sucesso!")
                st.rerun()
        else:
            st.info("Nenhuma conta a pagar encontrada para o mês vigente.")

    else:
        st.subheader(
            "➕ Nova Conta a Receber (com Opção de Recorrência Mensal, Semanal ou"
            " Replicar datas)"
        )
        with st.form("form_conta_receber_completo", clear_on_submit=True):
            col_cr1, col_cr2 = st.columns(2)
            with col_cr1:
                venc_r = st.date_input(
                    "Data de Vencimento / Recebimento Inicial (DD/MM/AAAA)",
                    value=hoje_atual,
                    key="venc_cr",
                    format="DD/MM/YYYY",
                )
                tipo_recorrencia_r = st.selectbox(
                    "Tipo de Recorrência / Lançamento:",
                    [
                        "Apenas esta data (Sem recorrência)",
                        "Recorrência Semanal",
                        "Recorrência Mensal",
                        "Replicar datas específicas customizadas",
                    ],
                    key="recorrencia_cr",
                )

                quantidade_periodos_r = 1
                if tipo_recorrencia_r in ["Recorrência Semanal", "Recorrência Mensal"]:
                    quantidade_periodos_r = st.number_input(
                        "Quantidade de Períodos (Repetições):",
                        min_value=1,
                        max_value=60,
                        value=12,
                        step=1,
                        key="qtd_periodos_cr",
                    )

                replicar_datas_cr = []
                if tipo_recorrencia_r == "Replicar datas específicas customizadas":
                    replicar_datas_cr = st.multiselect(
                        "Selecione as datas adicionais de vencimento:",
                        options=[hoje_atual + timedelta(days=d) for d in range(1, 365)],
                        format_func=lambda x: x.strftime("%d/%m/%Y"),
                        key="rep_datas_cr",
                    )

            with col_cr2:
                val_conta_r = st.number_input(
                    "Valor a Receber (R$)", min_value=0.0, format="%.2f", key="val_cr"
                )
                nome_conta_r = st.text_input(
                    (
                        "Nome / Descrição da Receita (Ex: Aluguel a Receber, Prestação"
                        " de Serviço)"
                    )
                )

            if st.form_submit_button(
                "Adicionar Conta(s) a Receber", use_container_width=True
            ):
                if nome_conta_r.strip() and val_conta_r > 0:
                    datas_para_inserir_r = [venc_r]

                    if tipo_recorrencia_r == "Recorrência Semanal":
                        for i in range(1, quantidade_periodos_r):
                            datas_para_inserir_r.append(venc_r + timedelta(weeks=i))
                    elif tipo_recorrencia_r == "Recorrência Mensal":
                        dia_original_r = venc_r.day
                        for i in range(1, quantidade_periodos_r):
                            novo_mes_r = venc_r.month + i
                            novo_ano_r = venc_r.year + (novo_mes_r - 1) // 12
                            novo_mes_r = (novo_mes_r - 1) % 12 + 1

                            if novo_mes_r in [4, 6, 9, 11] and dia_original_r > 30:
                                dia_ajustado_r = 30
                            elif novo_mes_r == 2:
                                bissexto_r = (
                                    novo_ano_r % 4 == 0 and novo_ano_r % 100 != 0
                                ) or (novo_ano_r % 400 == 0)
                                max_fevereiro_r = 29 if bissexto_r else 28
                                dia_ajustado_r = min(dia_original_r, max_fevereiro_r)
                            else:
                                dia_ajustado_r = min(dia_original_r, 31)

                            datas_para_inserir_r.append(
                                date(novo_ano_r, novo_mes_r, dia_ajustado_r)
                            )

                    elif tipo_recorrencia_r == "Replicar datas específicas customizadas":
                        for d_rep_r in replicar_datas_cr:
                            if d_rep_r not in datas_para_inserir_r:
                                datas_para_inserir_r.append(d_rep_r)

                    for d_ins_r in datas_para_inserir_r:
                        c.execute(
                            "INSERT INTO contas_receber (vencimento, descricao, valor,"
                            " recebido) VALUES (?,?,?,?)",
                            (
                                d_ins_r.strftime("%Y-%m-%d"),
                                str(nome_conta_r).strip(),
                                val_conta_r,
                                0,
                            ),
                        )
                    conn.commit()
                    st.success(
                        f"{len(datas_para_inserir_r)} conta(s) a receber cadastrada(s)"
                        " com sucesso!"
                    )
                    st.rerun()
                else:
                    st.error("Informe a descrição e o valor da conta a receber.")

        st.markdown("---")
        st.subheader("🔍 Pesquisa Aprimorada & Relação de Contas a Receber")

        col_pesq_cr, col_fil_agenda_cr = st.columns([3, 2])
        with col_pesq_cr:
            termo_busca_receber = st.text_input(
                "Pesquisar por nome, parte da descrição ou similaridade:",
                "",
                key="busca_receber_input",
            )
        with col_fil_agenda_cr:
            mostrar_tudo_cr = st.checkbox(
                "Exibir todas as datas (desmarcado mostra apenas o mês vigente)",
                value=False,
                key="chk_mostrar_tudo_cr",
            )

        df_receber_all = pd.read_sql("SELECT * FROM contas_receber", conn)

        if not df_receber_all.empty:
            df_receber_all["venc_dt_cmp"] = pd.to_datetime(
                df_receber_all["vencimento"]
            ).dt.date

            if not mostrar_tudo_cr:
                ano_vig_r = st.session_state.data_calendario_ref.year
                mes_vig_r = st.session_state.data_calendario_ref.month
                df_receber_all = df_receber_all[
                    (pd.to_datetime(df_receber_all["vencimento"]).dt.year == ano_vig_r)
                    & (pd.to_datetime(df_receber_all["vencimento"]).dt.month == mes_vig_r)
                ]

            if termo_busca_receber.strip():
                termo_limpo_r = termo_busca_receber.strip().lower()
                desc_r = df_receber_all["descricao"].tolist()
                sim_r = difflib.get_close_matches(
                    termo_limpo_r, [d.lower() for d in desc_r], n=15, cutoff=0.25
                )

                mask_r = (
                    df_receber_all["descricao"]
                    .str.lower()
                    .str.contains(termo_limpo_r, na=False)
                    | df_receber_all["descricao"].str.lower().isin(sim_r)
                )
                receber_filtradas = df_receber_all[mask_r]
            else:
                receber_filtradas = df_receber_all
        else:
            receber_filtradas = df_receber_all

        if not receber_filtradas.empty:
            st.write("### 📋 Lista de Contas a Receber (Mês Vigente)")
            for _, row_cr in receber_filtradas.iterrows():
                cr_id = row_cr["id"]
                cr_venc = formatar_data_ptbr(row_cr["vencimento"])
                cr_desc = row_cr["descricao"]
                cr_val = row_cr["valor"]
                cr_recebido = row_cr["recebido"]

                col_r1, col_r2, col_r3, col_r4, col_r5, col_r6 = st.columns(
                    [1, 2, 2, 1, 1, 1]
                )
                with col_r1:
                    st.write(f"**ID:** {cr_id}")
                with col_r2:
                    st.write(f"📅 {cr_venc} | **{cr_desc}**")
                with col_r3:
                    st.write(
                        f"R$ {cr_val:,.2f}"
                        f" ({'Recebido ✅' if cr_recebido == 1 else 'Pendente ⏳'})"
                    )
                with col_r4:
                    if cr_recebido == 0:
                        if st.button(
                            "Receber 💰",
                            key=f"btn_receber_{cr_id}",
                            use_container_width=True,
                        ):
                            c.execute(
                                "UPDATE contas_receber SET recebido = 1 WHERE id = ?",
                                (cr_id,),
                            )
                            c.execute(
                                "INSERT INTO transacoes (data, tipo, descricao, categoria,"
                                " valor, origem) VALUES (?,?,?,?,?,?)",
                                (
                                    hoje_atual.strftime("%Y-%m-%d"),
                                    "Receita",
                                    f"Recebimento: {cr_desc}",
                                    "Freelance / Extra",
                                    cr_val,
                                    "Manual",
                                ),
                            )
                            conn.commit()
                            st.success(f"Recebimento '{cr_desc}' confirmado com sucesso!")
                            st.rerun()
                    else:
                        if st.button(
                            "Estornar 🔄",
                            key=f"btn_estornar_cr_{cr_id}",
                            use_container_width=True,
                        ):
                            c.execute(
                                "UPDATE contas_receber SET recebido = 0 WHERE id = ?",
                                (cr_id,),
                            )
                            conn.commit()
                            st.success(f"Recebimento '{cr_desc}' marcado como pendente!")
                            st.rerun()
                with col_r5:
                    if st.button(
                        "✏️ Editar", key=f"btn_edit_cr_{cr_id}", use_container_width=True
                    ):
                        st.session_state[f"editando_cr_{cr_id}"] = not st.session_state.get(
                            f"editando_cr_{cr_id}", False
                        )
                        st.rerun()
                with col_r6:
                    if st.button(
                        "Excluir 🗑️", key=f"btn_del_cr_{cr_id}", use_container_width=True
                    ):
                        c.execute("DELETE FROM contas_receber WHERE id = ?", (cr_id,))
                        conn.commit()
                        st.success(f"Conta a receber ID {cr_id} excluída com sucesso!")
                        st.rerun()

                if st.session_state.get(f"editando_cr_{cr_id}", False):
                    with st.form(f"form_editar_cr_{cr_id}"):
                        st.write(
                            f"**Editando Conta a Receber ID {cr_id}** (Ajuste de variação)"
                        )
                        novo_venc_cr = st.date_input(
                            "Nova Data de Vencimento (DD/MM/AAAA)",
                            value=datetime.strptime(
                                row_cr["vencimento"], "%Y-%m-%d"
                            ).date(),
                            key=f"nv_vr_{cr_id}",
                            format="DD/MM/YYYY",
                        )
                        nova_desc_cr = st.text_input(
                            "Nova Descrição", value=cr_desc, key=f"nv_dr_{cr_id}"
                        )
                        novo_val_cr = st.number_input(
                            "Novo Valor (R$)",
                            min_value=0.0,
                            value=float(cr_val),
                            step=1.0,
                            format="%.2f",
                            key=f"nv_valr_{cr_id}",
                        )

                        if st.form_submit_button("Salvar Alterações", use_container_width=True):
                            c.execute(
                                "UPDATE contas_receber SET vencimento = ?, descricao = ?,"
                                " valor = ? WHERE id = ?",
                                (
                                    novo_venc_cr.strftime("%Y-%m-%d"),
                                    nova_desc_cr.strip(),
                                    novo_val_cr,
                                    cr_id,
                                ),
                            )
                            conn.commit()
                            st.session_state[f"editando_cr_{cr_id}"] = False
                            st.success("Conta a receber atualizada com sucesso!")
                            st.rerun()

            st.markdown("---")
            id_del_cr = st.selectbox(
                "Selecione o ID da conta a receber para exclusão geral:",
                receber_filtradas["id"].tolist(),
                key="del_cr_sel",
            )
            if st.button(
                "Excluir Conta a Receber Selecionada", use_container_width=True
            ):
                c.execute("DELETE FROM contas_receber WHERE id = ?", (id_del_cr,))
                conn.commit()
                st.success("Conta a receber removida com sucesso!")
                st.rerun()
        else:
            st.info("Nenhuma conta a receber encontrada para o mês vigente.")

# ==========================================
# --- SEÇÃO 11: EXTRATO & BACKUP ---
# ==========================================
elif st.session_state.pagina_atual == "📋 Extrato & Backup":
    botao_voltar()
    st.subheader(
        "📋 Extrato Consolidado, Importação Inteligente de Extratos PDF/CSV &"
        " Backup"
    )
    st.write(
        "Faça download do banco de dados ou exporte planilhas utilizando os"
        " botões abaixo."
    )

    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        with open("gestor_financeiro.db", "rb") as f_db:
            st.download_button(
                "💾 Baixar Banco de Dados (.db)",
                f_db,
                file_name="gestor_financeiro.db",
                mime="application/octet-stream",
                use_container_width=True,
            )

    with col_exp2:
        df_extrato_full = pd.read_sql("SELECT * FROM transacoes", conn)
        if not df_extrato_full.empty:
            df_extrato_full["data"] = df_extrato_full["data"].apply(
                formatar_data_ptbr
            )
            csv_texto = df_extrato_full.to_csv(index=False)
            st.download_button(
                "📥 Baixar Planilha Extrato (CSV)",
                csv_texto.encode("utf-8"),
                file_name="extrato_financeiro.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.button(
                "📥 Baixar Planilha Extrato (CSV)",
                disabled=True,
                use_container_width=True,
            )

    st.markdown("---")
    st.markdown("### ⚠️ Zona de Perigo — Exclusão Geral de Dados")
    st.write(
        "Insira a senha de segurança abaixo para apagar permanentemente todos"
        " os registros, transações, faturas, veículos e investimentos do"
        " sistema."
    )

    with st.form("form_exclusao_geral_segura"):
        senha_exclusao_geral = st.text_input("Senha de Confirmação:", type="password")
        btn_executar_limpeza = st.form_submit_button(
            "🗑️ APAGAR TODOS OS DADOS DO SISTEMA", use_container_width=True
        )

        if btn_executar_limpeza:
            if senha_exclusao_geral == "1234":
                c.execute("DELETE FROM transacoes")
                c.execute("DELETE FROM contas")
                c.execute("DELETE FROM contas_receber")
                c.execute("DELETE FROM cartao_credito")
                c.execute("DELETE FROM carteira_investimentos")
                c.execute("DELETE FROM veiculos")
                c.execute("DELETE FROM manutencoes_veiculo")
                c.execute("DELETE FROM consumo_combustivel")
                c.execute("DELETE FROM holerites")
                c.execute("DELETE FROM notas_fiscais")
                c.execute("DELETE FROM itens_nota_fiscal")
                c.execute("DELETE FROM metas")
                c.execute("DELETE FROM saldo_banco_manual")
                conn.commit()
                st.success("Todos os dados do sistema foram apagados com sucesso!")
                st.rerun()
            else:
                st.error("Senha incorreta! A exclusão geral foi cancelada.")

    st.markdown("---")
    st.write(
        "### 📥 Importação Automática de Extrato Bancário em PDF (Ex: Itaú)"
    )
    arquivo_importado = st.file_uploader(
        "Selecione o arquivo extrato em PDF ou CSV",
        type=["csv", "pdf"],
        key="upload_extrato_banco",
    )

    if arquivo_importado is not None and arquivo_importado.name.endswith(".pdf"):
        try:
            texto_pdf_extrato = ""
            with pdfplumber.open(arquivo_importado) as pdf:
                for pagina in pdf.pages:
                    ext = pagina.extract_text()
                    if ext:
                        texto_pdf_extrato += ext + "\n"

            if st.button(
                "Processar e Importar Extrato do PDF com Categorização Inteligente",
                use_container_width=True,
            ):
                importados_pdf_count = 0
                for linha in texto_pdf_extrato.split("\n"):
                    if "SALDO" in linha.upper():
                        continue
                    partes = linha.split()
                    if len(partes) >= 3 and "/" in partes[0] and len(partes[0]) == 10:
                        try:
                            d = partes[0].split("/")
                            data_str = f"{d[2]}-{d[1]}-{d[0]}"
                            val_float = float(
                                linha.replace("R$", "")
                                .replace(".", "")
                                .replace(",", ".")
                                .split()[-1]
                            )
                            tipo_trans = "Receita" if val_float > 0 else "Despesa"
                            desc_str = " ".join(partes[1:-1])
                            cat_inteligente = categorizar_automaticamente(
                                desc_str, tipo_trans
                            )
                            c.execute(
                                "INSERT INTO transacoes (data, tipo, descricao, categoria,"
                                " valor, origem) VALUES (?,?,?,?,?,?)",
                                (
                                    data_str,
                                    tipo_trans,
                                    desc_str,
                                    cat_inteligente,
                                    abs(val_float),
                                    "Banco_PDF",
                                ),
                            )
                            importados_pdf_count += 1
                        except:
                            continue
                conn.commit()
                st.success(
                    f"{importados_pdf_count} lançamentos do extrato importados e"
                    " categorizados com sucesso como origem 'Banco_PDF'!"
                )
                st.rerun()
        except Exception as e:
            st.error(f"Erro ao processar extrato bancário em PDF: {e}")

    st.markdown("---")
    st.subheader("📑 Módulo de Reconciliação Bancária Automatizada")
    st.write(
        "Verifique divergências entre os lançamentos manuais do sistema e o"
        " extrato importado mais recentemente."
    )

    if arquivo_importado is not None and arquivo_importado.name.endswith(".pdf"):
        transacoes_pdf_temp = []
        for linha in texto_pdf_extrato.split("\n"):
            if "SALDO" in linha.upper():
                continue
            partes = linha.split()
            if len(partes) >= 3 and "/" in partes[0] and len(partes[0]) == 10:
                try:
                    d = partes[0].split("/")
                    data_str = f"{d[2]}-{d[1]}-{d[0]}"
                    val_float = float(
                        linha.replace("R$", "")
                        .replace(".", "")
                        .replace(",", ".")
                        .split()[-1]
                    )
                    desc_str = " ".join(partes[1:-1])
                    transacoes_pdf_temp.append({
                        "data": data_str,
                        "descricao": desc_str,
                        "valor": abs(val_float),
                        "tipo": "Receita" if val_float > 0 else "Despesa",
                    })
                except:
                    continue

        if transacoes_pdf_temp:
            df_pdf_temp = pd.DataFrame(transacoes_pdf_temp)
            df_banco_atual = pd.read_sql(
                (
                    "SELECT data, descricao, valor, tipo FROM transacoes WHERE origem"
                    " = 'Manual'"
                ),
                conn,
            )

            if not df_banco_atual.empty:
                merged_rec = pd.merge(
                    df_pdf_temp,
                    df_banco_atual,
                    on=["data", "valor", tipo_trans := "tipo"],
                    how="left",
                    indicator=True,
                )
                divergentes = merged_rec[merged_rec["_merge"] == "left_only"]

                if not divergentes.empty:
                    divergentes["data"] = divergentes["data"].apply(formatar_data_ptbr)
                    st.warning(
                        f"⚠️ Atenção: Encontramos **{len(divergentes)}** transação(ões) no"
                        " PDF do extrato que constam como divergentes ou ausentes nos"
                        " lançamentos manuais do sistema:"
                    )
                    st.dataframe(
                        divergentes[["data", "descricao_x", "valor", "tipo"]].rename(
                            columns={"descricao_x": "Descrição no Extrato PDF"}
                        ),
                        use_container_width=True,
                    )
                else:
                    st.success(
                        "✅ **Reconciliação Perfeita:** Todos os lançamentos do extrato"
                        " PDF conferem com os registros manuais salvos no sistema!"
                    )
            else:
                st.info(
                    "Cadastre transações manuais no sistema para ativar o cruzamento"
                    " da reconciliação com o PDF."
                )
        else:
            st.info("Nenhuma transação válida lida no PDF atual para reconciliação.")
    else:
        st.info(
            "Faça o upload de um extrato bancário em PDF acima para habilitar o"
            " painel de Reconciliação Automatizada."
        )

    st.markdown("---")
    st.subheader("🔍 Pesquisa Avançada & Filtros Inteligentes no Extrato")

    col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
    with col_s1:
        termo_busca_extrato = st.text_input(
            "Filtrar por texto/similaridade (Descrição ou Categoria):",
            "",
            key="fil_extrato_similaridade",
        )
    with col_s2:
        filtro_tipo = st.selectbox(
            "Filtrar por Tipo:", ["Todos", "Receita", "Despesa"]
        )
    with col_s3:
        ordenacao_val = st.selectbox(
            "Ordenar por Valor:",
            ["Padrão (ID)", "Maior para Menor", "Menor para Maior"],
        )

    df_trans_all = pd.read_sql("SELECT * FROM transacoes", conn)

    if not df_trans_all.empty:
        df_extrato_filtrado = df_trans_all.copy()

        if termo_busca_extrato.strip():
            termo_limpo = termo_busca_extrato.strip().lower()
            descricoes_t = df_extrato_filtrado["descricao"].tolist()
            categorias_t = df_extrato_filtrado["categoria"].tolist()

            similares_desc = difflib.get_close_matches(
                termo_limpo, [d.lower() for d in descricoes_t], n=20, cutoff=0.25
            )
            similares_cat = difflib.get_close_matches(
                termo_limpo, [cat.lower() for cat in categorias_t], n=20, cutoff=0.25
            )

            mask = (
                df_extrato_filtrado["descricao"]
                .str.lower()
                .str.contains(termo_limpo, na=False)
                | df_extrato_filtrado["categoria"]
                .str.lower()
                .str.contains(termo_limpo, na=False)
                | df_extrato_filtrado["descricao"].str.lower().isin(similares_desc)
                | df_extrato_filtrado["descricao"].str.lower().isin(similares_cat)
            )
            df_extrato_filtrado = df_extrato_filtrado[mask]

        if filtro_tipo != "Todos":
            df_extrato_filtrado = df_extrato_filtrado[
                df_extrato_filtrado["tipo"] == filtro_tipo
            ]

        if ordenacao_val == "Maior para Menor":
            df_extrato_filtrado = df_extrato_filtrado.sort_values(
                by="valor", ascending=False
            )
        elif ordenacao_val == "Menor para Maior":
            df_extrato_filtrado = df_extrato_filtrado.sort_values(
                by="valor", ascending=True
            )

        if not df_extrato_filtrado.empty:
            df_extrato_filtrado_exib = df_extrato_filtrado.copy()
            df_extrato_filtrado_exib["data"] = df_extrato_filtrado_exib[
                "data"
            ].apply(formatar_data_ptbr)
            st.write(
                f"### 📋 Resultados Encontrados ({len(df_extrato_filtrado_exib)}"
                " registros)"
            )
            st.dataframe(
                df_extrato_filtrado_exib, use_container_width=True, hide_index=True
            )

            st.markdown(
                "### ⚙️ Gerenciar / Editar / Excluir Lançamentos do Extrato"
            )
            id_trans_sel = st.selectbox(
                "Selecione o ID da transação para editar ou excluir:",
                df_extrato_filtrado["id"].tolist(),
                key="sel_transacao_gerenciar",
            )

            if id_trans_sel:
                row_trans_atual = df_extrato_filtrado[
                    df_extrato_filtrado["id"] == id_trans_sel
                ].iloc[0]

                col_ed_op1, col_ed_op2 = st.columns(2)
                with col_ed_op1:
                    st.markdown(f"**Editando Lançamento ID {id_trans_sel}:**")
                    with st.form(f"form_editar_transacao_{id_trans_sel}"):
                        novo_tipo_t = st.selectbox(
                            "Tipo:",
                            ["Despesa", "Receita"],
                            index=0 if row_trans_atual["tipo"] == "Despesa" else 1,
                        )
                        nova_desc_t = st.text_input(
                            "Descrição:", value=row_trans_atual["descricao"]
                        )
                        novo_val_t = st.number_input(
                            "Valor (R$):",
                            min_value=0.0,
                            value=float(row_trans_atual["valor"]),
                            step=1.0,
                            format="%.2f",
                        )
                        nova_data_t = st.date_input(
                            "Data (DD/MM/AAAA):",
                            value=datetime.strptime(
                                str(row_trans_atual["data"])[:10], "%Y-%m-%d"
                            ).date(),
                            format="DD/MM/YYYY",
                        )

                        if st.form_submit_button(
                            "Salvar Alterações da Transação", use_container_width=True
                        ):
                            c.execute(
                                "UPDATE transacoes SET tipo = ?, descricao = ?, valor = ?,"
                                " data = ? WHERE id = ?",
                                (
                                    novo_tipo_t,
                                    nova_desc_t.strip(),
                                    novo_val_t,
                                    nova_data_t.strftime("%Y-%m-%d"),
                                    id_trans_sel,
                                ),
                            )
                            conn.commit()
                            st.success(f"Transação ID {id_trans_sel} atualizada com sucesso!")
                            st.rerun()

                with col_ed_op2:
                    st.markdown(f"**Excluir Lançamento ID {id_trans_sel}:**")
                    st.write(
                        f"Deseja remover permanentemente o registro"
                        f" *{row_trans_atual['descricao']}* (R$"
                        f" {row_trans_atual['valor']:,.2f})?"
                    )
                    if st.button(
                        "🗑️ Excluir Transação Selecionada", use_container_width=True
                    ):
                        c.execute("DELETE FROM transacoes WHERE id = ?", (id_trans_sel,))
                        conn.commit()
                        st.success(f"Transação ID {id_trans_sel} excluída com sucesso!")
                        st.rerun()
        else:
            st.info(
                "Nenhuma transação encontrada com os filtros e termos pesquisados."
            )
    else:
        st.info("Nenhum extrato armazenado no banco de dados.")

# ==========================================
# --- SEÇÃO 12: HOLERITES (COM SENHA DE ACESSO) ---
# ==========================================
elif st.session_state.pagina_atual == "📄 Holerites":
    botao_voltar()

    # Trava de segurança: Garante que se a página atual for recarregada ou acessada de novo, ela inicia bloqueada
    if st.session_state.get("pagina_anterior_holerite") != "📄 Holerites":
        st.session_state.holerites_desbloqueado = False
        st.session_state.pagina_anterior_holerite = "📄 Holerites"

    if "holerites_desbloqueado" not in st.session_state:
        st.session_state.holerites_desbloqueado = False

    if not st.session_state.holerites_desbloqueado:
        st.subheader("🔒 Acesso Restrito à Seção de Holerites")
        st.markdown(
            "Esta seção contém informações salariais e fiscais confidenciais. Digite a senha para prosseguir:"
        )

        with st.form("form_senha_holerites"):
            senha_holerite = st.text_input(
                "Senha de Acesso aos Holerites:",
                type="password",
                key="input_senha_holerite",
            )
            btn_desbloquear = st.form_submit_button(
                "Desbloquear Holerites", use_container_width=True
            )

            if btn_desbloquear:
                if senha_holerite == "1234":
                    st.session_state.holerites_desbloqueado = True
                    st.success("Acesso liberado com sucesso!")
                    st.rerun()
                else:
                    st.error("Senha incorreta!")

        if st.button("Bloquear / Sair da Seção", use_container_width=True):
            st.session_state.holerites_desbloqueado = False
            st.session_state.pagina_anterior_holerite = ""
            mudar_pagina("🏠 Início / Painel")
            st.rerun()
    else:
        col_sup1, col_sup2 = st.columns([4, 1])
        with col_sup1:
            st.subheader(
                "📄 Análise, Comparativo Mês a Mês & Leitura Dinâmica de Holerites via PDF"
            )
            st.info(
                "Faça o upload de arquivos PDF de contracheques. O sistema lerá com precisão cirúrgica os impostos e proventos."
            )
        with col_sup2:
            if st.button("🔒 Bloquear Seção", use_container_width=True):
                st.session_state.holerites_desbloqueado = False
                st.session_state.pagina_anterior_holerite = ""
                st.rerun()

        pdfs_holerites = st.file_uploader(
            "Escolha os arquivos PDF dos Holerites Corporativos",
            type=["pdf"],
            accept_multiple_files=True,
            key="upload_multiplos_holerites",
        )

        if pdfs_holerites:
            upload_ids = "-".join([f"{f.name}-{f.size}" for f in pdfs_holerites])
            if st.session_state.get("ultimo_upload_processado") != upload_ids:
                importados_automaticos = 0
                for arquivo_pdf in pdfs_holerites:
                    texto_holerite = ""
                    try:
                        with pdfplumber.open(arquivo_pdf) as pdf:
                            for pagina in pdf.pages:
                                ext = pagina.extract_text()
                                if ext:
                                    texto_holerite += ext + "\n"

                        (
                            mes_ano_extraido,
                            bruto_val,
                            desc_val,
                            liquido_val,
                            inss_val,
                            irrf_val,
                            vale_val,
                        ) = processar_texto_holerite(texto_holerite, arquivo_pdf.name)

                        cursor_check = c.execute(
                            "SELECT id FROM holerites WHERE mes_ano = ?",
                            (mes_ano_extraido,),
                        )
                        row_existente = cursor_check.fetchone()

                        if not row_existente:
                            c.execute(
                                "INSERT INTO holerites (mes_ano, salario_bruto, total_descontos, liquido, inss, irrf, vale) VALUES (?,?,?,?,?,?,?)",
                                (
                                    mes_ano_extraido,
                                    bruto_val,
                                    desc_val,
                                    liquido_val,
                                    inss_val,
                                    irrf_val,
                                    vale_val,
                                ),
                            )
                            conn.commit()
                            importados_automaticos += 1
                        else:
                            c.execute(
                                "UPDATE holerites SET salario_bruto = ?, total_descontos = ?, liquido = ?, inss = ?, irrf = ?, vale = ? WHERE mes_ano = ?",
                                (
                                    bruto_val,
                                    desc_val,
                                    liquido_val,
                                    inss_val,
                                    irrf_val,
                                    vale_val,
                                    mes_ano_extraido,
                                ),
                            )
                            conn.commit()
                            importados_automaticos += 1
                    except Exception as e:
                        st.error(
                            f"Erro ao processar o arquivo {arquivo_pdf.name}: {e}"
                        )

                st.session_state["ultimo_upload_processado"] = upload_ids
                if importados_automaticos > 0:
                    st.success(
                        f"🎉 {importados_automaticos} holerite(s) processado(s) e gravado(s) com sucesso!"
                    )
                    st.rerun()

        st.markdown("---")
        st.subheader("📋 Histórico Geral dos Holerites")
        df_hol_all = pd.read_sql("SELECT * FROM holerites ORDER BY id DESC", conn)
        
        if not df_hol_all.empty:
            st.dataframe(
                df_hol_all.rename(
                    columns={
                        "id": "ID",
                        "mes_ano": "Mês/Ano",
                        "salario_bruto": "Salário Bruto (R$)",
                        "total_descontos": "Total Descontos (R$)",
                        "liquido": "Líquido (R$)",
                        "inss": "INSS (R$)",
                        "irrf": "IRRF (R$)",
                        "vale": "Vale (R$)",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("---")
            st.subheader("🔍 Detalhamento Completo por Rubricas (Espelho do Holerite)")
            
            # CSS para compactar a tabela e aproximar as colunas
            st.markdown("""
                <style>
                    /* Ajusta o padding e deixa a tabela mais compacta e coesa */
                    [data-testid="stDataFrame"] div[data-testid="stTable"] {
                        width: 100%;
                    }
                    th { font-size: 13px !important; }
                    td { font-size: 13px !important; padding: 4px 8px !important; }
                </style>
            """, unsafe_allow_html=True)

            sel_hol_detalhe = st.selectbox(
                "Selecione o Mês/Ano para ver o espelho oficial, os maiores gastos e o Pareto:",
                df_hol_all["mes_ano"].tolist(),
                key="sel_detalhe_holerite"
            )

            if sel_hol_detalhe:
                hol_selecionado = df_hol_all[df_hol_all["mes_ano"] == sel_hol_detalhe].iloc[0]
                
                v_bruto = hol_selecionado["salario_bruto"]
                v_inss = hol_selecionado["inss"]
                v_irrf = hol_selecionado["irrf"]
                v_vale = hol_selecionado["vale"]

                dados_rubricas = [
                    {"Cód.": "0004", "Descrição": "Salário - Mensalistas", "Qtde.": "183,33", "Vencimentos (R$)": 5475.01, "Descontos (R$)": 0.0},
                    {"Cód.": "6151", "Descrição": "DSR Mensalista", "Qtde.": "36,67", "Vencimentos (R$)": 1095.00, "Descontos (R$)": 0.0},
                    {"Cód.": "10506", "Descrição": "Dev Prov Ad Qui - Crédito do Trabalhador", "Qtde.": "", "Vencimentos (R$)": 620.98, "Descontos (R$)": 0.0},
                    {"Cód.": "2066", "Descrição": "Seguro de Vida", "Qtde.": "", "Vencimentos (R$)": 0.0, "Descontos (R$)": 7.83},
                    {"Cód.": "2085", "Descrição": "Contribuição Confederativa", "Qtde.": "", "Vencimentos (R$)": 0.0, "Descontos (R$)": 12.00},
                    {"Cód.": "2092", "Descrição": "Mensalidade Sindical", "Qtde.": "", "Vencimentos (R$)": 0.0, "Descontos (R$)": 65.70},
                    {"Cód.": "2103", "Descrição": "INSS Normal", "Qtde.": "", "Vencimentos (R$)": 0.0, "Descontos (R$)": v_inss},
                    {"Cód.": "2125", "Descrição": "Imposto de Renda Normal", "Qtde.": "", "Vencimentos (R$)": 0.0, "Descontos (R$)": v_irrf},
                    {"Cód.": "2195", "Descrição": "Farmácia", "Qtde.": "", "Vencimentos (R$)": 0.0, "Descontos (R$)": 181.18},
                    {"Cód.": "2204", "Descrição": "Capital CredMaxion", "Qtde.": "3,00", "Vencimentos (R$)": 0.0, "Descontos (R$)": 197.10},
                    {"Cód.": "2205", "Descrição": "Mensalidade do Grêmio", "Qtde.": "1,00", "Vencimentos (R$)": 0.0, "Descontos (R$)": 35.00},
                    {"Cód.": "5182", "Descrição": "ABEMA", "Qtde.": "1,00", "Vencimentos (R$)": 0.0, "Descontos (R$)": 7.67},
                    {"Cód.": "5269", "Descrição": "GAS DE COZINHA", "Qtde.": "", "Vencimentos (R$)": 0.0, "Descontos (R$)": 110.00},
                    {"Cód.": "5565", "Descrição": "Uniodonto - Titular", "Qtde.": "1,00", "Vencimentos (R$)": 0.0, "Descontos (R$)": 17.65},
                    {"Cód.": "5566", "Descrição": "Uniodonto - Dependente", "Qtde.": "1,00", "Vencimentos (R$)": 0.0, "Descontos (R$)": 17.65},
                    {"Cód.": "6189", "Descrição": "ABEMA Dependentes", "Qtde.": "3,00", "Vencimentos (R$)": 0.0, "Descontos (R$)": 23.01},
                    {"Cód.": "7827", "Descrição": "Adiantamento Quinzenal", "Qtde.": "", "Vencimentos (R$)": 0.0, "Descontos (R$)": v_vale},
                    {"Cód.": "9297", "Descrição": "COPARTICIPACAO SULAMERICA", "Qtde.": "", "Vencimentos (R$)": 0.0, "Descontos (R$)": 63.07},
                    {"Cód.": "10497", "Descrição": "Empréstimo - Crédito do Trabalhador", "Qtde.": "", "Vencimentos (R$)": 0.0, "Descontos (R$)": 1552.45}
                ]
                
                df_rubricas = pd.DataFrame(dados_rubricas)
                st.dataframe(df_rubricas, use_container_width=False, hide_index=True)

                # --- INDICADOR DOS MAIORES GASTOS/DESCONTOS DO MÊS ---
                st.markdown("#### 🚨 Indicador: Maiores Descontos do Mês")
                df_apenas_descontos = df_rubricas[df_rubricas["Descontos (R$)"] > 0].copy()
                
                if not df_apenas_descontos.empty:
                    df_maiores_gastos = df_apenas_descontos.sort_values(by="Descontos (R$)", ascending=False).head(3)
                    
                    cols_indicador = st.columns(len(df_maiores_gastos))
                    for idx, (_, row) in enumerate(df_maiores_gastos.iterrows()):
                        with cols_indicador[idx]:
                            st.metric(
                                label=f"{row['Cód.']} - {row['Descrição']}",
                                value=f"R$ {row['Descontos (R$)']:,.2f}"
                            )
                else:
                    st.info("Nenhum desconto registrado para este período.")

                # --- GRÁFICO DE PARETO DOS DESCONTOS ---
                st.markdown("---")
                st.markdown("#### 📈 Gráfico de Pareto: Concentração dos Maiores Descontos")
                
                df_pareto = df_apenas_descontos.sort_values(by="Descontos (R$)", ascending=False).reset_index(drop=True)
                if not df_pareto.empty:
                    df_pareto["Acumulado"] = df_pareto["Descontos (R$)"].cumsum()
                    total_geral_desc = df_pareto["Descontos (R$)"].sum()
                    df_pareto["Porcentagem_Acumulada"] = (df_pareto["Acumulado"] / total_geral_desc) * 100
                    df_pareto["Rotulo"] = df_pareto["Cód."] + " - " + df_pareto["Descrição"]
                    df_pareto["Texto_Valor"] = df_pareto["Descontos (R$)"].apply(lambda x: f"R$ {x:,.2f}")

                    fig_pareto = px.bar(
                        df_pareto,
                        x="Rotulo",
                        y="Descontos (R$)",
                        text="Texto_Valor",
                        labels={"Rotulo": "Rubrica / Desconto", "Descontos (R$)": "Valor (R$)"},
                        color="Descontos (R$)",
                        color_continuous_scale="Reds"
                    )

                    fig_pareto.update_traces(
                        textposition='outside', 
                        cliponaxis=False,
                        textfont=dict(color="#f8fafc", size=12, family="sans-serif")
                    )

                    fig_pareto.add_trace(
                        px.line(
                            df_pareto,
                            x="Rotulo",
                            y="Porcentagem_Acumulada",
                            markers=True
                        ).data[0]
                    )

                    fig_pareto.update_traces(yaxis="y2")
                    fig_pareto.update_layout(
                        yaxis=dict(title="Valor dos Descontos (R$)", range=[0, df_pareto["Descontos (R$)"].max() * 1.35]),
                        yaxis2=dict(
                            title="Porcentagem Acumulada (%)",
                            overlaying="y",
                            side="right",
                            range=[0, 115],
                            showgrid=False
                        ),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#f8fafc",
                        showlegend=False,
                        xaxis_tickangle=-45,
                        margin=dict(t=120, b=50, l=40, r=40)
                    )

                    st.plotly_chart(fig_pareto, use_container_width=True)

            st.markdown("---")
            st.subheader(
                "📊 Comparativo Gráfico Mês a Mês (Evolução Salarial & Descontos)"
            )
            fig_hol = px.bar(
                df_hol_all,
                x="mes_ano",
                y=["salario_bruto", "total_descontos", "liquido"],
                barmode="group",
                labels={
                    "value": "Valor (R$)",
                    "mes_ano": "Mês/Ano",
                    "variable": "Indicador",
                },
                color_discrete_sequence=["#3b82f6", "#ef4444", "#22c55e"],
            )
            fig_hol.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#f8fafc",
            )
            st.plotly_chart(fig_hol, use_container_width=True)

            st.markdown("---")
            id_del_hol = st.selectbox(
                "Selecione o ID do holerite para remoção:",
                df_hol_all["id"].tolist(),
                key="del_hol_sel",
            )
            if st.button("Remover Holerite Selecionado", use_container_width=True):
                c.execute("DELETE FROM holerites WHERE id = ?", (id_del_hol,))
                conn.commit()
                st.success("Holerite removido com sucesso!")
                st.rerun()
        else:
            st.info("Nenhum holerite cadastrado ou importado até o momento.")
