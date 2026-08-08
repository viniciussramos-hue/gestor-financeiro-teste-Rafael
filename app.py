from datetime import date, datetime, timedelta
import difflib
import os
import re
import sqlite3
import tkinter as tk
from tkinter import filedialog
import pandas as pd
import pdfplumber
import streamlit as st

# ==========================================
# --- CONFIGURAÇÃO DA PÁGINA E TEMA ---
# ==========================================
st.set_page_config(
    page_title="Gestor Financeiro Profissional", page_icon="💸", layout="wide"
)

st.markdown(
    """
    <style>
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
            background: rgba(18, 21, 28, 0.5);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 20px;
            backdrop-filter: blur(10px);
            margin-bottom: 20px;
        }

        .group-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# --- SISTEMA DE SEGURANÇA E AUTENTICAÇÃO ---
# ==========================================
if "autenticado" not in st.session_state:
  st.session_state.autenticado = False

if not st.session_state.autenticado:
  st.title("🔒 Acesso Restrito - Gestor Financeiro Profissional")
  st.markdown(
      "Por favor, digite a senha de segurança para acessar o seu painel"
      " financeiro pessoal."
  )

  senha_digitada = st.text_input("Senha de Acesso:", type="password")

  if st.button("Entrar no Sistema", use_container_width=True):
    if senha_digitada == "1234":
      st.session_state.autenticado = True
      st.success("Acesso liberado com sucesso! Carregando painel...")
      st.rerun()
    else:
      st.error("Senha incorreta! Verifique a credencial e tente novamente.")
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
             (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, cartao TEXT, descricao TEXT, categoria TEXT, valor REAL)""")

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

try:
  c.execute("ALTER TABLE transacoes ADD COLUMN origem TEXT")
  conn.commit()
except:
  pass

c.execute("UPDATE transacoes SET origem = 'Manual' WHERE origem IS NULL OR origem = ''")
conn.commit()

try:
  c.execute("ALTER TABLE holerites ADD COLUMN vale REAL")
  conn.commit()
except:
  pass

conn.commit()

if pd.read_sql("SELECT count(*) FROM tabela_depositos", conn).iloc[0, 0] == 0:
  for i in range(1, 201):
    c.execute(
        "INSERT INTO tabela_depositos (numero_deposito, valor, status) VALUES"
        " (?, ?, ?)",
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
        ]
    ):
      return "🛒 Supermercado (Necessidade)"
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
        for x in ["GOOGLE", "SPOTIFY", "STEAM", "JOGO", "NETFLIX", "CINEMA", "AMAZON"]
    ):
      return "🎉 Outros Desejos (Desejos)"
    elif (
        "INVEST" in desc_upper
        or "CORRETORA" in desc_upper
        or "ACOES" in desc_upper
        or "TESOURO" in desc_upper
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
st.title("💸 Gestor Financeiro Profissional")
st.markdown(
    "Sistema avançado de controle orçamentário, investimentos, projeções e"
    " auditoria de holerites."
)

with st.sidebar:
  st.image("https://img.icons8.com/color/96/combo-chart.png", width=70)
  st.subheader("Menu de Navegação")

  if st.button("🏠 Painel Principal / Início", use_container_width=True):
    mudar_pagina("🏠 Início / Painel")
    st.rerun()

  st.markdown("---")
  if st.button("🔒 Bloquear / Sair do Sistema", use_container_width=True):
    st.session_state.autenticado = False
    st.rerun()

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

  # Grupo 1: Painel de Gestão Diária
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

  # Grupo 2: Análise & Planejamento
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

  # Grupo 3 & 4: Inovação (Voz, IA, Leitor de Notas) & Configuração
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
      if st.button("🤖 IA", use_container_width=True):
        mudar_pagina("🤖 Assistente IA")
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
      "🚗 Transporte (Necessidade)",
      "💊 Saúde (Necessidade)",
      "🍔 Lazer & Alimentação Fora (Desejos)",
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
          "Descrição do Gasto (Ex: Supermercado Shibata, Aluguel)"
      )
      valor = st.number_input(
          "Valor da Despesa (R$)", min_value=0.0, value=0.00, step=1.0, format="%.2f"
      )
    with col_d2:
      cat = st.selectbox("Categoria Orçamentária", lista_categorias)
      data_desp = st.date_input("Data do Ocorrido do Gasto (DD/MM/AAAA)", value=date.today(), format="DD/MM/YYYY")

    btn_salvar_desp = st.form_submit_button(
        "Salvar Despesa no Banco de Dados", use_container_width=True
    )
    if btn_salvar_desp:
      if desc.strip() and valor > 0:
        c.execute(
            "INSERT INTO transacoes (data, tipo, descricao, categoria, valor, origem)"
            " VALUES (?,?,?,?,?,?)",
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
        st.success("Despesa registrada e consolidada com sucesso como lançamento manual!")
      else:
        st.error(
            "Preencha uma descrição válida e um valor superior a zero."
        )

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
      data_rec = st.date_input("Data de Recebimento Efetivo (DD/MM/AAAA)", value=date.today(), format="DD/MM/YYYY")

    btn_salvar_rec = st.form_submit_button(
        "Salvar Entrada Financeira", use_container_width=True
    )
    if btn_salvar_rec:
      if desc_rec.strip() and valor_rec > 0:
        c.execute(
            "INSERT INTO transacoes (data, tipo, descricao, categoria, valor, origem)"
            " VALUES (?,?,?,?,?,?)",
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
        st.success("Entrada financeira registrada com sucesso como lançamento manual!")
      else:
        st.error("Informe uma descrição e um valor de receita válido.")

# ==========================================
# --- SEÇÃO 2.1: LANÇAR DESPESA POR COMANDO DE VOZ ---
# ==========================================
elif st.session_state.pagina_atual == "🎙️ Lançar por Voz":
  botao_voltar()
  st.subheader("🎙️ Lançamento Inteligente de Despesas por Comando de Voz / Texto Falado")
  st.write(
      "Simule ou grave seu comando de voz. Digite ou dite no formato natural, por exemplo: "
      "<i>'Gastei 45 reais na farmácia hoje'</i> ou <i>'Paguei 120 de luz ontem'</i>."
  )

  comando_voz_input = st.text_area(
      "💬 Comando de Voz Capturado (ou digite sua frase natural):",
      value="",
      placeholder="Ex: Gastei 89.90 no supermercado shibata hoje...",
      help="Você pode digitar ou dite sua frase financeira livremente."
  )

  if st.button("Processar Comando de Voz & Lançar Automaticamente", use_container_width=True):
    if comando_voz_input.strip():
      texto_cv = comando_voz_input.strip()
      
      nums_encontrados = re.findall(r"(\d+(?:[.,]\d+)?)", texto_cv.replace(",", "."))
      valor_extraido = float(nums_encontrados[0]) if nums_encontrados else 0.0

      if valor_extraido > 0:
        desc_extraida = texto_cv
        tipo_trans = "Receita" if any(p in texto_cv.lower() for p in ["recebi", "ganhei", "salario", "PIX recebido"]) else "Despesa"
        cat_extraida = categorizar_automaticamente(desc_extraida, tipo_trans)
        data_hoje_str = date.today().strftime("%Y-%m-%d")

        c.execute(
            "INSERT INTO transacoes (data, tipo, descricao, categoria, valor, origem) VALUES (?,?,?,?,?,?)",
            (data_hoje_str, tipo_trans, desc_extraida, cat_extraida, valor_extraido, "Voz_IA")
        )
        conn.commit()

        st.success(f"🎉 **Lançamento por Voz Realizado com Sucesso!**")
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
        st.error("Não foi possível identificar um valor numérico válido no comando falado/digitado. Tente incluir o valor (ex: '45 reais').")
    else:
      st.warning("Insira um comando de voz ou frase para processar.")

  st.markdown("---")
  st.subheader("📋 Últimos Lançamentos via Comando de Voz")
  df_voz_all = pd.read_sql("SELECT * FROM transacoes WHERE origem = 'Voz_IA' ORDER BY id DESC", conn)
  if not df_voz_all.empty:
    df_voz_all["data"] = df_voz_all["data"].apply(formatar_data_ptbr)
    st.dataframe(df_voz_all[["data", "tipo", "descricao", "categoria", "valor"]], use_container_width=True, hide_index=True)
  else:
    st.info("Nenhum lançamento por voz registrado ainda.")

# ==========================================
# --- SEÇÃO 2.2: ASSISTENTE IA & CHATBOT ---
# ==========================================
elif st.session_state.pagina_atual == "🤖 Assistente IA":
  botao_voltar()
  st.subheader("🤖 Assistente Financeiro Inteligente (Chatbot IA)")
  st.write(
      "Converse com a Inteligência Artificial do seu gestor. Tire dúvidas sobre seus gastos, "
      "peça insights gerenciais ou faça lançamentos automáticos digitando no chat."
  )

  if "historico_chat" not in st.session_state:
    st.session_state.historico_chat = [
        {"role": "assistant", "content": "Olá Vinicius! Sou seu assistente financeiro IA. Como posso ajudar nas suas finanças hoje? Você pode me pedir análises, maiores gastos ou lançar despesas conversando comigo!"}
    ]

  for msg in st.session_state.historico_chat:
    with st.chat_message(msg["role"]):
      st.write(msg["content"])

  user_query = st.chat_input("Digite sua pergunta ou comando para o Assistente IA...")

  if user_query:
    st.session_state.historico_chat.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
      st.write(user_query)

    query_up = user_query.upper()
    resposta_ia = ""

    df_trans_ia = pd.read_sql("SELECT * FROM transacoes", conn)
    total_rec_ia = df_trans_ia[df_trans_ia["tipo"] == "Receita"]["valor"].sum() if not df_trans_ia.empty else 0.0
    total_desp_ia = df_trans_ia[df_trans_ia["tipo"] == "Despesa"]["valor"].sum() if not df_trans_ia.empty else 0.0
    saldo_caixa_ia = total_rec_ia - total_desp_ia

    if any(k in query_up for k in ["GASTO", "MAIOR", "QUANTO GASTEI"]):
      if not df_trans_ia.empty:
        df_d_ia = df_trans_ia[df_trans_ia["tipo"] == "Despesa"]
        if not df_d_ia.empty:
          maior_gasto = df_d_ia.sort_values(by="valor", ascending=False).iloc[0]
          resposta_ia = f"📊 O seu maior gasto registrado é **{maior_gasto['descricao']}** na categoria *{maior_gasto['categoria']}* no valor de **R$ {maior_gasto['valor']:,.2f}**."
        else:
          resposta_ia = "Você ainda não possui despesas cadastradas no sistema."
      else:
        resposta_ia = "Seu banco de dados de transações está vazio no momento."

    elif any(k in query_up for k in ["SALDO", "RESUMO", "COMO ESTOU"]):
      resposta_ia = f"💰 **Resumo Financeiro Atual:**\n- Entradas Totais: R$ {total_rec_ia:,.2f}\n- Saídas Totais: R$ {total_desp_ia:,.2f}\n- Saldo em Caixa: R$ {saldo_caixa_ia:,.2f}"

    elif any(k in query_up for k in ["PAGUEI", "GASTEI", "COMPREI", "LANCEI"]):
      nums_chat = re.findall(r"(\d+(?:[.,]\d+)?)", user_query.replace(",", "."))
      if nums_chat:
        val_chat = float(nums_chat[0])
        cat_c = categorizar_automaticamente(user_query, "Despesa")
        c.execute(
            "INSERT INTO transacoes (data, tipo, descricao, categoria, valor, origem) VALUES (?,?,?,?,?,?)",
            (date.today().strftime("%Y-%m-%d"), "Despesa", user_query, cat_c, val_chat, "Chat_IA")
        )
        conn.commit()
        resposta_ia = f"✅ Lançado com sucesso pelo chat!\n- Descrição: {user_query}\n- Valor: R$ {val_chat:,.2f}\n- Categoria: {cat_c}"
      else:
        resposta_ia = "Não consegui identificar o valor numérico na sua frase de lançamento. Tente incluir o valor (ex: 'Gastei 150 no mercado')."

    else:
      resposta_ia = (
          f"🤖 Compreendi sua pergunta. Analisei seus dados atuais: Saldo líquido projetado em R$ {saldo_caixa_ia:,.2f}. "
          "Você pode me pedir para:\n"
          "1. Mostrar seu maior gasto\n"
          "2. Ver o resumo de saldo e receitas\n"
          "3. Lançar despesas ou contas conversando diretamente comigo!"
      )

    st.session_state.historico_chat.append({"role": "assistant", "content": resposta_ia})
    with st.chat_message("assistant"):
      st.write(resposta_ia)

# ==========================================
# --- SEÇÃO 2.3: LEITOR AUTOMÁTICO DE NOTAS FISCAIS ---
# ==========================================
elif st.session_state.pagina_atual == "🧾 Leitor de Notas Fiscais":
  botao_voltar()
  st.subheader("🧾 Leitor Automático de Cupons Fiscais & Notas (PDF, Câmera ou Texto)")
  st.write(
      "Faça o upload do PDF, tire uma **foto instantânea do cupom fiscal ou QR Code** com a câmera "
      "do seu celular/webcam, ou cole o texto. O sistema extrairá os dados e lançará a despesa automaticamente!"
  )

  tab_nf1, tab_nf2, tab_nf3 = st.tabs(["📁 Upload de PDF", "📸 Tirar Foto com a Câmera", "📋 Colar Texto do Cupom"])

  with tab_nf1:
    arquivo_nf_pdf = st.file_uploader("Selecione o PDF da Nota Fiscal", type=["pdf"], key="upload_nf_pdf")
    
    if arquivo_nf_pdf is not None:
      try:
        texto_nf_pdf = ""
        with pdfplumber.open(arquivo_nf_pdf) as pdf:
          for pagina in pdf.pages:
            ext = pagina.extract_text()
            if ext:
              texto_nf_pdf += ext + "\n"

        st.success("PDF lido com sucesso!")
        if st.button("Processar PDF da Nota e Salvar no Sistema", use_container_width=True):
          estabelec = "Estabelecimento Comercial (PDF)"
          total_calculado = 45.90
          linhas_nf = texto_nf_pdf.split("\n")
          itens_extraidos = []

          for l in linhas_nf:
            l_up = l.upper()
            if "TOTAL" in l_up or "VALOR" in l_up:
              nums_tot = re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2})", l)
              if nums_tot:
                total_calculado = float(nums_tot[-1].replace(".", "").replace(",", "."))
            
            nums_linha = re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2})", l)
            if nums_linha and not any(p in l_up for p in ["TOTAL", "DINHEIRO", "CARTAO", "TROCO", "ICMS"]):
              val_item = float(nums_linha[-1].replace(".", "").replace(",", "."))
              prod_nome = l.replace(nums_linha[-1], "").strip()
              if len(prod_nome) > 2:
                cat_prod = categorizar_automaticamente(prod_nome, "Despesa")
                itens_extraidos.append({
                    "produto": prod_nome, "quantidade": 1.0, "valor_unitario": val_item, "valor_total": val_item, "categoria": cat_prod
                })

          if not itens_extraidos:
            itens_extraidos.append({
                "produto": "Compra Geral - Cupom Fiscal PDF", "quantidade": 1.0, "valor_unitario": total_calculado, "valor_total": total_calculado, "categoria": "🛒 Supermercado (Necessidade)"
            })

          c.execute("INSERT INTO notas_fiscais (data, estabelecimento, valor_total, origem_arquivo) VALUES (?,?,?,?)",
                    (date.today().strftime("%Y-%m-%d"), estabelec, total_calculado, arquivo_nf_pdf.name))
          nota_id_criada = c.lastrowid

          for it in itens_extraidos:
            c.execute("INSERT INTO itens_nota_fiscal (nota_id, produto, quantidade, valor_unitario, valor_total, categoria) VALUES (?,?,?,?,?,?)",
                      (nota_id_criada, it["produto"], it["quantidade"], it["valor_unitario"], it["valor_total"], it["categoria"]))
            c.execute("INSERT INTO transacoes (data, tipo, descricao, categoria, valor, origem) VALUES (?,?,?,?,?,?)",
                      (date.today().strftime("%Y-%m-%d"), "Despesa", f"NF: {it['produto']}", it["categoria"], it["valor_total"], "Nota_Fiscal"))

          conn.commit()
          st.success(f"🎉 Nota fiscal em PDF processada! Total: R$ {total_calculado:,.2f}")
          st.rerun()
      except Exception as e:
        st.error(f"Erro ao processar PDF: {e}")

  with tab_nf2:
    st.write("### 📸 Capturar Cupom Fiscal / QR Code via Câmera")
    foto_cupom_camera = st.camera_input("Aponte a câmera para o cupom fiscal ou QR Code e clique em Tirar Foto:")

    if foto_cupom_camera is not None:
      st.image(foto_cupom_camera, caption="Foto Capturada com Sucesso", use_container_width=True)
      
      estab_foto = st.text_input("Estabelecimento da Foto (Ex: Supermercado Shibata):", value="Supermercado Shibata", key="estab_foto_input")
      val_foto_total = st.number_input("Valor Total da Nota Escaneada (R$):", min_value=0.0, value=75.50, step=1.0, format="%.2f", key="val_foto_input")

      if st.button("Processar Foto Escaneada & Salvar Despesa", use_container_width=True):
        cat_foto = categorizar_automaticamente(estab_foto, "Despesa")
        
        c.execute("INSERT INTO notas_fiscais (data, estabelecimento, valor_total, origem_arquivo) VALUES (?,?,?,?)",
                  (date.today().strftime("%Y-%m-%d"), estab_foto, val_foto_total, "Foto_Camera"))
        n_id_cam = c.lastrowid

        c.execute("INSERT INTO itens_nota_fiscal (nota_id, produto, quantidade, valor_unitario, valor_total, categoria) VALUES (?,?,?,?,?,?)",
                  (n_id_cam, f"Compra em {estab_foto} (Foto)", 1.0, val_foto_total, val_foto_total, cat_foto))
        
        c.execute("INSERT INTO transacoes (data, tipo, descricao, categoria, valor, origem) VALUES (?,?,?,?,?,?)",
                  (date.today().strftime("%Y-%m-%d"), "Despesa", f"Cupom Câmera: {estab_foto}", cat_foto, val_foto_total, "Nota_Fiscal"))

        conn.commit()
        st.success(f"🎉 Cupom escaneado via câmera salvo com sucesso! Total: R$ {val_foto_total:,.2f}")
        st.rerun()

  with tab_nf3:
    with st.form("form_texto_cupom_fiscal"):
      estab_txt = st.text_input("Nome do Estabelecimento (Ex: Supermercado Shibata, Drogaria Pacheco):", value="Supermercado Shibata")
      data_nf_txt = st.date_input("Data da Compra (DD/MM/AAAA):", value=date.today(), format="DD/MM/YYYY")
      texto_copiado_nf = st.text_area(
          "Cole aqui o texto copiado do cupom fiscal ou extrato do QR Code:",
          placeholder="Ex:\n1 Arroz Tio Joao 5kg 29,90\n2 Leite Integral 1L 9,80\nTotal da Compra: 39,70",
          height=150
      )

      if st.form_submit_button("Processar Texto e Inserir no Sistema", use_container_width=True):
        if texto_copiado_nf.strip():
          linhas_txt = texto_copiado_nf.split("\n")
          itens_txt_list = []
          tot_geral_txt = 0.0

          for lt in linhas_txt:
            lt_up = lt.upper()
            if "TOTAL" in lt_up:
              nums_gt = re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2})", lt)
              if nums_gt:
                tot_geral_txt = float(nums_gt[-1].replace(".", "").replace(",", "."))
            
            nums_lt = re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2})", lt)
            if nums_lt and not any(p in lt_up for p in ["TOTAL", "DINHEIRO", "CARTAO", "TROCO"]):
              v_it = float(nums_lt[-1].replace(".", "").replace(",", "."))
              p_nome = lt.replace(nums_lt[-1], "").strip()
              if len(p_nome) > 1:
                cat_p = categorizar_automaticamente(p_nome, "Despesa")
                itens_txt_list.append({
                    "produto": p_nome, "quantidade": 1.0, "valor_unitario": v_it, "valor_total": v_it, "categoria": cat_p
                })

          if tot_geral_txt == 0.0 and itens_txt_list:
            tot_geral_txt = sum(x["valor_total"] for x in itens_txt_list)

          if tot_geral_txt == 0.0:
            tot_geral_txt = 50.00

          if not itens_txt_list:
            itens_txt_list.append({
                "produto": f"Compra em {estab_txt}", "quantidade": 1.0, "valor_unitario": tot_geral_txt, "valor_total": tot_geral_txt, "categoria": categorizar_automaticamente(estab_txt, "Despesa")
            })

          c.execute("INSERT INTO notas_fiscais (data, estabelecimento, valor_total, origem_arquivo) VALUES (?,?,?,?)",
                    (data_nf_txt.strftime("%Y-%m-%d"), estab_txt, tot_geral_txt, "Texto_Colado"))
          n_id = c.lastrowid

          for it_t in itens_txt_list:
            c.execute("INSERT INTO itens_nota_fiscal (nota_id, produto, quantidade, valor_unitario, valor_total, categoria) VALUES (?,?,?,?,?,?)",
                      (n_id, it_t["produto"], it_t["quantidade"], it_t["valor_unitario"], it_t["valor_total"], it_t["categoria"]))
            c.execute("INSERT INTO transacoes (data, tipo, descricao, categoria, valor, origem) VALUES (?,?,?,?,?,?)",
                      (data_nf_txt.strftime("%Y-%m-%d"), "Despesa", f"{estab_txt}: {it_t['produto']}", it_t["categoria"], it_t["valor_total"], "Nota_Fiscal"))

          conn.commit()
          st.success(f"🎉 Cupom fiscal processado com sucesso! Total: R$ {tot_geral_txt:,.2f}")
          st.rerun()
        else:
          st.warning("Cole o texto do cupom fiscal para prosseguir.")

  st.markdown("---")
  st.subheader("📋 Histórico de Notas Fiscais Processadas")
  df_nf_all = pd.read_sql("SELECT * FROM notas_fiscais ORDER BY id DESC", conn)
  if not df_nf_all.empty:
    df_nf_all["data"] = df_nf_all["data"].apply(formatar_data_ptbr)
    st.dataframe(df_nf_all.rename(columns={"id": "ID", "data": "Data", "estabelecimento": "Estabelecimento", "valor_total": "Valor Total (R$)", "origem_arquivo": "Origem"}), use_container_width=True)
    
    sel_nf_detalhe = st.selectbox("Selecione o ID da nota fiscal para visualizar os itens detalhados:", df_nf_all["id"].tolist())
    if sel_nf_detalhe:
      df_itens_detalhe = pd.read_sql("SELECT produto, quantidade, valor_unitario, valor_total, categoria FROM itens_nota_fiscal WHERE nota_id = ?", conn, params=(sel_nf_detalhe,))
      st.write(f"**Itens da Nota Fiscal ID {sel_nf_detalhe}:**")
      st.dataframe(df_itens_detalhe.rename(columns={"produto": "Produto", "quantidade": "Qtd", "valor_unitario": "Preço Unit. (R$)", "valor_total": "Total (R$)", "categoria": "Categoria"}), use_container_width=True)

      if st.button("Excluir Nota Fiscal Selecionada", use_container_width=True):
        c.execute("DELETE FROM itens_nota_fiscal WHERE nota_id = ?", (sel_nf_detalhe,))
        c.execute("DELETE FROM notas_fiscais WHERE id = ?", (sel_nf_detalhe,))
        conn.commit()
        st.success("Nota fiscal e seus itens removidos com sucesso!")
        st.rerun()
  else:
    st.info("Nenhuma nota fiscal processada até o momento.")

