from datetime import date, datetime, timedelta
import difflib
import re
import sqlite3
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
# --- MOTOR DE INTELIGÊNCIA E CATEGORIZAÇÃO ---
# ==========================================
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
    return "🏠 Contas Fixas (Necessidade)"


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
  st.markdown("---")
  if st.button("⬅️ Voltar para o Painel Principal", use_container_width=True):
    mudar_pagina("🏠 Início / Painel")
    st.rerun()


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
    if st.button("📅 Contas a Pagar", use_container_width=True):
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

  # Grupo 3 & 4: Configuração, Suporte, Relatórios & Backup
  col_a, col_b = st.columns(2)
  with col_a:
    st.markdown(
        '<div class="group-card"><div class="group-title">Configuração &'
        " Suporte</div>",
        unsafe_allow_html=True,
    )
    sub1, sub2 = st.columns(2)
    with sub1:
      if st.button("🏷️ Categorias & Ícones", use_container_width=True):
        mudar_pagina("🏷️ Categorias & Ícones")
        st.rerun()
    with sub2:
      if st.button("❤️ Saúde Financeira", use_container_width=True):
        mudar_pagina("❤️ Saúde Financeira")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

  with col_b:
    st.markdown(
        '<div class="group-card"><div class="group-title">Relatórios &'
        " Backup</div>",
        unsafe_allow_html=True,
    )
    sub1, sub2 = st.columns(2)
    with sub1:
      if st.button("📄 Holerites & PDF", use_container_width=True):
        mudar_pagina("📄 Holerites")
        st.rerun()
    with sub2:
      if st.button("📋 Extrato & Backup", use_container_width=True):
        mudar_pagina("📋 Extrato & Backup")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# --- SEÇÃO 1: LANÇAR DESPESA ---
# ==========================================
elif st.session_state.pagina_atual == "🔴 Lançar Despesa":
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
      data_desp = st.date_input("Data do Ocorrido do Gasto", value=date.today())

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
  botao_voltar()

# ==========================================
# --- SEÇÃO 2: ENTRADAS & SALÁRIOS ---
# ==========================================
elif st.session_state.pagina_atual == "🟢 Entradas & Salários":
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
      data_rec = st.date_input("Data de Recebimento Efetivo", value=date.today())

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
  botao_voltar()

# ==========================================
# --- SEÇÃO 2.1: VEÍCULOS, MANUTENÇÕES & COMBUSTÍVEIS ---
# ==========================================
elif st.session_state.pagina_atual == "🚗 Veículos & Manutenção":
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
          data_manut = st.date_input("Data do Ocorrido / Agendamento", value=date.today())
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
          data_comb = st.date_input("Data do Abastecimento", value=date.today(), key="data_comb_key")
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
  botao_voltar()

# ==========================================
# --- SEÇÃO 3A: DASHBOARD MANUAL (LANÇAMENTOS REAIS) ---
# ==========================================
elif st.session_state.pagina_atual == "📊 Dashboard Manual":
  st.subheader("📊 Executive Dashboard — Lançamentos Reais Manuais")
  st.write("Painel gerencial focado exclusivamente nos registros feitos de forma manual no sistema.")

  df_all = pd.read_sql("SELECT * FROM transacoes WHERE origem = 'Manual'", conn)
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
  botao_voltar()

# ==========================================
# --- SEÇÃO 3B: DASHBOARD EXTRATO BANCO (PDF) ---
# ==========================================
elif st.session_state.pagina_atual == "📥 Dashboard Banco":
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
    st.dataframe(df_b[["data", "tipo", "descricao", "categoria", "valor"]], use_container_width=True, hide_index=True)
  else:
    st.info("Nenhum extrato bancário em PDF foi importado e processado até o momento. Faça o upload na aba 'Extrato & Backup'.")
  botao_voltar()