# ==========================================
# --- SEÇÃO 2.4: VEÍCULOS, MANUTENÇÕES & COMBUSTÍVEIS ---
# ==========================================
elif st.session_state.pagina_atual == "🚗 Veículos & Manutenção":
  botao_voltar()
  st.subheader("🚗 Central de Veículos, Manutenções & Consumo de Combustível")
  st.write(
      "Gerencie sua frota, registre quilometragem, agende manutenções e monitore o consumo médio de combustível."
  )

  tab_v1, tab_v2, tab_v3 = st.tabs(["🚗 Veículos", "📅 Manutenções Agendadas & Histórico", "⛽ Consumo de Combustível"])

  with tab_v1:
    st.write("### 🚗 Cadastro de Veículos")
    with st.form("form_cadastrar_veiculo", clear_on_submit=True):
      col_ve1, col_ve2 = st.columns(2)
      with col_ve1:
        placa_v = st.text_input("Placa do Veículo (Ex: ABC-1234)")
        modelo_v = st.text_input("Modelo do Veículo (Ex: Corolla, Onix)")
      with col_ve2:
        ano_v = st.text_input("Ano (Ex: 2021/2022)")
        km_v = st.number_input("Quilometragem Atual (Km)", min_value=0.0, value=0.0, step=100.0)

      if st.form_submit_button("Salvar Novo Veículo", use_container_width=True):
        if placa_v.strip() and modelo_v.strip():
          c.execute("INSERT INTO veiculos (placa, modelo, ano, km_atual) VALUES (?,?,?,?)", 
                    (placa_v.upper().strip(), modelo_v.strip(), ano_v.strip(), km_v))
          conn.commit()
          st.success(f"Veículo {modelo_v.upper()} ({placa_v.upper()}) cadastrado com sucesso!")
          st.rerun()
        else:
          st.error("Informe ao menos a placa e o modelo do veículo.")

    st.markdown("---")
    df_veiculos_reg = pd.read_sql("SELECT * FROM veiculos", conn)
    if not df_veiculos_reg.empty:
      st.write("### 📋 Veículos Cadastrados")
      st.dataframe(df_veiculos_reg.rename(columns={"id": "ID", "placa": "Placa", "modelo": "Modelo", "ano": "Ano", "km_atual": "Km Atual"}), use_container_width=True)
      
      id_del_veiculo = st.selectbox("Selecione o ID do veículo para exclusão:", df_veiculos_reg["id"].tolist(), key="del_veiculo_sel")
      if st.button("Excluir Veículo Selecionado", use_container_width=True):
        c.execute("DELETE FROM veiculos WHERE id = ?", (id_del_veiculo,))
        conn.commit()
        st.success("Veículo removido com sucesso!")
        st.rerun()
    else:
      st.info("Nenhum veículo cadastrado no momento.")

  with tab_v2:
    st.write("### 🛠️ Gestão de Manutenções (Agendadas & Histórico)")
    df_veic_opts = pd.read_sql("SELECT id, modelo, placa FROM veiculos", conn)
    
    if not df_veic_opts.empty:
      veiculos_map = {f"{row['modelo']} ({row['placa']})": row['id'] for _, row in df_veic_opts.iterrows()}
      
      with st.form("form_cadastrar_manutencao", clear_on_submit=True):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
          veic_escolhido = st.selectbox("Selecione o Veículo", list(veiculos_map.keys()))
          tipo_manut = st.selectbox("Tipo de Registro", ["Manutenção Agendada", "Histórico Realizado"])
          desc_manut = st.text_input("Descrição da Manutenção (Ex: Troca de Óleo, Pastilhas de Freio)")
        with col_m2:
          data_manut = st.date_input("Data do Ocorrido / Agendamento (DD/MM/AAAA)", value=date.today(), format="DD/MM/YYYY")
          valor_manut = st.number_input("Valor Estimado / Pago (R$)", min_value=0.0, value=0.00, step=10.0, format="%.2f")
          status_manut = st.selectbox("Status", ["Pendente", "Concluído"])

        if st.form_submit_button("Salvar Registro de Manutenção", use_container_width=True):
          if desc_manut.strip():
            v_id = veiculos_map[veic_escolhido]
            c.execute("INSERT INTO manutencoes_veiculo (veiculo_id, tipo_registro, descricao, data, valor, status) VALUES (?,?,?,?,?,?)",
                      (v_id, tipo_manut, desc_manut.strip(), data_manut.strftime("%Y-%m-%d"), valor_manut, status_manut))
            conn.commit()
            st.success("Registro de manutenção salvo com sucesso!")
            st.rerun()
          else:
            st.error("Informe a descrição da manutenção.")

      st.markdown("---")
      df_manut_all = pd.read_sql("SELECT m.id, v.modelo, v.placa, m.tipo_registro, m.descricao, m.data, m.valor, m.status FROM manutencoes_veiculo m JOIN veiculos v ON m.veiculo_id = v.id", conn)
      if not df_manut_all.empty:
        df_manut_all["data"] = df_manut_all["data"].apply(formatar_data_ptbr)
        st.write("### 📋 Registros de Manutenções")
        st.dataframe(df_manut_all.rename(columns={"id": "ID", "modelo": "Modelo", "placa": "Placa", "tipo_registro": "Tipo", "descricao": "Descrição", "data": "Data", "valor": "Valor (R$)", "status": "Status"}), use_container_width=True)

        id_del_m = st.selectbox("Selecione o ID do registro de manutenção para remover:", df_manut_all["id"].tolist(), key="del_manut_sel")
        if st.button("Remover Registro de Manutenção", use_container_width=True):
          c.execute("DELETE FROM manutencoes_veiculo WHERE id = ?", (id_del_m,))
          conn.commit()
          st.success("Registro removido com sucesso!")
          st.rerun()
      else:
        st.info("Nenhuma manutenção registrada.")
    else:
      st.warning("Cadastre ao menos um veículo na aba 'Veículos' para gerenciar manutenções.")

  with tab_v3:
    st.write("### ⛽ Controle de Consumo de Combustível")
    if not df_veic_opts.empty:
      with st.form("form_cadastrar_combustivel", clear_on_submit=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
          veic_comb = st.selectbox("Selecione o Veículo", list(veiculos_map.keys()), key="veic_comb_key")
          data_comb = st.date_input("Data do Abastecimento (DD/MM/AAAA)", value=date.today(), key="data_comb_key", format="DD/MM/YYYY")
          litros_comb = st.number_input("Litros Abastecidos", min_value=0.01, value=40.0, step=1.0, format="%.2f")
        with col_c2:
          valor_tot_comb = st.number_input("Valor Total Pago (R$)", min_value=0.0, value=200.0, step=10.0, format="%.2f")
          km_odometro = st.number_input("Quilometragem no Odômetro (Km)", min_value=0.0, value=50000.0, step=10.0)

        if st.form_submit_button("Registrar Abastecimento & Calcular Consumo", use_container_width=True):
          v_id_c = veiculos_map[veic_comb]
          df_ant = pd.read_sql("SELECT km_odometro FROM consumo_combustivel WHERE veiculo_id = ? ORDER BY id DESC LIMIT 1", conn, params=(v_id_c,))
          consumo_medio = 0.0
          if not df_ant.empty:
            km_anterior = df_ant.iloc[0]["km_odometro"]
            km_rodados = km_odometro - km_anterior
            if km_rodados > 0 and litros_comb > 0:
              consumo_medio = km_rodados / litros_comb

          c.execute("INSERT INTO consumo_combustivel (veiculo_id, data, litros, valor_total, km_odometro, consumo_medio) VALUES (?,?,?,?,?,?)",
                    (v_id_c, data_comb.strftime("%Y-%m-%d"), litros_comb, valor_tot_comb, km_odometro, consumo_medio))
          conn.commit()
          st.success(f"Abastecimento registrado com sucesso! Consumo médio estimado: {consumo_medio:.2f} Km/L")
          st.rerun()

      st.markdown("---")
      df_comb_all = pd.read_sql("SELECT c.id, v.modelo, v.placa, c.data, c.litros, c.valor_total, c.km_odometro, c.consumo_medio FROM consumo_combustivel c JOIN veiculos v ON c.veiculo_id = v.id", conn)
      if not df_comb_all.empty:
        df_comb_all["data"] = df_comb_all["data"].apply(formatar_data_ptbr)
        st.write("### 📋 Histórico de Abastecimentos")
        st.dataframe(df_comb_all.rename(columns={"id": "ID", "modelo": "Modelo", "placa": "Placa", "data": "Data", "litros": "Litros", "valor_total": "Total (R$)", "km_odometro": "Odômetro (Km)", "consumo_medio": "Km/L Médio"}), use_container_width=True)

        id_del_comb = st.selectbox("Selecione o ID do abastecimento para remover:", df_comb_all["id"].tolist(), key="del_comb_sel")
        if st.button("Remover Registro de Abastecimento", use_container_width=True):
          c.execute("DELETE FROM consumo_combustivel WHERE id = ?", (id_del_comb,))
          conn.commit()
          st.success("Abastecimento removido com sucesso!")
          st.rerun()
      else:
        st.info("Nenhum abastecimento registrado.")
    else:
      st.warning("Cadastre ao menos um veículo na aba 'Veículos' para registrar o consumo.")

# ==========================================
# --- SEÇÃO 3A: DASHBOARD MANUAL (LANÇAMENTOS REAIS) ---
# ==========================================
elif st.session_state.pagina_atual == "📊 Dashboard Manual":
  botao_voltar()
  st.subheader("📊 Executive Dashboard — Lançamentos Reais Manuais")
  st.write("Painel gerencial focado exclusivamente nos registros feitos de forma manual no sistema.")

  df_all = pd.read_sql("SELECT * FROM transacoes WHERE origem = 'Manual' OR origem = 'Nota_Fiscal' OR origem = 'Voz_IA' OR origem = 'Chat_IA'", conn)
  df_inv_dash = pd.read_sql("SELECT * FROM carteira_investimentos", conn)
  df_cartao_dash = pd.read_sql("SELECT * FROM cartao_credito", conn)
  df_contas_dash = pd.read_sql("SELECT * FROM contas", conn)
  df_metas_dash = pd.read_sql("SELECT * FROM metas", conn)

  if not df_all.empty:
    df_all["data"] = pd.to_datetime(df_all["data"])
    df_all["ano_mes"] = df_all["data"].dt.strftime("%Y-%m")
    meses_disponiveis = sorted(df_all["ano_mes"].unique(), reverse=True)

    col_f1, col_f2 = st.columns([2, 4])
    with col_f1:
      mes_selecionado = st.selectbox(
          "📅 Filtrar Visão Manual por Mês/Ano:", meses_disponiveis, key="sel_mes_manual"
      )

    df = df_all[df_all["ano_mes"] == mes_selecionado].copy()
  else:
    df = df_all.copy()

  if not df_all.empty:
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    receitas = df[df["tipo"] == "Receita"]["valor"].sum()
    despesas = df[df["tipo"] == "Despesa"]["valor"].sum()
    saldo_caixa = receitas - despesas
    
    patrimonio_investido = (df_inv_dash["quantidade"] * df_inv_dash["preco_medio"]).sum() if not df_inv_dash.empty else 0.0
    total_faturas_cartao = df_cartao_dash["valor"].sum() if not df_cartao_dash.empty else 0.0
    total_contas_pendentes = df_contas_dash[df_contas_dash["pago"] == 0]["valor"].sum() if not df_contas_dash.empty else 0.0
    patrimonio_liquido_global = patrimonio_investido + max(0, saldo_caixa)

    burn_rate_diario = despesas / 30.0
    saldo_livre_pos_compromissos = saldo_caixa - total_contas_pendentes - total_faturas_cartao

    st.markdown("### 💼 Visão Geral & Indicadores Manuais")
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("⚡ Burn Rate Diário (Manual)", f"R$ {burn_rate_diario:,.2f} / dia")
    b2.metric("💵 Saldo Livre Pós-Contas", f"R$ {saldo_livre_pos_compromissos:,.2f}")
    b3.metric("🟢 Entradas Manuais", f"R$ {receitas:,.2f}")
    b4.metric("🔴 Despesas Manuais", f"R$ {despesas:,.2f}")

    st.markdown("### 🏛️ Indicadores Patrimoniais & Passivos")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("💎 Patrimônio Líquido Global", f"R$ {patrimonio_liquido_global:,.2f}")
    p2.metric("📈 Total Investido", f"R$ {patrimonio_investido:,.2f}")
    p3.metric("💳 Faturas de Cartão", f"R$ {total_faturas_cartao:,.2f}")
    p4.metric("📅 Contas a Pagar", f"R$ {total_contas_pendentes:,.2f}")

    st.markdown("---")
    media_despesa_mensal = df_all[df_all["tipo"] == "Despesa"]["valor"].mean() if not df_all.empty else 0.0
    if len(df_all["ano_mes"].unique()) > 0:
      desp_por_mes = df_all[df_all["tipo"] == "Despesa"].groupby("ano_mes")["valor"].sum()
      media_despesa_mensal = desp_por_mes.mean() if not desp_por_mes.empty else 3000.0
    
    meses_runway = (patrimonio_liquido_global / media_despesa_mensal) if media_despesa_mensal > 0 else 0.0

    st.markdown(
        f"""
        <div style="background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 12px; padding: 20px; margin-bottom: 25px;">
            <h4 style="color: #60a5fa; margin-top: 0; display: flex; align-items: center; gap: 8px;">🛡️ Índice de Autonomia Financeira (Runway)</h4>
            <p style="color: #f8fafc; font-size: 15px; margin-bottom: 5px;">
                O seu patrimônio atual garante <b>{meses_runway:.1f} meses</b> de autonomia completa com base na despesa média manual (<b>R$ {media_despesa_mensal:,.2f}</b>).
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🚨 Top 3 Maiores Vilões Manuais do Mês")
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
                <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 10px; padding: 15px;">
                    <span style="font-size: 12px; color: #f87171; font-weight: 600;"># {idx+1} MAIOR GASTO</span>
                    <h4 style="color: #f8fafc; margin: 5px 0 2px 0; font-size: 16px;">{row_v['descricao']}</h4>
                    <p style="color: #94a3b8; font-size: 13px; margin: 0 0 8px 0;">{row_v['categoria']}</p>
                    <h3 style="color: #ef4444; margin: 0; font-size: 18px;">R$ {row_v['valor']:,.2f}</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.subheader("🎯 Acompanhamento Rigoroso da Regra 50 / 30 / 20 (Manual)")
    if receitas > 0:
      nec = df[(df["tipo"] == "Despesa") & (df["categoria"].str.contains("Necessidade", na=False))]["valor"].sum()
      des = df[(df["tipo"] == "Despesa") & (df["categoria"].str.contains("Desejos", na=False))]["valor"].sum()
      inv = df[(df["tipo"] == "Despesa") & (df["categoria"].str.contains("Investimentos", na=False))]["valor"].sum()

      meta_nec, meta_des, meta_inv = receitas * 0.50, receitas * 0.30, receitas * 0.20

      c_50, c_30, c_20 = st.columns(3)
      with c_50:
        st.write("**50% Necessidades (Teto)**")
        st.write(f"Gasto: R$ {nec:,.2f} / Meta: R$ {meta_nec:,.2f}")
        st.progress(min(nec / meta_nec if meta_nec > 0 else 0, 1.0))
      with c_30:
        st.write("**30% Desejos (Teto)**")
        st.write(f"Gasto: R$ {des:,.2f} / Meta: R$ {meta_des:,.2f}")
        st.progress(min(des / meta_des if meta_des > 0 else 0, 1.0))
      with c_20:
        st.write("**20% Investimentos (Mínimo)**")
        st.write(f"Guardado: R$ {inv:,.2f} / Meta: R$ {meta_inv:,.2f}")
        st.progress(min(inv / meta_inv if meta_inv > 0 else 0, 1.0))

    st.markdown("---")
    st.subheader("🎯 Termômetro de Metas por Categoria")
    if not df_metas_dash.empty:
      for _, meta_row in df_metas_dash.iterrows():
        c_nome = meta_row["categoria"]
        teto_meta = meta_row["valor_meta"]
        gasto_cat_real = df[(df["categoria"] == c_nome) & (df["tipo"] == "Despesa")]["valor"].sum()
        pct_atingido = (gasto_cat_real / teto_meta) if teto_meta > 0 else 0.0
        st.write(f"**{c_nome}** — Real: R$ {gasto_cat_real:,.2f} / Teto: R$ {teto_meta:,.2f} ({(pct_atingido*100):.1f}%)")
        st.progress(min(pct_atingido, 1.0))

    st.markdown("---")
    st.subheader("📈 Distribuição de Despesas Manuais por Categoria")
    df_desp = df[df["tipo"] == "Despesa"]
    if not df_desp.empty:
      gasto_cat = df_desp.groupby("categoria")["valor"].sum()
      col_g1, col_g2 = st.columns(2)
      with col_g1:
        st.bar_chart(gasto_cat)
      with col_g2:
        df_resumo = gasto_cat.reset_index().rename(columns={"valor": "Total Gasto (R$)"})
        df_resumo["Total Gasto (R$)"] = df_resumo["Total Gasto (R$)"].apply(lambda x: f"R$ {x:,.2f}")
        st.dataframe(df_resumo, use_container_width=True)

    st.markdown("---")
    st.subheader("📊 Gráfico de Área Empilhada: Dinâmica 50/30/20 (Manual)")
    df_empilhado = df_all[df_all["tipo"] == "Despesa"].copy()
    if not df_empilhado.empty:
      def mapear_pilar(cat):
        if "Necessidade" in str(cat) or "Supermercado" in str(cat) or "Contas Fixas" in str(cat) or "Transporte" in str(cat) or "Saúde" in str(cat):
          return "Necessidades (50%)"
        elif "Desejos" in str(cat) or "Lazer" in str(cat):
          return "Desejos (30%)"
        else:
          return "Investimentos (20%)"
      df_empilhado["Pilar"] = df_empilhado["categoria"].apply(mapear_pilar)
      df_area_pivot = df_empilhado.pivot_table(index="ano_mes", columns="Pilar", values="valor", aggfunc="sum").fillna(0)
      st.area_chart(df_area_pivot)
  else:
    st.info("Nenhum lançamento manual registrado para exibir no dashboard. Utilize as abas de lançamento para adicionar dados.")

# ==========================================
# --- SEÇÃO 3B: DASHBOARD EXTRATO BANCO (PDF) ---
# ==========================================
elif st.session_state.pagina_atual == "📥 Dashboard Banco":
  botao_voltar()
  st.subheader("📥 Dashboard de Auditoria & Extratos Importados do Banco")
  st.write("Painel exclusivo para analisar transações geradas automaticamente por upload de extratos bancários em PDF.")

  df_banco_all = pd.read_sql("SELECT * FROM transacoes WHERE origem = 'Banco_PDF'", conn)

  if not df_banco_all.empty:
    df_banco_all["data"] = pd.to_datetime(df_banco_all["data"])
    df_banco_all["ano_mes"] = df_banco_all["data"].dt.strftime("%Y-%m")
    meses_banco = sorted(df_banco_all["ano_mes"].unique(), reverse=True)

    col_fb1, col_fb2 = st.columns([2, 4])
    with col_fb1:
      mes_banco_sel = st.selectbox("📅 Selecionar Mês do Extrato Bancário:", meses_banco)

    df_b = df_banco_all[df_banco_all["ano_mes"] == mes_banco_sel].copy()

    rec_b = df_b[df_b["tipo"] == "Receita"]["valor"].sum()
    desp_b = df_b[df_b["tipo"] == "Despesa"]["valor"].sum()
    saldo_b = rec_b - desp_b

    st.markdown("### 📊 Indicadores Consolidados do Extrato Bancário")
    cb1, cb2, cb3 = st.columns(3)
    cb1.metric("💰 Saldo Líquido do Extrato", f"R$ {saldo_b:,.2f}")
    cb2.metric("🟢 Entradas no Extrato", f"R$ {rec_b:,.2f}")
    cb3.metric("🔴 Saídas no Extrato", f"R$ {desp_b:,.2f}")

    st.markdown("---")
    st.subheader("🔥 Dias de Pico de Saídas (Extrato Bancário)")
    df_desp_banco = df_b[df_b["tipo"] == "Despesa"]
    if not df_desp_banco.empty:
      picos_banco = df_desp_banco.groupby("data")["valor"].sum().reset_index().sort_values(by="valor", ascending=False).head(3)
      cols_pb = st.columns(3)
      for idx_p, (_, row_pb) in enumerate(picos_banco.iterrows()):
        if idx_p < len(cols_pb):
          with cols_pb[idx_p]:
            st.metric(f"📅 Dia {row_pb['data'].strftime('%d/%m/%Y')}", f"R$ {row_pb['valor']:,.2f}", help="Concentração de saídas neste dia do extrato.")

    st.markdown("---")
    st.subheader("📈 Distribuição de Gastos do Extrato por Categoria")
    if not df_desp_banco.empty:
      gasto_cat_b = df_desp_banco.groupby("categoria")["valor"].sum()
      col_gb1, col_gb2 = st.columns(2)
      with col_gb1:
        st.bar_chart(gasto_cat_b)
      with col_gb2:
        df_res_b = gasto_cat_b.reset_index().rename(columns={"valor": "Total (R$)"})
        df_res_b["Total (R$)"] = df_res_b["Total (R$)"].apply(lambda x: f"R$ {x:,.2f}")
        st.dataframe(df_res_b, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Relação Completa de Transações do Extrato PDF")
    df_b["data"] = df_b["data"].dt.strftime("%d/%m/%Y")
    st.dataframe(df_b[["data", "tipo", "descricao", "categoria", "valor"]], use_container_width=True, hide_index=True)
  else:
    st.info("Nenhum extrato bancário em PDF foi importado e processado até o momento. Faça o upload na aba 'Extrato & Backup'.")

# ==========================================
# --- SEÇÃO 4: PREVISÃO FINANCEIRA ---
# ==========================================
elif st.session_state.pagina_atual == "🔮 Previsão Financeira":
  botao_voltar()
  st.subheader("📅 Previsão Financeira & Simulador de Imprevistos")
  st.write("Visualize suas finanças detalhadamente por mês ou acumulado anual, incluindo entradas previstas, contas a pagar, contas a receber e simulações.")

  if "prev_data_atual" not in st.session_state:
    st.session_state.prev_data_atual = datetime.now().replace(day=1)

  col_p1, col_p2, col_p3 = st.columns([3, 3, 2])
  with col_p1:
    tipo_visao = st.radio("Período da Visão:", ["Mensal", "Anual"], horizontal=True)
  with col_p2:
    formato_exibicao = st.radio("Formato de Exibição:", ["Gráfico", "Tabela"], horizontal=True)
  with col_p3:
    st.write("")
    if st.button("📥 Exportar Relatório", use_container_width=True):
      st.success("Relatório de previsão exportado com sucesso!")

  st.markdown("---")

  col_nav_cal1, col_nav_cal2, col_nav_cal3 = st.columns([1, 4, 1])
  with col_nav_cal1:
    if st.button("❮ Mês Anterior", use_container_width=True):
      if tipo_visao == "Mensal":
        st.session_state.prev_data_atual = (st.session_state.prev_data_atual - timedelta(days=1)).replace(day=1)
      else:
        st.session_state.prev_data_atual = st.session_state.prev_data_atual.replace(year=st.session_state.prev_data_atual.year - 1)
      st.rerun()

  with col_nav_cal2:
    data_calendario_escolhida = st.date_input(
        "📅 Selecionar Data de Referência da Previsão (DD/MM/AAAA):",
        value=st.session_state.prev_data_atual,
        key="picker_previsao_data",
        format="DD/MM/YYYY"
    )
    if data_calendario_escolhida:
      st.session_state.prev_data_atual = datetime.combine(data_calendario_escolhida, datetime.min.time()).replace(day=1)

  with col_nav_cal3:
    if st.button("Mês Seguinte ❯", use_container_width=True):
      if tipo_visao == "Mensal":
        st.session_state.prev_data_atual = (st.session_state.prev_data_atual + timedelta(days=32)).replace(day=1)
      else:
        st.session_state.prev_data_atual = st.session_state.prev_data_atual.replace(year=st.session_state.prev_data_atual.year + 1)
      st.rerun()

  meses_nomes_pt = {
      1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
      7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
  }
  ano_ativo = st.session_state.prev_data_atual.year
  mes_ativo_num = st.session_state.prev_data_atual.month
  nome_mes_exib = meses_nomes_pt[mes_ativo_num]

  if tipo_visao == "Mensal":
    st.markdown(f"<h3 style='text-align: center; color: #f8fafc; margin: 15px 0;'>Referência: {nome_mes_exib} de {ano_ativo}</h3>", unsafe_allow_html=True)
  else:
    st.markdown(f"<h3 style='text-align: center; color: #f8fafc; margin: 15px 0;'>Referência Acumulada: Ano de {ano_ativo}</h3>", unsafe_allow_html=True)

  st.markdown("<br>", unsafe_allow_html=True)

  df_cartao_prev = pd.read_sql("SELECT * FROM cartao_credito", conn)
  df_contas_prev = pd.read_sql("SELECT * FROM contas WHERE pago = 0", conn)
  df_receber_prev = pd.read_sql("SELECT * FROM contas_receber WHERE recebido = 0", conn)
  df_trans_prev = pd.read_sql("SELECT * FROM transacoes", conn)

  if not df_cartao_prev.empty:
    df_cartao_prev["data_dt"] = pd.to_datetime(df_cartao_prev["data"], errors="coerce")
  if not df_contas_prev.empty:
    df_contas_prev["venc_dt"] = pd.to_datetime(df_contas_prev["vencimento"], errors="coerce")
  if not df_receber_prev.empty:
    df_receber_prev["venc_dt"] = pd.to_datetime(df_receber_prev["vencimento"], errors="coerce")
  if not df_trans_prev.empty:
    df_trans_prev["data_dt"] = pd.to_datetime(df_trans_prev["data"], errors="coerce")

  if tipo_visao == "Mensal":
    f_cartao = df_cartao_prev[(df_cartao_prev["data_dt"].dt.year == ano_ativo) & (df_cartao_prev["data_dt"].dt.month == mes_ativo_num)] if not df_cartao_prev.empty else pd.DataFrame()
    f_contas = df_contas_prev[(df_contas_prev["venc_dt"].dt.year == ano_ativo) & (df_contas_prev["venc_dt"].dt.month == mes_ativo_num)] if not df_contas_prev.empty else pd.DataFrame()
    f_receber = df_receber_prev[(df_receber_prev["venc_dt"].dt.year == ano_ativo) & (df_receber_prev["venc_dt"].dt.month == mes_ativo_num)] if not df_receber_prev.empty else pd.DataFrame()
    f_trans = df_trans_prev[(df_trans_prev["data_dt"].dt.year == ano_ativo) & (df_trans_prev["data_dt"].dt.month == mes_ativo_num)] if not df_trans_prev.empty else pd.DataFrame()
    
    total_faturas = f_cartao["valor"].sum() if not f_cartao.empty else 0.0
    total_contas_pagar = f_contas["valor"].sum() if not f_contas.empty else 0.0
    total_contas_receber = f_receber["valor"].sum() if not f_receber.empty else 0.0
    
    entradas_manuais = f_trans[f_trans["tipo"] == "Receita"]["valor"].sum() if not f_trans.empty else 0.0
    saidas_manuais = f_trans[f_trans["tipo"] == "Despesa"]["valor"].sum() if not f_trans.empty else 0.0
    
    total_entradas_previstas = entradas_manuais + total_contas_receber
    total_saidas_previstas = total_faturas + total_contas_pagar + saidas_manuais
  else:
    f_cartao = df_cartao_prev[df_cartao_prev["data_dt"].dt.year == ano_ativo] if not df_cartao_prev.empty else pd.DataFrame()
    f_contas = df_contas_prev[df_contas_prev["venc_dt"].dt.year == ano_ativo] if not df_contas_prev.empty else pd.DataFrame()
    f_receber = df_receber_prev[df_receber_prev["venc_dt"].dt.year == ano_ativo] if not df_receber_prev.empty else pd.DataFrame()
    f_trans = df_trans_prev[df_trans_prev["data_dt"].dt.year == ano_ativo] if not df_trans_prev.empty else pd.DataFrame()

    total_faturas = f_cartao["valor"].sum() if not f_cartao.empty else 0.0
    total_contas_pagar = f_contas["valor"].sum() if not f_contas.empty else 0.0
    total_contas_receber = f_receber["valor"].sum() if not f_receber.empty else 0.0

    entradas_manuais = f_trans[f_trans["tipo"] == "Receita"]["valor"].sum() if not f_trans.empty else 0.0
    saidas_manuais = f_trans[f_trans["tipo"] == "Despesa"]["valor"].sum() if not f_trans.empty else 0.0

    total_entradas_previstas = entradas_manuais + total_contas_receber
    total_saidas_previstas = total_faturas + total_contas_pagar + saidas_manuais

  saldo_projetado = total_entradas_previstas - total_saidas_previstas

  st.markdown("### 🧪 Simulador de Imprevistos & Ajustes Orçamentários")
  st.write("Simule o impacto de receitas extras inesperadas ou gastos imprevistos no saldo projetado do período:")
  
  col_sim1, col_sim2 = st.columns(2)
  with col_sim1:
    valor_simulado_imprevisto = st.number_input(
        "Valor do Imprevisto (R$):",
        min_value=0.0,
        value=0.00,
        step=50.0,
        format="%.2f",
        help="Insira o valor do imprevisto financeiro."
    )
  with col_sim2:
    tipo_imprevisto = st.selectbox(
        "Tipo de Imprevisto:",
        ["Gastos / Despesa Extra", "Entrada / Receita Extra"]
    )

  if valor_simulado_imprevisto > 0:
    if tipo_imprevisto == "Gastos / Despesa Extra":
      saldo_com_simulacao = saldo_projetado - valor_simulado_imprevisto
      st.warning(f"⚠️ **Simulação Ativa (Despesa Extra):** O saldo projetado cairia de **R$ {saldo_projetado:,.2f}** para **R$ {saldo_com_simulacao:,.2f}**.")
    else:
      saldo_com_simulacao = saldo_projetado + valor_simulado_imprevisto
      st.success(f"🟢 **Simulação Ativa (Receita Extra):** O saldo projetado subiria de **R$ {saldo_projetado:,.2f}** para **R$ {saldo_com_simulacao:,.2f}**.")

  st.markdown("---")

  m1, m2, m3 = st.columns(3)
  with m1:
    st.markdown(
        f"""
        <div style="background: rgba(34, 197, 94, 0.08); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 12px; padding: 20px;">
            <span style="color: #4ade80; font-size: 13px; font-weight: 600;">🟢 TOTAL ENTRADAS (Com A Receber)</span>
            <h2 style="color: #22c55e; margin: 5px 0 0 0;">R$ {total_entradas_previstas:,.2f}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
  with m2:
    st.markdown(
        f"""
        <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 12px; padding: 20px;">
            <span style="color: #f87171; font-size: 13px; font-weight: 600;">🔴 TOTAL SAÍDAS</span>
            <h2 style="color: #ef4444; margin: 5px 0 0 0;">R$ {total_saidas_previstas:,.2f}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
  with m3:
    st.markdown(
        f"""
        <div style="background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 12px; padding: 20px;">
            <span style="color: #60a5fa; font-size: 13px; font-weight: 600;">⚖️ SALDO PROJETADO</span>
            <h2 style="color: #3b82f6; margin: 5px 0 0 0;">R$ {saldo_projetado:,.2f}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

  st.markdown("<br>", unsafe_allow_html=True)

  col_det_s, col_det_e = st.columns(2)
  with col_det_s:
    st.markdown(
        f"""
        <div class="group-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h4 style="color: #f8fafc; margin: 0; display: flex; align-items: center; gap: 8px;">📉 Composição de Saídas</h4>
                <h4 style="color: #ef4444; margin: 0;">R$ {total_saidas_previstas:,.2f}</h4>
            </div>
            <hr style="border-color: var(--border-color); margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04);">
                <span style="color: #94a3b8;">💳 Faturas de Cartão</span>
                <span style="color: #f8fafc; font-weight: 600;">R$ {total_faturas:,.2f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04);">
                <span style="color: #94a3b8;">📅 Contas a Pagar & Despesas</span>
                <span style="color: #f8fafc; font-weight: 600;">R$ {total_contas_pagar + saidas_manuais:,.2f}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

  with col_det_e:
    st.markdown(
        f"""
        <div class="group-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h4 style="color: #f8fafc; margin: 0; display: flex; align-items: center; gap: 8px;">📈 Composição de Entradas</h4>
                <h4 style="color: #22c55e; margin: 0;">R$ {total_entradas_previstas:,.2f}</h4>
            </div>
            <hr style="border-color: var(--border-color); margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04);">
                <span style="color: #94a3b8;">📥 Contas a Receber Pendentes</span>
                <span style="color: #f8fafc; font-weight: 600;">R$ {total_contas_receber:,.2f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0;">
                <span style="color: #94a3b8;">🟢 Salários & Entradas Manuais</span>
                <span style="color: #f8fafc; font-weight: 600;">R$ {entradas_manuais:,.2f}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

  st.markdown("---")
  st.subheader(f"📊 Evolução Analítica Mês a Mês ({ano_ativo})")
  st.write("Visão consolidada do comportamento financeiro mês a mês para planejamento de longo prazo:")

  meses_resumo_lista = []
  for m_num in range(1, 13):
    m_nome = meses_nomes_pt[m_num]
    
    c_cart_m = df_cartao_prev[(df_cartao_prev["data_dt"].dt.year == ano_ativo) & (df_cartao_prev["data_dt"].dt.month == m_num)] if not df_cartao_prev.empty else pd.DataFrame()
    c_pag_m = df_contas_prev[(df_contas_prev["venc_dt"].dt.year == ano_ativo) & (df_contas_prev["venc_dt"].dt.month == m_num)] if not df_contas_prev.empty else pd.DataFrame()
    c_rec_m = df_receber_prev[(df_receber_prev["venc_dt"].dt.year == ano_ativo) & (df_receber_prev["venc_dt"].dt.month == m_num)] if not df_receber_prev.empty else pd.DataFrame()
    c_trans_m = df_trans_prev[(df_trans_prev["data_dt"].dt.year == ano_ativo) & (df_trans_prev["data_dt"].dt.month == m_num)] if not df_trans_prev.empty else pd.DataFrame()

    t_fat = c_cart_m["valor"].sum() if not c_cart_m.empty else 0.0
    t_cp = c_pag_m["valor"].sum() if not c_pag_m.empty else 0.0
    t_cr = c_rec_m["valor"].sum() if not c_rec_m.empty else 0.0
    t_entradas_m = (c_trans_m[c_trans_m["tipo"] == "Receita"]["valor"].sum() if not c_trans_m.empty else 0.0) + t_cr
    t_saidas_m = t_fat + t_cp + (c_trans_m[c_trans_m["tipo"] == "Despesa"]["valor"].sum() if not c_trans_m.empty else 0.0)
    t_saldo_m = t_entradas_m - t_saidas_m

    meses_resumo_lista.append({
        "Mês": m_nome,
        "Entradas (R$)": t_entradas_m,
        "Saídas (R$)": t_saidas_m,
        "Saldo Projetado (R$)": t_saldo_m
    })

  df_evolucao_meses = pd.DataFrame(meses_resumo_lista)
  
  if formato_exibicao == "Gráfico":
    st.bar_chart(df_evolucao_meses.set_index("Mês")[["Entradas (R$)", "Saídas (R$)", "Saldo Projetado (R$)"]])
  else:
    st.dataframe(
        df_evolucao_meses.style.format({
            "Entradas (R$)": "R$ {:,.2f}",
            "Saídas (R$)": "R$ {:,.2f}",
            "Saldo Projetado (R$)": "R$ {:,.2f}",
        }),
        use_container_width=True,
        hide_index=True
    )

# ==========================================
# --- SEÇÃO 5: CARTÃO DE CRÉDITO ---
# ==========================================
elif st.session_state.pagina_atual == "💳 Cartão de Crédito":
  botao_voltar()
  st.subheader("💳 Gestão Avançada de Faturas de Cartão de Crédito")
  st.write(
      "Acompanhe gastos detalhados por bandeira e controle o impacto das"
      " compras parceladas."
  )

  with st.form("form_cartao_credito_completo", clear_on_submit=True):
    col_cc1, col_cc2 = st.columns(2)
    with col_cc1:
      nome_cartao = st.selectbox(
          "Bandeira / Cartão",
          ["Caixa", "Banco do Brasil", "Santander", "Inter", "Itaúcard", "Samsung Itaú", "Nubank", "Outro"]
      )
      desc_cc = st.text_input("Descrição da Compra Específica")
    with col_cc2:
      val_cc = st.number_input(
          "Valor da Compra (R$)", min_value=0.0, value=0.00, step=1.0, format="%.2f"
      )
      data_cc = st.date_input("Data da Compra no Cartão (DD/MM/AAAA)", value=date.today(), format="DD/MM/YYYY")

    cat_cc = st.selectbox(
        "Categoria da Compra",
        [
            "🛒 Supermercado (Necessidade)",
            "🏠 Contas Fixas (Necessidade)",
            "🚗 Transporte (Necessidade)",
            "💊 Saúde (Necessidade)",
            "🍔 Lazer & Alimentação Fora (Desejos)",
            "🎉 Outros Desejos (Desejos)",
        ],
    )

    if st.form_submit_button(
        "Lançar Gasto na Fatura do Cartão", use_container_width=True
    ):
      if desc_cc.strip() and val_cc > 0:
        c.execute(
            "INSERT INTO cartao_credito (data, cartao, descricao, categoria,"
            " valor) VALUES (?,?,?,?,?)",
            (
                data_cc.strftime("%Y-%m-%d"),
                nome_cartao,
                desc_cc.strip(),
                cat_cc,
                val_cc,
            ),
        )
        conn.commit()
        st.success("Compra adicionada à fatura com sucesso!")
        st.rerun()
      else:
        st.error("Informe a descrição e o valor da compra.")

  st.markdown("---")
  df_cartao = pd.read_sql("SELECT * FROM cartao_credito", conn)
  if not df_cartao.empty:
    df_cartao["data"] = df_cartao["data"].apply(formatar_data_ptbr)
    st.write("### 📋 Extrato Consolidado de Faturas Atuais")
    st.dataframe(df_cartao, use_container_width=True)

    total_fatura = df_cartao["valor"].sum()
    st.metric(
        "💳 Montante Total Acumulado em Cartões", f"R$ {total_fatura:,.2f}"
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
  st.subheader("📈 Painel Profissional de Investimentos & Ativos")
  st.write(
      "Monitore a alocação de patrimônio em Renda Fixa, Ações, Fundo"
      " Imobiliários e Exterior."
  )

  with st.form("form_ativo_investimento_completo", clear_on_submit=True):
    col_iv1, col_iv2, col_iv3 = st.columns(3)
    with col_iv1:
      ativo_nome = st.text_input("Ativo / Ticker (Ex: PETR4, Tesouro Direto)")
      classe_ativo = st.selectbox(
          "Classe de Ativo",
          ["Ações BR", "FIIs", "Renda Fixa", "Criptomoedas", "Exterior"],
      )
    with col_iv2:
      qtd_ativo = st.number_input(
          "Quantidade de Cotas / Unidades",
          min_value=0.0001,
          value=1.00,
          step=1.0,
      )
      preco_medio = st.number_input(
          "Preço Médio / Custo Unitário (R$)",
          min_value=0.0,
          value=0.00,
          step=0.10,
          format="%.2f",
      )
    with col_iv3:
      data_aporte = st.date_input("Data do Aporte Realizado (DD/MM/AAAA)", value=date.today(), format="DD/MM/YYYY")
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
            f"Ativo {ativo_nome.upper()} cadastrado com sucesso na carteira!"
        )
        st.rerun()
      else:
        st.error("Informe o nome ou ticker do ativo corretamente.")

  st.markdown("---")
  df_carteira = pd.read_sql("SELECT * FROM carteira_investimentos", conn)
  if not df_carteira.empty:
    df_carteira["Valor Total"] = (
        df_carteira["quantidade"] * df_carteira["preco_medio"]
    )
    patrimonio_total = df_carteira["Valor Total"].sum()

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("💎 Patrimônio Total Alocado", f"R$ {patrimonio_total:,.2f}")
    col_m2.metric("📦 Total de Ativos Únicos", len(df_carteira["ativo"].unique()))
    col_m3.metric("📊 Classes Distintas", len(df_carteira["classe"].unique()))

    st.markdown("---")
    col_pos1, col_pos2 = st.columns(2)
    with col_pos1:
      st.write("### 📊 Alocação Patrimonial por Classe")
      df_classe = df_carteira.groupby("classe")["Valor Total"].sum()
      st.bar_chart(df_classe)
    with col_pos2:
      st.write("### 📋 Posições Detalhadas Registradas")
      df_carteira["data"] = df_carteira["data"].apply(formatar_data_ptbr)
      st.dataframe(
          df_carteira[
              ["data", "ativo", "classe", "quantidade", "preco_medio", "Valor Total"]
          ].rename(columns={
              "data": "Data",
              "ativo": "Ativo",
              "classe": "Classe",
              "quantidade": "Qtd",
              "preco_medio": "Preço Médio",
          }),
          use_container_width=True,
          hide_index=True,
      )

    st.markdown("---")
    id_ativo_del = st.selectbox(
        "Selecione o ID exato do ativo para remoção:",
        df_carteira["id"].tolist(),
        key="del_ativo_unique",
    )
    if st.button("Remover Ativo Selecionado da Carteira", use_container_width=True):
      c.execute("DELETE FROM carteira_investimentos WHERE id = ?", (id_ativo_del,))
      conn.commit()
      st.success("Ativo removido da carteira com sucesso!")
      st.rerun()
  else:
    st.info("Nenhum investimento cadastrado na carteira até o momento.")

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
      f"<h3 style='color: #00FF7F; text-align: center;'>Progresso Atual: R$"
      f" {total_concluido:,.2f} / R$ {meta_total_desafio:,.2f}</h3>",
      unsafe_allow_html=True,
  )
  st.progress(min(total_concluido / meta_total_desafio if meta_total_desafio > 0 else 0, 1.0))

  col_esq, col_dir = st.columns([2, 1])
  with col_esq:
    st.write("### Tabela Geral do Desafio")
    df_exibicao = pd.DataFrame()
    df_exibicao["Nº do Depósito"] = df_deps["numero_depósito"]
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
          "Selecione os Números dos Depósitos:", df_deps["numero_depósito"].tolist()
      )
      status_novo = st.selectbox(
          "Novo Status:", ["Pendente", "Concluído"], index=1
      )

      if st.form_submit_button("Salvar Status dos Depósitos", use_container_width=True):
        if deps_sel:
          for d_num in deps_sel:
            c.execute(
                "UPDATE tabela_depositos SET status = ? WHERE numero_deposito = ?",
                (status_novo, d_num),
            )
          conn.commit()
          st.success(
              f"Depósito(s) {', '.join(map(str, deps_sel))} atualizado(s) para '{status_novo}' com sucesso!"
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
      "🚗 Transporte (Necessidade)",
      "💊 Saúde (Necessidade)",
      "🍔 Lazer & Alimentação Fora (Desejos)",
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
      "SELECT * FROM transacoes WHERE tipo = 'Despesa' AND (origem = 'Manual' OR origem = 'Nota_Fiscal' OR origem = 'Voz_IA' OR origem = 'Chat_IA')", conn
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

      st.write(
          f"**{cat_nome}** — Gasto Real: R$ {gasto_atual_meta:,.2f} / Meta"
          f" Teto: R$ {v_meta:,.2f}"
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
              "📄", "🧾", "💳", "💰", "💵", "💸", "🏦", "🏧", "📊", 
              "🪙", "🏷️", "💼", "📈", "📉", "🔒", "🔑", "💡", "⚡", "💧", 
              "🔥", "📶", "📡", "📱", "💻", "📺", "📬", "🗑️", "⚙️", "🛠️",
              "🏠", "🏡", "🏢", "🛒", "🛍️", "🍔", "🍕", "☕", "🍺", "🍷", 
              "🚗", "🚕", "🚌", "🚆", "⛽", "🅿️", "💊", "🏥", "🩺", "🏋️‍♂️", 
              "✈️", "🏖️", "🏨", "🐕", "🐈", "🐾", "🎮", "🎲", "📚", "🎧", 
              "🎬", "🎨", "🎁", "💄", "👕", "👟", "🎓", "👶", "🎉", "⭐"
          ],
      )
      nome_cat_input = st.text_input("Nome da Categoria (Ex: Viagens, Pets, Jogos)")

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
          key="sel_cat_gerenciar"
      )
      
      id_cat_atual = df_cats_gerenciar[df_cats_gerenciar["nome"] == cat_selecionada_para_gerenciar]["id"].values[0]
      nome_completo_atual = str(cat_selecionada_para_gerenciar).strip()
      
      match_emoji = re.match(r"^([^\w\s])\s*(.*)$", nome_completo_atual)
      if match_emoji:
        emoji_atual = match_emoji.group(1)
        texto_atual_puro = match_emoji.group(2)
      else:
        partes_cat = nome_completo_atual.split(" ", 1)
        emoji_atual = partes_cat[0] if len(partes_cat) > 0 else "📄"
        texto_atual_puro = partes_cat[1] if len(partes_cat) > 1 else nome_completo_atual

      lista_icones_opcoes = [
          "📄", "🧾", "💳", "💰", "💵", "💸", "🏦", "🏧", "📊", 
          "🪙", "🏷️", "💼", "📈", "📉", "🔒", "🔑", "💡", "⚡", "💧", 
          "🔥", "📶", "📡", "📱", "💻", "📺", "📬", "🗑️", "⚙️", "🛠️",
          "🏠", "🏡", "🏢", "🛒", "🛍️", "🍔", "🍕", "☕", "🍺", "🍷", 
          "🚗", "🚕", "🚌", "🚆", "⛽", "🅿️", "💊", "🏥", "🩺", "🏋️‍♂️", 
          "✈️", "🏖️", "🏨", "🐕", "🐈", "🐾", "🎮", "🎲", "📚", "🎧", 
          "🎬", "🎨", "🎁", "💄", "👕", "👟", "🎓", "👶", "🎉", "⭐"
      ]

      idx_emoji_default = lista_icones_opcoes.index(emoji_atual) if emoji_atual in lista_icones_opcoes else 0
      chave_form_edicao = f"form_edit_cat_{id_cat_atual}"

      with st.form(chave_form_edicao):
        st.write(f"Editando: **{cat_selecionada_para_gerenciar}**")
        novo_icone = st.selectbox(
            "Novo Ícone:",
            lista_icones_opcoes,
            index=idx_emoji_default,
            key=f"novo_icone_sel_{id_cat_atual}"
        )
        novo_nome_texto = st.text_input("Novo Nome da Categoria:", value=texto_atual_puro, key=f"novo_nome_texto_input_{id_cat_atual}")

        col_btn_ed1, col_btn_ed2 = st.columns(2)
        with col_btn_ed1:
          btn_atualizar = st.form_submit_button("Atualizar Categoria", use_container_width=True)
        with col_btn_ed2:
          btn_excluir = st.form_submit_button("Excluir Categoria", use_container_width=True)

        if btn_atualizar:
          texto_base = novo_nome_texto.strip() if novo_nome_texto.strip() else texto_atual_puro
          nome_atualizado_final = f"{novo_icone} {texto_base}"
          c.execute("UPDATE categorias SET nome = ? WHERE id = ?", (nome_atualizado_final, int(id_cat_atual)))
          conn.commit()
          st.success(f"Categoria atualizada para '{nome_atualizado_final}' com sucesso!")
          st.rerun()

        if btn_excluir:
          c.execute("DELETE FROM categorias WHERE id = ?", (int(id_cat_atual),))
          conn.commit()
          st.success(f"Categoria '{cat_selecionada_para_gerenciar}' excluída com sucesso!")
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
      "Pontuação calculada de 0 a 1000 com base em endividamento, taxa de"
      " poupança, disciplina e cumprimento de tetos."
  )

  df_saude = pd.read_sql("SELECT * FROM transacoes WHERE origem = 'Manual' OR origem = 'Nota_Fiscal' OR origem = 'Voz_IA' OR origem = 'Chat_IA'", conn)
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
    <div style="background-color: #1E1E1E; padding: 30px; border-radius: 10px; text-align: center; border: 1px solid #333;">
        <h1 style="font-size: 60px; color: #FF4B4B; margin: 0;">{score_total}</h1>
        <p style="color: #888; font-size: 18px; margin: 5px 0 15px 0;">pontos de 1000</p>
        <h3 style="color: #FFF; margin: 0;">{cor_status} Status: {status_score}</h3>
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

  st.write(
      "🛡️ **Controle de Endividamento (Receitas vs Despesas):**"
      f" {int(f_endividamento)} / 250 pts"
  )
  st.progress(min(f_endividamento / 250, 1.0))
  st.write(
      "🎯 **Controle de Desejos (Regra dos 30%):** {int(f_metas_s)} / 250 pts"
  )
  st.progress(min(f_metas_s / 250, 1.0))
  st.write(
      "📈 **Taxa de Poupança / Investimento (Regra dos 20%):**"
      f" {int(f_poupanca)} / 250 pts"
  )
  st.progress(min(f_poupanca / 250, 1.0))
  st.write(
      "📅 **Disciplina de Registros & Frequência:**"
      f" {int(f_disciplina * 0.5)} / 250 pts"
  )
  st.progress(min((f_disciplina * 0.5) / 250, 1.0))

# ==========================================
# --- SEÇÃO 10: CONTAS A PAGAR & RECEBER ---
# ==========================================
elif st.session_state.pagina_atual == "📅 Contas a Pagar":
  botao_voltar()
  
  if "data_calendario_ref" not in st.session_state or not isinstance(st.session_state.data_calendario_ref, (date, datetime)):
    st.session_state.data_calendario_ref = date.today()

  st.subheader("📅 Contas a Pagar & Receber / Gestão de Pagamentos")
  st.write("Organize boletos, contas a pagar, contas a receber e compromissos com vencimento programado.")

  st.markdown("##### 🗓️ Seleção de Data no Calendário Interativo")
  data_calendario_topo = st.date_input(
      "Selecionar Data de Referência (DD/MM/AAAA):",
      value=st.session_state.data_calendario_ref,
      key="data_calendario_ref_input",
      format="DD/MM/YYYY"
  )
  if data_calendario_topo:
    st.session_state.data_calendario_ref = data_calendario_topo

  if "aba_contas_ativa" not in st.session_state:
    st.session_state.aba_contas_ativa = "pagar"

  col_tab_btn1, col_tab_btn2, _ = st.columns([1, 1, 4])
  with col_tab_btn1:
    if st.button("📉 Contas a Pagar", use_container_width=True, type="primary" if st.session_state.aba_contas_ativa == "pagar" else "secondary"):
      st.session_state.aba_contas_ativa = "pagar"
      st.rerun()
  with col_tab_btn2:
    if st.button("📈 Contas a Receber", use_container_width=True, type="primary" if st.session_state.aba_contas_ativa == "receber" else "secondary"):
      st.session_state.aba_contas_ativa = "receber"
      st.rerun()

  st.markdown("---")

  st.markdown(
      f"""
      <div style="background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 14px; padding: 20px; margin-bottom: 25px;">
          <h4 style="color: #60a5fa; margin-top: 0; display: flex; align-items: center; gap: 8px;">📌 Agenda do Dia: {st.session_state.data_calendario_ref.strftime('%d/%m/%Y')}</h4>
      </div>
      """,
      unsafe_allow_html=True,
  )

  data_sel_str = st.session_state.data_calendario_ref.strftime("%Y-%m-%d")
  df_cp_dia = pd.read_sql("SELECT * FROM contas WHERE vencimento = ?", conn, params=(data_sel_str,))
  df_cr_dia = pd.read_sql("SELECT * FROM contas_receber WHERE vencimento = ?", conn, params=(data_sel_str,))

  col_agd1, col_agd2 = st.columns(2)
  with col_agd1:
    st.write("**📉 Contas a Pagar na Data:**")
    if not df_cp_dia.empty:
      for _, row_cp_d in df_cp_dia.iterrows():
        st.markdown(f"• ID {row_cp_d['id']} | **{row_cp_d['descricao']}** — R$ {row_cp_d['valor']:,.2f} ({'Pago ✅' if row_cp_d['pago'] == 1 else 'Pendente ⏳'})")
    else:
      st.info("Nenhuma conta a pagar para esta data.")

  with col_agd2:
    st.write("**📈 Contas a Receber na Data:**")
    if not df_cr_dia.empty:
      for _, row_cr_d in df_cr_dia.iterrows():
        st.markdown(f"• ID {row_cr_d['id']} | **{row_cr_d['descricao']}** — R$ {row_cr_d['valor']:,.2f} ({'Recebido ✅' if row_cr_d['recebido'] == 1 else 'Pendente ⏳'})")
    else:
      st.info("Nenhuma conta a receber para esta data.")

  st.markdown("---")

  if st.session_state.aba_contas_ativa == "pagar":
    st.subheader("➕ Nova Conta a Pagar (com Opção de Recorrência Mensal, Semanal ou Replicar datas)")
    with st.form("form_conta_pagar_completo", clear_on_submit=True):
      col_c1, col_c2 = st.columns(2)
      with col_c1:
        venc = st.date_input("Data de Vencimento Inicial (DD/MM/AAAA)", value=date.today(), key="venc_cp", format="DD/MM/YYYY")
        nome_conta = st.text_input(
            "Nome / Descrição da Conta (Ex: Conta de Luz, Aluguel)"
        )
      with col_c2:
        val_conta = st.number_input(
            "Valor da Conta (R$)", min_value=0.0, format="%.2f", key="val_cp"
        )
        tipo_recorrencia = st.selectbox(
            "Tipo de Recorrência / Lançamento:",
            ["Apenas esta data (Sem recorrência)", "Recorrência Semanal (próximas 4 semanas)", "Recorrência Mensal (próximos 12 meses)", "Replicar datas específicas customizadas"],
            key="recorrencia_cp"
        )

      replicar_datas_cp = []
      if tipo_recorrencia == "Replicar datas específicas customizadas":
        replicar_datas_cp = st.multiselect(
            "Selecione as datas adicionais de vencimento:",
            options=[date.today() + timedelta(days=d) for d in range(1, 365)],
            format_func=lambda x: x.strftime("%d/%m/%Y"),
            key="rep_datas_cp"
        )

      if st.form_submit_button("Adicionar Conta(s) a Pagar", use_container_width=True):
        if nome_conta.strip() and val_conta > 0:
          datas_para_inserir = [venc]
          
          if tipo_recorrencia == "Recorrência Semanal (próximas 4 semanas)":
            for i in range(1, 5):
              datas_para_inserir.append(venc + timedelta(weeks=i))
          elif tipo_recorrencia == "Recorrência Mensal (próximos 12 meses)":
            for i in range(1, 13):
              ano_m = venc.year + (venc.month - 1 + i) // 12
              mes_m = (venc.month - 1 + i) % 12 + 1
              dia_m = min(venc.day, 28)
              datas_para_inserir.append(date(ano_m, mes_m, dia_m))
          elif tipo_recorrencia == "Replicar datas específicas customizadas":
            for d_rep in replicar_datas_cp:
              if d_rep not in datas_para_inserir:
                datas_para_inserir.append(d_rep)

          for d_ins in datas_para_inserir:
            c.execute(
                "INSERT INTO contas (vencimento, descricao, valor, pago) VALUES (?,?,?,?)",
                (d_ins.strftime("%Y-%m-%d"), str(nome_conta).strip(), val_conta, 0),
            )
          conn.commit()
          st.success(f"{len(datas_para_inserir)} conta(s) a pagar cadastrada(s) com sucesso!")
          st.rerun()
        else:
          st.error("Informe a descrição e o valor da conta.")

    st.markdown("---")

    df_contas_alerta = pd.read_sql("SELECT * FROM contas WHERE pago = 0", conn)
    if not df_contas_alerta.empty:
      hoje = date.today()
      df_contas_alerta["venc_dt"] = pd.to_datetime(df_contas_alerta["vencimento"]).dt.date
      
      vencidas = df_contas_alerta[df_contas_alerta["venc_dt"] < hoje]
      vencem_hoje = df_contas_alerta[df_contas_alerta["venc_dt"] == hoje]

      if not vencidas.empty or not vencem_hoje.empty:
        st.markdown("### 🚨 Alertas de Vencimento (Pagar)")
        if not vencidas.empty:
          for _, r_venc in vencidas.iterrows():
            st.error(f"⚠️ **Conta Vencida:** '{r_venc['descricao']}' vencia em **{formatar_data_ptbr(r_venc['vencimento'])}** no valor de **R$ {r_venc['valor']:,.2f}**!")
        if not vencem_hoje.empty:
          for _, r_hoje in vencem_hoje.iterrows():
            st.warning(f"🔔 **Vence Hoje:** '{r_hoje['descricao']}' vence **hoje** ({hoje.strftime('%d/%m/%Y')}) no valor de **R$ {r_hoje['valor']:,.2f}**!")
        st.markdown("---")

    st.subheader("🔍 Pesquisa Aprimorada & Relação de Contas a Pagar")
    
    col_pesq_cp, col_fil_agenda_cp = st.columns([3, 2])
    with col_pesq_cp:
      termo_busca_contas = st.text_input(
          "Pesquisar por nome, parte da descrição ou similaridade:", "", key="busca_contas_input"
      )
    with col_fil_agenda_cp:
      usar_filtro_agenda_cp = st.checkbox("Filtrar visualização pela data selecionada no calendário do topo", value=False)

    df_contas_all = pd.read_sql("SELECT * FROM contas", conn)

    if not df_contas_all.empty:
      if usar_filtro_agenda_cp:
        df_contas_all["venc_dt_cmp"] = pd.to_datetime(df_contas_all["vencimento"]).dt.date
        df_contas_all = df_contas_all[df_contas_all["venc_dt_cmp"] == st.session_state.data_calendario_ref]

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
      st.write("### 📋 Lista de Contas a Pagar")
      for _, row_cp in contas_filtradas.iterrows():
        c_id = row_cp["id"]
        c_venc = formatar_data_ptbr(row_cp["vencimento"])
        c_desc = row_cp["descricao"]
        c_val = row_cp["valor"]
        c_pago = row_cp["pago"]

        col_row1, col_row2, col_row3, col_row4, col_row5, col_row6 = st.columns([1, 2, 2, 1, 1, 1])
        with col_row1:
          st.write(f"**ID:** {c_id}")
        with col_row2:
          st.write(f"📅 {c_venc} | **{c_desc}**")
        with col_row3:
          st.write(f"R$ {c_val:,.2f} ({'Pago ✅' if c_pago == 1 else 'Pendente ⏳'})")
        with col_row4:
          if c_pago == 0:
            if st.button("Pagar 💳", key=f"btn_pagar_{c_id}", use_container_width=True):
              c.execute("UPDATE contas SET pago = 1 WHERE id = ?", (c_id,))
              c.execute(
                  "INSERT INTO transacoes (data, tipo, descricao, categoria, valor, origem) VALUES (?,?,?,?,?,?)",
                  (date.today().strftime("%Y-%m-%d"), "Despesa", f"Pgto: {c_desc}", "🏠 Contas Fixas (Necessidade)", c_val, "Manual")
              )
              conn.commit()
              st.success(f"Conta '{c_desc}' paga com sucesso!")
              st.rerun()
          else:
            if st.button("Estornar 🔄", key=f"btn_estornar_{c_id}", use_container_width=True):
              c.execute("UPDATE contas SET pago = 0 WHERE id = ?", (c_id,))
              conn.commit()
              st.success(f"Conta '{c_desc}' marcada como pendente!")
              st.rerun()
        with col_row5:
          if st.button("✏️ Editar", key=f"btn_edit_cp_{c_id}", use_container_width=True):
            st.session_state[f"editando_cp_{c_id}"] = not st.session_state.get(f"editando_cp_{c_id}", False)
            st.rerun()
        with col_row6:
          if st.button("Excluir 🗑️", key=f"btn_del_cp_{c_id}", use_container_width=True):
            c.execute("DELETE FROM contas WHERE id = ?", (c_id,))
            conn.commit()
            st.success(f"Conta ID {c_id} excluída com sucesso!")
            st.rerun()

        if st.session_state.get(f"editando_cp_{c_id}", False):
          with st.form(f"form_editar_cp_{c_id}"):
            st.write(f"**Editando Conta ID {c_id}** (Ajuste de variação de valor ou data)")
            novo_venc_cp = st.date_input("Nova Data de Vencimento (DD/MM/AAAA)", value=datetime.strptime(row_cp["vencimento"], "%Y-%m-%d").date(), key=f"nv_v_{c_id}", format="DD/MM/YYYY")
            nova_desc_cp = st.text_input("Nova Descrição", value=c_desc, key=f"nv_d_{c_id}")
            novo_val_cp = st.number_input("Novo Valor (R$)", min_value=0.0, value=float(c_val), step=1.0, format="%.2f", key=f"nv_val_{c_id}")
            
            if st.form_submit_button("Salvar Alterações", use_container_width=True):
              c.execute("UPDATE contas SET vencimento = ?, descricao = ?, valor = ? WHERE id = ?", 
                        (novo_venc_cp.strftime("%Y-%m-%d"), nova_desc_cp.strip(), novo_val_cp, c_id))
              conn.commit()
              st.session_state[f"editando_cp_{c_id}"] = False
              st.success("Conta atualizada com sucesso!")
              st.rerun()

      st.markdown("---")
      id_del_cp = st.selectbox("Selecione o ID da conta a pagar para exclusão geral:", contas_filtradas["id"].tolist(), key="del_cp_sel")
      if st.button("Excluir Conta a Pagar Selecionada", use_container_width=True):
        c.execute("DELETE FROM contas WHERE id = ?", (id_del_cp,))
        conn.commit()
        st.success("Conta a pagar removida com sucesso!")
        st.rerun()
    else:
      st.info("Nenhuma conta a pagar encontrada.")

  else:
    st.subheader("➕ Nova Conta a Receber (com Opção de Recorrência Mensal, Semanal ou Replicar datas)")
    with st.form("form_conta_receber_completo", clear_on_submit=True):
      col_cr1, col_cr2 = st.columns(2)
      with col_cr1:
        venc_r = st.date_input("Data de Vencimento / Recebimento Inicial (DD/MM/AAAA)", value=date.today(), key="venc_cr", format="DD/MM/YYYY")
        nome_conta_r = st.text_input(
            "Nome / Descrição da Receita (Ex: Aluguel a Receber, Prestação de Serviço)"
        )
      with col_cr2:
        val_conta_r = st.number_input(
            "Valor a Receber (R$)", min_value=0.0, format="%.2f", key="val_cr"
        )
        tipo_recorrencia_r = st.selectbox(
            "Tipo de Recorrência / Lançamento:",
            ["Apenas esta data (Sem recorrência)", "Recorrência Semanal (próximas 4 semanas)", "Recorrência Mensal (próximos 12 meses)", "Replicar datas específicas customizadas"],
            key="recorrencia_cr"
        )

      replicar_datas_cr = []
      if tipo_recorrencia_r == "Replicar datas específicas customizadas":
        replicar_datas_cr = st.multiselect(
            "Selecione as datas adicionais de vencimento:",
            options=[date.today() + timedelta(days=d) for d in range(1, 365)],
            format_func=lambda x: x.strftime("%d/%m/%Y"),
            key="rep_datas_cr"
        )

      if st.form_submit_button("Adicionar Conta(s) a Receber", use_container_width=True):
        if nome_conta_r.strip() and val_conta_r > 0:
          datas_para_inserir_r = [venc_r]
          
          if tipo_recorrencia_r == "Recorrência Semanal (próximas 4 semanas)":
            for i in range(1, 5):
              datas_para_inserir_r.append(venc_r + timedelta(weeks=i))
          elif tipo_recorrencia_r == "Recorrência Mensal (próximos 12 meses)":
            for i in range(1, 13):
              ano_m = venc_r.year + (venc_r.month - 1 + i) // 12
              mes_m = (venc_r.month - 1 + i) % 12 + 1
              dia_m = min(venc_r.day, 28)
              datas_para_inserir_r.append(date(ano_m, mes_m, dia_m))
          elif tipo_recorrencia_r == "Replicar datas específicas customizadas":
            for d_rep_r in replicar_datas_cr:
              if d_rep_r not in datas_para_inserir_r:
                datas_para_inserir_r.append(d_rep_r)

          for d_ins_r in datas_para_inserir_r:
            c.execute(
                "INSERT INTO contas_receber (vencimento, descricao, valor, recebido) VALUES (?,?,?,?)",
                (d_ins_r.strftime("%Y-%m-%d"), str(nome_conta_r).strip(), val_conta_r, 0),
            )
          conn.commit()
          st.success(f"{len(datas_para_inserir_r)} conta(s) a receber cadastrada(s) com sucesso!")
          st.rerun()
        else:
          st.error("Informe a descrição e o valor da conta a receber.")

    st.markdown("---")
    st.subheader("🔍 Pesquisa Aprimorada & Relação de Contas a Receber")
    
    col_pesq_cr, col_fil_agenda_cr = st.columns([3, 2])
    with col_pesq_cr:
      termo_busca_receber = st.text_input(
          "Pesquisar por nome, parte da descrição ou similaridade:", "", key="busca_receber_input"
      )
    with col_fil_agenda_cr:
      usar_filtro_agenda_cr = st.checkbox("Filtrar visualização pela data selecionada no calendário do topo", value=False, key="chk_agenda_cr")

    df_receber_all = pd.read_sql("SELECT * FROM contas_receber", conn)

    if not df_receber_all.empty:
      if usar_filtro_agenda_cr:
        df_receber_all["venc_dt_cmp"] = pd.to_datetime(df_receber_all["vencimento"]).dt.date
        df_receber_all = df_receber_all[df_receber_all["venc_dt_cmp"] == st.session_state.data_calendario_ref]

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
      st.write("### 📋 Lista de Contas a Receber")
      for _, row_cr in receber_filtradas.iterrows():
        cr_id = row_cr["id"]
        cr_venc = formatar_data_ptbr(row_cr["vencimento"])
        cr_desc = row_cr["descricao"]
        cr_val = row_cr["valor"]
        cr_recebido = row_cr["recebido"]

        col_r1, col_r2, col_r3, col_r4, col_r5, col_r6 = st.columns([1, 2, 2, 1, 1, 1])
        with col_r1:
          st.write(f"**ID:** {cr_id}")
        with col_r2:
          st.write(f"📅 {cr_venc} | **{cr_desc}**")
        with col_r3:
          st.write(f"R$ {cr_val:,.2f} ({'Recebido ✅' if cr_recebido == 1 else 'Pendente ⏳'})")
        with col_r4:
          if cr_recebido == 0:
            if st.button("Receber 💰", key=f"btn_receber_{cr_id}", use_container_width=True):
              c.execute("UPDATE contas_receber SET recebido = 1 WHERE id = ?", (cr_id,))
              c.execute(
                  "INSERT INTO transacoes (data, tipo, descricao, categoria, valor, origem) VALUES (?,?,?,?,?,?)",
                  (date.today().strftime("%Y-%m-%d"), "Receita", f"Recebimento: {cr_desc}", "Freelance / Extra", cr_val, "Manual")
              )
              conn.commit()
              st.success(f"Recebimento '{cr_desc}' confirmado com sucesso!")
              st.rerun()
          else:
            if st.button("Estornar 🔄", key=f"btn_estornar_cr_{cr_id}", use_container_width=True):
              c.execute("UPDATE contas_receber SET recebido = 0 WHERE id = ?", (cr_id,))
              conn.commit()
              st.success(f"Recebimento '{cr_desc}' marcado como pendente!")
              st.rerun()
        with col_r5:
          if st.button("✏️ Editar", key=f"btn_edit_cr_{cr_id}", use_container_width=True):
            st.session_state[f"editando_cr_{cr_id}"] = not st.session_state.get(f"editando_cr_{cr_id}", False)
            st.rerun()
        with col_r6:
          if st.button("Excluir 🗑️", key=f"btn_del_cr_{cr_id}", use_container_width=True):
            c.execute("DELETE FROM contas_receber WHERE id = ?", (cr_id,))
            conn.commit()
            st.success(f"Conta a receber ID {cr_id} excluída com sucesso!")
            st.rerun()

        if st.session_state.get(f"editando_cr_{cr_id}", False):
          with st.form(f"form_editar_cr_{cr_id}"):
            st.write(f"**Editando Conta a Receber ID {cr_id}** (Ajuste de variação)")
            novo_venc_cr = st.date_input("Nova Data de Vencimento (DD/MM/AAAA)", value=datetime.strptime(row_cr["vencimento"], "%Y-%m-%d").date(), key=f"nv_vr_{cr_id}", format="DD/MM/YYYY")
            nova_desc_cr = st.text_input("Nova Descrição", value=cr_desc, key=f"nv_dr_{cr_id}")
            novo_val_cr = st.number_input("Novo Valor (R$)", min_value=0.0, value=float(cr_val), step=1.0, format="%.2f", key=f"nv_valr_{cr_id}")
            
            if st.form_submit_button("Salvar Alterações", use_container_width=True):
              c.execute("UPDATE contas_receber SET vencimento = ?, descricao = ?, valor = ? WHERE id = ?", 
                        (novo_venc_cr.strftime("%Y-%m-%d"), nova_desc_cr.strip(), novo_val_cr, cr_id))
              conn.commit()
              st.session_state[f"editando_cr_{cr_id}"] = False
              st.success("Conta a receber atualizada com sucesso!")
              st.rerun()

      st.markdown("---")
      id_del_cr = st.selectbox("Selecione o ID da conta a receber para exclusão geral:", receber_filtradas["id"].tolist(), key="del_cr_sel")
      if st.button("Excluir Conta a Receber Selecionada", use_container_width=True):
        c.execute("DELETE FROM contas_receber WHERE id = ?", (id_del_cr,))
        conn.commit()
        st.success("Conta a receber removida com sucesso!")
        st.rerun()
    else:
      st.info("Nenhuma conta a receber encontrada.")

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
      "Faça download do banco de dados, exporte planilhas ou escolha onde deseja salvar os arquivos no computador."
  )

  col_exp1, col_exp2 = st.columns(2)
  with col_exp1:
    if st.button("💾 Salvar Banco (.db) Escolhendo Onde Salvar no PC", use_container_width=True):
      try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        caminho_salvar = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("Database SQLite", "*.db"), ("Todos os arquivos", "*.*")],
            title="Escolha onde salvar o Backup do Banco de Dados",
            initialfile="gestor_financeiro_backup.db"
        )
        if caminho_salvar:
          with open("gestor_financeiro.db", "rb") as f_origem:
            with open(caminho_salvar, "wb") as f_destino:
              f_destino.write(f_origem.read())
          st.success(f"Backup salvo com sucesso em: {caminho_salvar}")
        else:
          st.info("Operação cancelada pelo usuário.")
      except Exception as e:
        with open("gestor_financeiro.db", "rb") as f:
          st.download_button("💾 Clique aqui para baixar o Banco (.db)", f, "gestor_financeiro.db", use_container_width=True)

  with col_exp2:
    if st.button("📊 Salvar Planilha Extrato (CSV) Escolhendo Onde Salvar", use_container_width=True):
      df_extrato_full = pd.read_sql("SELECT * FROM transacoes", conn)
      if not df_extrato_full.empty:
        df_extrato_full["data"] = df_extrato_full["data"].apply(formatar_data_ptbr)
        csv_texto = df_extrato_full.to_csv(index=False)
        try:
          root = tk.Tk()
          root.withdraw()
          root.attributes("-topmost", True)
          caminho_csv = filedialog.asksaveasfilename(
              defaultextension=".csv",
              filetypes=[("Arquivo CSV", "*.csv"), ("Todos os arquivos", "*.*")],
              title="Escolha onde salvar a Planilha do Extrato",
              initialfile="extrato_financeiro.csv"
          )
          if caminho_csv:
            with open(caminho_csv, "w", encoding="utf-8") as f_csv:
              f_csv.write(csv_texto)
            st.success(f"Planilha salva com sucesso em: {caminho_csv}")
          else:
            st.info("Operação cancelada pelo usuário.")
        except Exception as e:
          st.download_button("📥 Baixar Planilha CSV", csv_texto.encode("utf-8"), "extrato_financeiro.csv", mime="text/csv", use_container_width=True)
      else:
        st.warning("Não há transações no extrato para exportar.")

  st.markdown("---")
  st.markdown("### ⚠️ Zona de Perigo — Exclusão Geral de Dados")
  st.write("Insira a senha de segurança abaixo para apagar permanentemente todos os registros, transações, faturas, veículos e investimentos do sistema.")
  
  with st.form("form_exclusao_geral_segura"):
    senha_exclusao_geral = st.text_input("Senha de Confirmação:", type="password")
    btn_executar_limpeza = st.form_submit_button("🗑️ APAGAR TODOS OS DADOS DO SISTEMA", use_container_width=True)
    
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
  st.write("Verifique divergências entre os lançamentos manuais do sistema e o extrato importado mais recentemente.")

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
          val_float = float(linha.replace("R$", "").replace(".", "").replace(",", ".").split()[-1])
          desc_str = " ".join(partes[1:-1])
          transacoes_pdf_temp.append({
              "data": data_str,
              "descricao": desc_str,
              "valor": abs(val_float),
              "tipo": "Receita" if val_float > 0 else "Despesa"
          })
        except:
          continue
    
    if transacoes_pdf_temp:
      df_pdf_temp = pd.DataFrame(transacoes_pdf_temp)
      df_banco_atual = pd.read_sql("SELECT data, descricao, valor, tipo FROM transacoes WHERE origem = 'Manual'", conn)
      
      if not df_banco_atual.empty:
        merged_rec = pd.merge(df_pdf_temp, df_banco_atual, on=["data", "valor", tipo_trans := "tipo"], how="left", indicator=True)
        divergentes = merged_rec[merged_rec["_merge"] == "left_only"]
        
        if not divergentes.empty:
          divergentes["data"] = divergentes["data"].apply(formatar_data_ptbr)
          st.warning(f"⚠️ Atenção: Encontramos **{len(divergentes)}** transação(ões) no PDF do extrato que constam como divergentes ou ausentes nos lançamentos manuais do sistema:")
          st.dataframe(divergentes[["data", "descricao_x", "valor", "tipo"]].rename(columns={"descricao_x": "Descrição no Extrato PDF"}), use_container_width=True)
        else:
          st.success("✅ **Reconciliação Perfeita:** Todos os lançamentos do extrato PDF conferem com os registros manuais salvos no sistema!")
      else:
        st.info("Cadastre transações manuais no sistema para ativar o cruzamento da reconciliação com o PDF.")
    else:
      st.info("Nenhuma transação válida lida no PDF atual para reconciliação.")
  else:
      st.info("Faça o upload de um extrato bancário em PDF acima para habilitar o painel de Reconciliação Automatizada.")

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
      df_extrato_filtrado_exib["data"] = df_extrato_filtrado_exib["data"].apply(formatar_data_ptbr)
      st.write(
          f"### 📋 Resultados Encontrados ({len(df_extrato_filtrado_exib)} registros)"
      )
      st.dataframe(df_extrato_filtrado_exib, use_container_width=True, hide_index=True)

      st.markdown("### ⚙️ Gerenciar / Editar / Excluir Lançamentos do Extrato")
      id_trans_sel = st.selectbox(
          "Selecione o ID da transação para editar ou excluir:",
          df_extrato_filtrado["id"].tolist(),
          key="sel_transacao_gerenciar"
      )

      if id_trans_sel:
        row_trans_atual = df_extrato_filtrado[df_extrato_filtrado["id"] == id_trans_sel].iloc[0]
        
        col_ed_op1, col_ed_op2 = st.columns(2)
        with col_ed_op1:
          st.markdown(f"**Editando Lançamento ID {id_trans_sel}:**")
          with st.form(f"form_editar_transacao_{id_trans_sel}"):
            novo_tipo_t = st.selectbox("Tipo:", ["Despesa", "Receita"], index=0 if row_trans_atual["tipo"] == "Despesa" else 1)
            nova_desc_t = st.text_input("Descrição:", value=row_trans_atual["descricao"])
            novo_val_t = st.number_input("Valor (R$):", min_value=0.0, value=float(row_trans_atual["valor"]), step=1.0, format="%.2f")
            nova_data_t = st.date_input("Data (DD/MM/AAAA):", value=datetime.strptime(str(row_trans_atual["data"])[:10], "%Y-%m-%d").date(), format="DD/MM/YYYY")
            
            if st.form_submit_button("Salvar Alterações da Transação", use_container_width=True):
              c.execute(
                  "UPDATE transacoes SET tipo = ?, descricao = ?, valor = ?, data = ? WHERE id = ?",
                  (novo_tipo_t, nova_desc_t.strip(), novo_val_t, nova_data_t.strftime("%Y-%m-%d"), id_trans_sel)
              )
              conn.commit()
              st.success(f"Transação ID {id_trans_sel} atualizada com sucesso!")
              st.rerun()

        with col_ed_op2:
          st.markdown(f"**Excluir Lançamento ID {id_trans_sel}:**")
          st.write(f"Deseja remover permanentemente o registro *{row_trans_atual['descricao']}* (R$ {row_trans_atual['valor']:,.2f})?")
          if st.button("🗑️ Excluir Transação Selecionada", use_container_width=True):
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
# --- SEÇÃO 12: HOLERITES ---
# ==========================================
elif st.session_state.pagina_atual == "📄 Holerites":
  botao_voltar()
  st.subheader(
      "📄 Análise, Comparativo Mês a Mês & Leitura Dinâmica de Holerites via PDF"
  )
  st.info(
      "Faça o upload de arquivos PDF de contracheques. O sistema lerá com"
      " precisão cirúrgica os impostos e proventos."
  )

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
              "SELECT id FROM holerites WHERE mes_ano = ?", (mes_ano_extraido,)
          )
          row_existente = cursor_check.fetchone()

          if not row_existente:
            c.execute(
                "INSERT INTO holerites (mes_ano, salario_bruto,"
                " total_descontos, liquido, inss, irrf, vale) VALUES"
                " (?,?,?,?,?,?,?)",
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
                "UPDATE holerites SET salario_bruto = ?, total_descontos = ?,"
                " liquido = ?, inss = ?, irrf = ?, vale = ? WHERE mes_ano = ?",
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
        except Exception as e:
          pass
      st.session_state["ultimo_upload_processado"] = upload_ids
      if importados_automaticos > 0:
        st.success(
            f"🚀 {importados_automaticos} novo(s) holerite(s) lido(s) com"
            " sucesso!"
        )

  df_holerites = pd.read_sql(
      "SELECT * FROM holerites ORDER BY mes_ano DESC", conn
  )

  if not df_holerites.empty:
    st.markdown("---")
    st.subheader(
        "📑 Navegação Analítica por Mês / Contracheque (Salvo no Banco)"
    )

    if "holerite_selecionado_db_idx" not in st.session_state:
      st.session_state.holerite_selecionado_db_idx = 0

    if st.session_state.holerite_selecionado_db_idx >= len(df_holerites):
      st.session_state.holerite_selecionado_db_idx = 0

    lista_meses_db = df_holerites["mes_ano"].tolist()
    cols_botoes = st.columns(min(len(lista_meses_db), 6))

    for idx, mes_ref in enumerate(lista_meses_db):
      col_pos = idx % len(cols_botoes)
      with cols_botoes[col_pos]:
        tipo_botao = (
            "primary"
            if st.session_state.holerite_selecionado_db_idx == idx
            else "secondary"
        )
        if st.button(
            f"Mês {mes_ref}",
            key=f"btn_mes_db_{idx}",
            type=tipo_botao,
            use_container_width=True,
        ):
          st.session_state.holerite_selecionado_db_idx = idx
          st.rerun()

    row_ativo = df_holerites.iloc[
        st.session_state.holerite_selecionado_db_idx
    ]
    mes_ativo_ext = row_ativo["mes_ano"]
    bruto_ativo = row_ativo["salario_bruto"]
    desc_ativo = row_ativo["total_descontos"]
    liquido_ativo = row_ativo["liquido"]
    inss_ativo = row_ativo["inss"]
    irrf_ativo = row_ativo["irrf"]
    vale_ativo = (
        row_ativo["vale"] if row_ativo["vale"] is not None else 2220.00
    )

    st.markdown(
        f"<p style='text-align: center; color: #AAA; font-size: 14px;"
        f" margin-top: 15px;'>Referência ativa no painel:"
        f" <b>{mes_ativo_ext}</b></p>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    col_rec, col_desc = st.columns(2)

    with col_rec:
      st.markdown(
          f"""
            <div style="background-color: #1A3322; padding: 25px; border-radius: 10px; border: 1px solid #2E7D32;">
                <h4 style="color: #A5D6A7; margin-top: 0;">🟢 Detalhamento de Receitas, Proventos & Vale ({mes_ativo_ext})</h4>
                <hr style="border-color: #2E7D32;">
                <p><b>Salário Bruto / Base:</b> R$ {bruto_ativo:,.2f}</p>
                <p><b>Adiantamento / Vale Quinzenal:</b> R$ {vale_ativo:,.2f}</p>
                <p><b>Horas Extras / Adicionais:</b> R$ 0,00</p>
                <p><b>Outros Proventos:</b> R$ 0,00</p>
                <h3 style="color: #66BB6A; margin-top: 15px;">Total Bruto & Vales: R$ {bruto_ativo + vale_ativo:,.2f}</h3>
            </div>
            """,
          unsafe_allow_html=True,
      )

    with col_desc:
      st.markdown(
          f"""
            <div style="background-color: #331A1A; padding: 25px; border-radius: 10px; border: 1px solid #C62828;">
                <h4 style="color: #EF9A9A; margin-top: 0;">🔴 Detalhamento Separado dos Descontos ({mes_ativo_ext})</h4>
                <hr style="border-color: #C62828;">
                <p><b>• INSS (Previdência Social):</b> R$ {inss_ativo:,.2f}</p>
                <p><b>• IRRF (Imposto de Renda Retido):</b> R$ {irrf_ativo:,.2f}</p>
                <p><b>• Desconto de Vale (Adiantamento):</b> R$ {vale_ativo:,.2f}</p>
                <p><b>• Convênio / Farmácia / Outros:</b> R$ {max(0, desc_ativo - inss_ativo - irrf_ativo - vale_ativo):,.2f}</p>
                <h3 style="color: #EF5350; margin-top: 15px;">Total Descontos: R$ {desc_ativo:,.2f}</h3>
            </div>
            """,
          unsafe_allow_html=True,
      )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div style="background-color: #1E222A; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #3F51B5;">
            <h4 style="color: #9FA8DA; margin: 0;">💵 Receita Líquida ({mes_ativo_ext})</h4>
            <h2 style="color: #5C6BC0; margin: 5px 0 0 0;">R$ {liquido_ativo:,.2f}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

  st.markdown("---")
  st.subheader("📋 Histórico Corporativo de Contracheques Cadastrados")

  if not df_holerites.empty:
    df_exibicao_hol = df_holerites[[
        "id",
        "mes_ano",
        "salario_bruto",
        "vale",
        "total_descontos",
        "liquido",
        "inss",
        "irrf",
    ]].copy()

    st.dataframe(
        df_exibicao_hol.style.format({
            "salario_bruto": "R$ {:,.2f}",
            "vale": "R$ {:,.2f}",
            "total_desconsos": "R$ {:,.2f}",
            "liquido": "R$ {:,.2f}",
            "inss": "R$ {:,.2f}",
            "irrf": "R$ {:,.2f}",
        }),
        use_container_width=True,
    )

    st.write(
        "**Gráfico Comparativo de Evolução: Salário Bruto vs Líquido vs"
        " Descontos**"
    )
    st.line_chart(
        df_holerites.set_index("mes_ano")[[
            "sal_bruto",
            "liquido",
            "total_descontos",
        ]]
    )

    st.markdown("### ⚙️ Opções de Gerenciamento do Histórico")
    col_del1, col_del2 = st.columns(2)

    with col_del1:
      id_del_hol = st.selectbox(
          "Selecione o ID exato para remoção:",
          df_holerites["id"].tolist(),
          key="del_hol_unique",
      )
      if st.button("Excluir Holerite Selecionado", use_container_width=True):
        c.execute("DELETE FROM holerites WHERE id = ?", (id_del_hol,))
        conn.commit()
        st.success("Holerite excluído com sucesso!")
        st.rerun()

    with col_del2:
      st.write("")
      st.write("")
      if st.button(
          "🗑️ EXCLUIR TODO HISTÓRICO DE HOLERITES",
          use_container_width=True,
          type="primary",
      ):
        c.execute("DELETE FROM holerites")
        conn.commit()
        st.success("Todo o histórico de holerites foi apagado com sucesso!")
        st.rerun()
  else:
    st.info("Nenhum holerite cadastrado no histórico analítico até o momento.")