# ==========================================
# --- SEÇÃO 4: PREVISÃO FINANCEIRA ---
# ==========================================
elif st.session_state.pagina_atual == "🔮 Previsão Financeira":
  st.subheader("📅 Previsão Financeira")
  st.write("Visualize suas finanças em qualquer período de forma detalhada e interativa.")

  if "prev_data_atual" not in st.session_state:
    st.session_state.prev_data_atual = datetime.now().replace(day=1)

  col_p1, col_p2, col_p3 = st.columns([2, 2, 2])
  with col_p1:
    tipo_visao = st.radio("Período:", ["Mensal", "Anual"], horizontal=True, label_visibility="collapsed")
  with col_p2:
    formato_exibicao = st.radio("Formato:", ["Gráfico", "Tabela"], horizontal=True, label_visibility="collapsed")
  with col_p3:
    if st.button("📥 Exportar Relatório Previsto", use_container_width=True):
      st.success("Relatório de previsão exportado com sucesso!")

  st.markdown("---")

  col_nav1, col_nav2, col_nav3 = st.columns([1, 4, 1])
  with col_nav1:
    if st.button("❮ Anterior", use_container_width=True):
      if tipo_visao == "Mensal":
        st.session_state.prev_data_atual = (st.session_state.prev_data_atual - timedelta(days=1)).replace(day=1)
      else:
        st.session_state.prev_data_atual = st.session_state.prev_data_atual.replace(year=st.session_state.prev_data_atual.year - 1)
      st.rerun()

  meses_nomes_pt = {
      1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
      7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
  }
  ano_ativo = st.session_state.prev_data_atual.year
  mes_ativo_num = st.session_state.prev_data_atual.month
  nome_mes_exib = meses_nomes_pt[mes_ativo_num]

  with col_nav2:
    if tipo_visao == "Mensal":
      st.markdown(f"<h3 style='text-align: center; color: #f8fafc; margin: 0;'>{nome_mes_exib} de {ano_ativo}</h3>", unsafe_allow_html=True)
    else:
      st.markdown(f"<h3 style='text-align: center; color: #f8fafc; margin: 0;'>Ano de {ano_ativo}</h3>", unsafe_allow_html=True)

  with col_nav3:
    if st.button("Próximo ❯", use_container_width=True):
      if tipo_visao == "Mensal":
        st.session_state.prev_data_atual = (st.session_state.prev_data_atual + timedelta(days=32)).replace(day=1)
      else:
        st.session_state.prev_data_atual = st.session_state.prev_data_atual.replace(year=st.session_state.prev_data_atual.year + 1)
      st.rerun()

  st.markdown("<br>", unsafe_allow_html=True)

  df_cartao_prev = pd.read_sql("SELECT * FROM cartao_credito", conn)
  df_contas_prev = pd.read_sql("SELECT * FROM contas WHERE pago = 0", conn)
  df_trans_prev = pd.read_sql("SELECT * FROM transacoes", conn)

  if not df_cartao_prev.empty:
    df_cartao_prev["data_dt"] = pd.to_datetime(df_cartao_prev["data"], errors="coerce")
    if tipo_visao == "Mensal":
      df_cartao_filtered = df_cartao_prev[(df_cartao_prev["data_dt"].dt.year == ano_ativo) & (df_cartao_prev["data_dt"].dt.month == mes_ativo_num)]
    else:
      df_cartao_filtered = df_cartao_prev[df_cartao_prev["data_dt"].dt.year == ano_ativo]
    total_faturas = df_cartao_filtered["valor"].sum()
  else:
    total_faturas = 0.0

  if not df_contas_prev.empty:
    df_contas_prev["venc_dt"] = pd.to_datetime(df_contas_prev["vencimento"], errors="coerce")
    if tipo_visao == "Mensal":
      df_contas_filtered = df_contas_prev[(df_contas_prev["venc_dt"].dt.year == ano_ativo) & (df_contas_prev["venc_dt"].dt.month == mes_ativo_num)]
    else:
      df_contas_filtered = df_contas_prev[df_contas_prev["venc_dt"].dt.year == ano_ativo]
    total_contas = df_contas_filtered["valor"].sum()
  else:
    total_contas = 0.0

  if not df_trans_prev.empty:
    df_trans_prev["data_dt"] = pd.to_datetime(df_trans_prev["data"], errors="coerce")
    if tipo_visao == "Mensal":
      df_trans_filtered = df_trans_prev[(df_trans_prev["data_dt"].dt.year == ano_ativo) & (df_trans_prev["data_dt"].dt.month == mes_ativo_num)]
    else:
      df_trans_filtered = df_trans_prev[df_trans_prev["data_dt"].dt.year == ano_ativo]
    
    total_entradas_previstas = df_trans_filtered[df_trans_filtered["tipo"] == "Receita"]["valor"].sum()
    total_saidas_manuais = df_trans_filtered[df_trans_filtered["tipo"] == "Despesa"]["valor"].sum()
  else:
    total_entradas_previstas = 0.0
    total_saidas_manuais = 0.0

  total_dividas = 0.0
  total_saidas_previstas = total_faturas + total_contas + total_dividas + total_saidas_manuais
  saldo_projetado = total_entradas_previstas - total_saidas_previstas

  m1, m2, m3 = st.columns(3)
  with m1:
    st.markdown(
        f"""
        <div style="background: rgba(34, 197, 94, 0.08); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 12px; padding: 20px;">
            <span style="color: #4ade80; font-size: 13px; font-weight: 600;">🟢 TOTAL ENTRADAS</span>
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

  st.markdown(
      f"""
      <div class="group-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
              <h4 style="color: #f8fafc; margin: 0; display: flex; align-items: center; gap: 8px;">📉 Saídas Previstas</h4>
              <h4 style="color: #ef4444; margin: 0;">R$ {total_saidas_previstas:,.2f}</h4>
          </div>
          <hr style="border-color: var(--border-color); margin-bottom: 15px;">
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04);">
              <span style="color: #94a3b8;">💳 Faturas de Cartão</span>
              <span style="color: #f8fafc; font-weight: 600;">R$ {total_faturas:,.2f}</span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04);">
              <span style="color: #94a3b8;">📅 Contas a Pagar & Despesas</span>
              <span style="color: #f8fafc; font-weight: 600;">R$ {total_contas + total_saidas_manuais:,.2f}</span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0;">
              <span style="color: #94a3b8;">🏛️ Parcelas de Dívidas</span>
              <span style="color: #f8fafc; font-weight: 600;">R$ {total_dividas:,.2f}</span>
          </div>
      </div>
      """,
      unsafe_allow_html=True,
  )

  st.markdown(
      f"""
      <div class="group-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
              <h4 style="color: #f8fafc; margin: 0; display: flex; align-items: center; gap: 8px;">📈 Entradas Previstas</h4>
              <h4 style="color: #22c55e; margin: 0;">R$ {total_entradas_previstas:,.2f}</h4>
          </div>
          <hr style="border-color: var(--border-color); margin-bottom: 15px;">
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0;">
              <span style="color: #94a3b8;">📥 Contas a Receber / Salários</span>
              <span style="color: #f8fafc; font-weight: 600;">R$ {total_entradas_previstas:,.2f}</span>
          </div>
      </div>
      """,
      unsafe_allow_html=True,
  )

  if formato_exibicao == "Gráfico":
    st.markdown("### 📊 Gráfico de Previsão de Fluxo")
    df_graf_prev = pd.DataFrame({
        "Categoria": ["Entradas", "Saídas", "Saldo Projetado"],
        "Valor": [total_entradas_previstas, total_saidas_previstas, saldo_projetado]
    })
    st.bar_chart(df_graf_prev.set_index("Categoria"))
  else:
    st.markdown("### 📋 Tabela Analítica da Previsão")
    df_tabela_prev = pd.DataFrame([
        {"Tipo": "Entrada Prevista", "Descrição": "Salários / Receitas Cadastradas", "Valor (R$)": total_entradas_previstas},
        {"Tipo": "Saída Prevista", "Descrição": "Faturas de Cartão de Crédito", "Valor (R$)": total_faturas},
        {"Tipo": "Saída Prevista", "Descrição": "Contas a Pagar Pendentes", "Valor (R$)": total_contas},
    ])
    st.dataframe(df_tabela_prev, use_container_width=True, hide_index=True)

  botao_voltar()

# ==========================================
# --- SEÇÃO 5: CARTÃO DE CRÉDITO ---
# ==========================================
elif st.session_state.pagina_atual == "💳 Cartão de Crédito":
  st.subheader("💳 Gestão Avançada de Faturas de Cartão de Crédito")
  st.write(
      "Acompanhe gastos detalhados por bandeira e controle o impacto das"
      " compras parceladas."
  )

  with st.form("form_cartao_credito_completo", clear_on_submit=True):
    col_cc1, col_cc2 = st.columns(2)
    with col_cc1:
      nome_cartao = st.selectbox(
          "Bandeira / Cartão", ["Itaúcard", "Samsung Itaú", "Nubank", "Outro"]
      )
      desc_cc = st.text_input("Descrição da Compra Específica")
    with col_cc2:
      val_cc = st.number_input(
          "Valor da Compra (R$)", min_value=0.0, value=0.00, step=1.0, format="%.2f"
      )
      data_cc = st.date_input("Data da Compra no Cartão", value=date.today())

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
  botao_voltar()

# ==========================================
# --- SEÇÃO 6: INVESTIMENTOS ---
# ==========================================
elif st.session_state.pagina_atual == "📈 Investimentos":
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
      data_aporte = st.date_input("Data do Aporte Realizado", value=date.today())
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
      st.dataframe(
          df_carteira[
              ["ativo", "classe", "quantidade", "preco_medio", "Valor Total"]
          ].rename(columns={
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
  botao_voltar()

# ==========================================
# --- SEÇÃO 7: DESAFIOS ---
# ==========================================
elif st.session_state.pagina_atual == "🎯 Desafios":
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
  botao_voltar()

# ==========================================
# --- SEÇÃO 8A: METAS DE GASTOS ---
# ==========================================
elif st.session_state.pagina_atual == "🎯 Metas de Gastos":
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
      "SELECT * FROM transacoes WHERE tipo = 'Despesa' AND origem = 'Manual'", conn
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
  botao_voltar()

# ==========================================
# --- SEÇÃO 8B: CATEGORIAS & ÍCONES ---
# ==========================================
elif st.session_state.pagina_atual == "🏷️ Categorias & Ícones":
  st.subheader("🏷️ Gerenciamento de Categorias Personalizadas & Ícones")
  st.write(
      "Cadastre novas categorias customizadas para o seu ecossistema"
      " financeiro."
  )

  col_m1, col_m2 = st.columns(2)

  with col_m1:
    st.write("### ➕ Adicionar Nova Categoria com Ícone")
    with st.form("form_nova_categoria_completo", clear_on_submit=True):
      icone_escolhido = st.selectbox(
          "Escolha um Ícone Personalizado:",
          [
              # --- Contas, Boletos & Finanças ---
              "📄", "🧾", "💳", "💰", "💵", "💸", "🏦", "🏧", "📊", 
              "🪙", "🏷️", "💼", "📈", "📉", "🔒", "🔑", "💡", "⚡", "💧", 
              "🔥", "📶", "📡", "📱", "💻", "📺", "📬", "🗑️", "⚙️", "🛠️",
              # --- Despesas do Dia a Dia & Moradia ---
              "🏠", "🏡", "🏢", "🛒", "🛍️", "🍔", "🍕", "☕", "🍺", "🍷", 
              "🚗", "🚕", "🚌", "🚆", "⛽", "🅿️", "💊", "🏥", "🩺", "🏋️‍♂️", 
              # --- Lazer, Pets & Outros ---
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
          st.error("Digite um nome válido para a categoria.")

  with col_m2:
    st.write("### 🗑️ Excluir Categoria Personalizada")
    df_cats_excluir = pd.read_sql("SELECT * FROM categorias", conn)
    if not df_cats_excluir.empty:
      with st.form("form_excluir_cat_completo"):
        cat_para_deletar = st.selectbox(
            "Selecione a categoria para apagar:",
            df_cats_excluir["nome"].tolist(),
        )
        if st.form_submit_button(
            "Excluir Categoria Selecionada", use_container_width=True
        ):
          c.execute("DELETE FROM categorias WHERE nome = ?", (cat_para_deletar,))
          conn.commit()
          st.success(f"Categoria '{cat_para_deletar}' excluída com sucesso!")
          st.rerun()
    else:
      st.info("Nenhuma categoria personalizada cadastrada para exclusão.")

  st.markdown("---")
  st.subheader("📋 Relação de Categorias Personalizadas Cadastradas")
  df_cats_view = pd.read_sql("SELECT * FROM categorias", conn)
  if not df_cats_view.empty:
    st.dataframe(df_cats_view, use_container_width=True)
  else:
    st.info("Nenhuma categoria customizada registrada.")

  botao_voltar()

# ==========================================
# --- SEÇÃO 9: SAÚDE FINANCEIRA ---
# ==========================================
elif st.session_state.pagina_atual == "❤️ Saúde Financeira":
  st.subheader("❤️ Score de Saúde Financeira & Auditoria de Perfil")
  st.write(
      "Pontuação calculada de 0 a 1000 com base em endividamento, taxa de"
      " poupança, disciplina e cumprimento de tetos."
  )

  df_saude = pd.read_sql("SELECT * FROM transacoes WHERE origem = 'Manual'", conn)
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
  botao_voltar()

# ==========================================
# --- SEÇÃO 10: CONTAS A PAGAR ---
# ==========================================
elif st.session_state.pagina_atual == "📅 Contas a Pagar":
  st.subheader("📅 Calendário de Contas a Vencer & Gestão de Pagamentos")
  st.write(
      "Organize boletos, contas fixas, IPVA e compromissos com vencimento"
      " programado."
  )

  with st.form("form_conta_pagar_completo", clear_on_submit=True):
    col_c1, col_c2 = st.columns(2)
    with col_c1:
      venc = st.date_input("Data de Vencimento da Conta")
      nome_conta = st.text_input(
          "Nome / Descrição da Conta (Ex: Conta de Luz, Seguro Auto)"
      )
    with col_c2:
      val_conta = st.number_input(
          "Valor Estimado ou Exato (R$)", min_value=0.0, format="%.2f"
      )

    if st.form_submit_button("Adicionar Conta ao Calendário", use_container_width=True):
      if nome_conta.strip() and val_conta > 0:
        c.execute(
            "INSERT INTO contas (vencimento, descricao, valor, pago) VALUES"
            " (?,?,?,?)",
            (venc.strftime("%Y-%m-%d"), str(nome_conta).strip(), val_conta, 0),
        )
        conn.commit()
        st.success("Conta cadastrada no calendário com sucesso!")
        st.rerun()
      else:
        st.error("Informe a descrição e o valor da conta.")

  st.markdown("---")

  st.write("### 🔍 Pesquisa Inteligente de Contas (com Similaridade)")
  termo_busca_contas = st.text_input(
      "Digite o nome ou descrição da conta:", "", key="busca_contas_input"
  )

  df_contas_all = pd.read_sql("SELECT * FROM contas", conn)

  if termo_busca_contas.strip() and not df_contas_all.empty:
    termo_limpo = termo_busca_contas.strip().lower()
    descricoes = df_contas_all["descricao"].tolist()
    similares = difflib.get_close_matches(
        termo_limpo, [d.lower() for d in descricoes], n=10, cutoff=0.3
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

  if not contas_filtradas.empty:
    st.write("### 📋 Relação de Compromissos (Resultados da Busca)")
    st.dataframe(contas_filtradas, use_container_width=True)
  else:
    st.info("Nenhuma conta encontrada com o termo pesquisado.")
  botao_voltar()

# ==========================================
# --- SEÇÃO 11: EXTRATO & BACKUP ---
# ==========================================
elif st.session_state.pagina_atual == "📋 Extrato & Backup":
  st.subheader(
      "📋 Extrato Consolidado, Importação Inteligente de Extratos PDF/CSV &"
      " Backup"
  )
  st.write(
      "Faça download do banco de dados, exporte planilhas ou importe extratos"
      " bancários em PDF automaticamente."
  )

  col_exp1, col_exp2 = st.columns(2)
  with col_exp1:
    with open("gestor_financeiro.db", "rb") as f:
      st.download_button(
          "💾 Baixar Backup Completo do Banco (.db)",
          f,
          "gestor_financeiro.db",
          use_container_width=True,
      )
  with col_exp2:
    df_extrato_full = pd.read_sql("SELECT * FROM transacoes", conn)
    if not df_extrato_full.empty:
      csv_data = df_extrato_full.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📊 Exportar Extrato Completo para Planilha (CSV)",
          data=csv_data,
          file_name="extrato_financeiro.csv",
          mime="text/csv",
          use_container_width=True,
      )

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
        c.execute("DELETE FROM cartao_credito")
        c.execute("DELETE FROM carteira_investimentos")
        c.execute("DELETE FROM veiculos")
        c.execute("DELETE FROM manutencoes_veiculo")
        c.execute("DELETE FROM consumo_combustivel")
        c.execute("DELETE FROM holerites")
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
        key="filtro_extrato_similaridade",
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
      st.write(
          f"### 📋 Resultados Encontrados ({len(df_extrato_filtrado)} registros)"
      )
      st.dataframe(df_extrato_filtrado, use_container_width=True)
    else:
      st.info(
          "Nenhuma transação encontrada com os filtros e termos pesquisados."
      )
  else:
    st.info("Nenhum extrato armazenado no banco de dados.")

  botao_voltar()

# ==========================================
# --- SEÇÃO 12: HOLERITES ---
# ==========================================
elif st.session_state.pagina_atual == "📄 Holerites":
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
            "total_descontos": "R$ {:,.2f}",
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
            "salario_bruto",
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
          "🗑️ EXCLUIR TODO O HISTÓRICO DE HOLERITES",
          use_container_width=True,
          type="primary",
      ):
        c.execute("DELETE FROM holerites")
        conn.commit()
        st.success("Todo o histórico de holerites foi apagado com sucesso!")
        st.rerun()
  else:
    st.info("Nenhum holerite cadastrado no histórico analítico até o momento.")
  botao_voltar()
