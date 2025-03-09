import sqlite3
import datetime
import math
import time
import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_autorefresh import st_autorefresh 
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import base64


st.set_page_config(layout="wide", page_title="Gerenciador")

# Remova a inicialização automática da seção para que o usuário informe


if "chamar_clicked" not in st.session_state:
    st.session_state["chamar_clicked"] = False
if "next_chamar_novamente" not in st.session_state:
    st.session_state["next_chamar_novamente"] = 0
if "chamar_info_message" not in st.session_state:
    st.session_state["chamar_info_message"] = ""

st.title("Gerenciador")
st.markdown("---")

# --- Configuração do Banco de Dados ---
def setup_database():
    conn = sqlite3.connect("senhas.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS senha (
        secao INTEGER,
        senha INTEGER,
        hora TEXT,
        usuario TEXT,
        resposta TEXT,
        status TEXT,
        terminal INTEGER
    )
    """)
    conn.commit()
    conn.close()

setup_database()

# --- Entrada da Seção ---
if "secao" not in st.session_state:
    secao_input = st.text_input("Informe a seção (número):", value="")
    if secao_input.strip():
        try:
            secao_num = int(secao_input)
        except ValueError:
            st.error("Por favor, informe apenas números para a seção.")
            st.stop()
        # Verifica se a seção existe no banco de dados
        conn = sqlite3.connect("senhas.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM senha WHERE secao = ?", (secao_num,))
        count = cursor.fetchone()[0]
        conn.close()
        if count == 0:
            st.error("Seção não encontrada no banco de dados. Verifique o número informado.")
            st.stop()
        else:
            st.session_state.secao = secao_num
    else:
        st.info("Digite o número da seção acima para prosseguir.")
        st.stop()

# --- Menu Lateral ---
with st.sidebar:
    selected = option_menu(
        menu_title="Menu",
        options=["Chamar", "Senhas"],
        icons=["telephone", "table"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "5!important", "background-color": "#fafafa"},
            "icon": {"color": "red", "font-size": "25px"},
            "nav-link": {
                "font-size": "16px",
                "text-align": "left",
                "margin": "0px",
                "color": "white",
                "background-color": "red",
                "border-radius": "5px",
                "padding": "8px 16px"
            },
            "nav-link-selected": {"background-color": "darkred"}
        }
    )


if selected == "Chamar":
    st_autorefresh(interval=1000, key="refresher")
    if st.session_state.get("chamar_info_message"):
        st.info(st.session_state["chamar_info_message"])

    # Inicializa as chaves se ainda não existirem
    if "nome" not in st.session_state:
        st.session_state["nome"] = ""
    if "terminal_input" not in st.session_state or st.session_state["terminal_input"] < 1:
        st.session_state["terminal_input"] = 1

    # Inputs: Nome e Terminal em colunas, utilizando os valores do session_state como default
    col_nome, col_terminal = st.columns(2)
    nome = col_nome.text_input("Informe seu nome:", value=st.session_state["nome"])
    terminal_input = col_terminal.number_input("Informe seu terminal:",
                                               value=st.session_state["terminal_input"],
                                               min_value=1,
                                               step=1)

    # Atualiza os valores no session_state para que persistam mesmo após a mudança de aba
    st.session_state["nome"] = nome
    st.session_state["terminal_input"] = terminal_input

    # Verifica se os inputs foram informados
    if not nome or not terminal_input:
        st.warning("Por favor, informe seu nome e terminal para prosseguir.")
        st.stop()

    st.markdown("---")

    # Verifica se existem registros no banco para a sessão atual
    conn = sqlite3.connect("senhas.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM senha WHERE secao = ? AND status <> 'admin'",
        (st.session_state.secao,)
    )
    count_valid = cursor.fetchone()[0]
    conn.close()

    if count_valid == 0:
        st.info("Por favor, gere as senhas na aba 'Senhas' antes de chamar.")
        st.stop()


    # Conecta ao banco de dados
    conn = sqlite3.connect("senhas.db")
    cursor = conn.cursor()

    # 1) Tenta buscar o maior valor de 'senha' onde status <> '0'
    cursor.execute("""
        SELECT unidade, senha, hora
        FROM senha
        WHERE secao = ?
          AND status <> '0'
        ORDER BY senha DESC
        LIMIT 1
    """, (st.session_state.secao,))
    row = cursor.fetchone()

    # 2) Se não encontrou, busca o registro onde status='admin' e senha=0
    if not row:
        cursor.execute("""
            SELECT unidade, senha, hora
            FROM senha
            WHERE secao = ?
              AND status = 'admin'
              AND senha = 0
            LIMIT 1
        """, (st.session_state.secao,))
        row = cursor.fetchone()

    conn.close()

    # 3) Define as variáveis para o card
    if row:
        cabecalho = row[0] if row[0] else "SEM UNIDADE"  # coluna 'unidade'
        senha_numero = row[1] if row[1] else 0           # coluna 'senha'
        hora_str = row[2] if row[2] else "Data não encontrada"  # coluna 'hora'
    else:
        cabecalho = "SEM UNIDADE"
        senha_numero = 0
        hora_str = "Data não encontrada"

    # Define a seção como string para exibir no rodapé
    secao_str = st.session_state.secao

    # 4) Cria o card centralizado
    col_left, col_middle, col_right = st.columns([1,2,1])
    with col_middle:
        st.markdown(
            f"""
            <div style="border: 1px solid black; text-align:center; width:300px;">
                <div style="background-color:black; color:white; padding:10px; font-weight:bold;">
                    {cabecalho}
                </div>
                <div style="padding:20px;">
                    <div style="font-size:20px; font-weight:bold;">
                        SENHA
                    </div>
                    <div style="font-size:54px; font-weight:bold;">
                        {senha_numero:03d}
                    </div>
                </div>
                <div style="background-color:black; color:white; padding:15px; font-size:14px;">
                    DATA {hora_str} — Seção {secao_str}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # --- Separador e Botão "Chamar" para atualizar o registro ---
    st.markdown("---")

    with st.container():
        # Cria um placeholder para a mensagem
        info_placeholder = st.empty()
 # Se o botão "Chamar" ainda não foi clicado, exibe-o
    if not st.session_state["chamar_clicked"]:
        if st.button("Chamar"):
            # Antes de chamar, verifica se existe registro aberto
            conn = sqlite3.connect("senhas.db")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT usuario 
                FROM senha
                WHERE secao = ? AND status = 'aberto'
                LIMIT 1
            """, (st.session_state.secao,))
            open_record = cursor.fetchone()
            if open_record:
                st.session_state["chamar_info_message"] = f"Aguarde, {open_record[0]} ainda não encerrou sua chamada."
                conn.close()
                info_placeholder.info(st.session_state["chamar_info_message"])
                st.stop()
            else:
                # Obtém a hora atual
                hora_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Procura o menor registro com senha >= 1 e status = '0'
                cursor.execute("""
                    SELECT senha 
                    FROM senha
                    WHERE secao = ? AND senha >= 1 AND status = '0'
                    ORDER BY senha ASC
                    LIMIT 1
                """, (st.session_state.secao,))
                row_chamar = cursor.fetchone()

                if row_chamar:
                    senha_para_chamar = row_chamar[0]
                    # Atualiza o registro com os dados fornecidos
                    cursor.execute("""
                        UPDATE senha
                        SET hora = ?, usuario = ?, resposta = ?, status = ?, terminal = ?
                        WHERE secao = ? AND senha = ?
                    """, (hora_atual, nome, "chamando 1", "aberto", terminal_input, st.session_state.secao, senha_para_chamar))
                    conn.commit()
                    st.success(f"Senha {senha_para_chamar:03d} chamada!")
                    # Define o tempo para reabilitar o botão "Chamar Novamente"
                    st.session_state["next_chamar_novamente"] = time.time() + 6
                    # Indica que o botão "Chamar" foi clicado
                    st.session_state["chamar_clicked"] = True
                    # Limpa a mensagem informativa, se houver
                    st.session_state["chamar_info_message"] = ""
                    info_placeholder.empty()  # limpa o placeholder
                else:
                    st.warning("Nenhuma senha encontrada com status '0' para chamar.")
                conn.close()
    else:
        # Se o botão "Chamar" já foi clicado, exibe os 3 botões no mesmo contêiner
        col_a, col_b, col_c = st.columns(3)
        now = time.time()
        if now < st.session_state["next_chamar_novamente"]:
            seconds_left = int(st.session_state["next_chamar_novamente"] - now)
            button_text = f"Chamar Novamente ({seconds_left}s)"
            disable_chamar_novamente = True
        else:
            button_text = "Chamar Novamente"
            disable_chamar_novamente = False

        with col_a:
            if st.button(button_text, disabled=disable_chamar_novamente):
                # Lógica de "Chamar Novamente"
                conn = sqlite3.connect("senhas.db")
                cursor = conn.cursor()
                # Procura o registro aberto com os mesmos dados (usuário, terminal e senha exibida no card)
                cursor.execute("""
                    SELECT resposta 
                    FROM senha
                    WHERE secao = ? AND status = 'aberto' AND usuario = ? AND terminal = ? AND senha = ?
                    LIMIT 1
                """, (st.session_state.secao, nome, terminal_input, senha_numero))
                open_record = cursor.fetchone()
                if open_record:
                    current_response = open_record[0] or ""
                    # Se a resposta estiver no formato "chamando X", incrementa o contador; caso contrário, inicia em 1.
                    try:
                        parts = current_response.split()
                        if len(parts) == 2 and parts[0].lower() == "chamando":
                            count = int(parts[1])
                            new_count = count + 1
                        else:
                            new_count = 1
                    except:
                        new_count = 1
                    new_response = f"chamando {new_count}"
                    cursor.execute("""
                        UPDATE senha
                        SET resposta = ?
                        WHERE secao = ? AND status = 'aberto' AND usuario = ? AND terminal = ? AND senha = ?
                    """, (new_response, st.session_state.secao, nome, terminal_input, senha_numero))
                    conn.commit()
                    st.success(f"Registro atualizado para: {new_response}")
                    # Reinicia a contagem regressiva para 5 segundos a cada clique
                    st.session_state["next_chamar_novamente"] = time.time() + 6
                else:
                    st.warning("Nenhum registro aberto encontrado para atualizar.")
                conn.close()

          
            with col_b:
                if st.button("Chamar Compareceu"):
                    conn = sqlite3.connect("senhas.db")
                    cursor = conn.cursor()
                    # Procura o registro aberto que corresponda aos dados atuais
                    cursor.execute("""
                        SELECT * FROM senha
                        WHERE secao = ? AND status = 'aberto' AND usuario = ? AND terminal = ? AND senha = ?
                        LIMIT 1
                    """, (st.session_state.secao, nome, terminal_input, senha_numero))
                    record = cursor.fetchone()
                    if record:
                        hora_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cursor.execute("""
                            UPDATE senha
                            SET hora = ?, resposta = ?, status = ?
                            WHERE secao = ? AND status = 'aberto' AND usuario = ? AND terminal = ? AND senha = ?
                        """, (hora_atual, "compareceu", "encerrado",
                            st.session_state.secao, nome, terminal_input, senha_numero))
                        conn.commit()
                        st.success(f"Senha {senha_numero:03d} encerrada como 'compareceu'!")
                        # Opcional: reseta o estado para que a interface volte ao estado inicial
                        st.session_state["chamar_clicked"] = False
                    else:
                        st.warning("Nenhum registro aberto encontrado para atualizar.")
                    conn.close()
           
            with col_c:
                if st.button("Chamar Não Compareceu"):
                    conn = sqlite3.connect("senhas.db")
                    cursor = conn.cursor()
                    # Procura o registro aberto com os mesmos dados (usuário, terminal e senha exibida no card)
                    cursor.execute("""
                        SELECT * FROM senha
                        WHERE secao = ? AND status = 'aberto' AND usuario = ? AND terminal = ? AND senha = ?
                        LIMIT 1
                    """, (st.session_state.secao, nome, terminal_input, senha_numero))
                    record = cursor.fetchone()
                    if record:
                        hora_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cursor.execute("""
                            UPDATE senha
                            SET hora = ?, resposta = ?, status = ?
                            WHERE secao = ? AND status = 'aberto' AND usuario = ? AND terminal = ? AND senha = ?
                        """, (hora_atual, "não compareceu", "encerrado",
                            st.session_state.secao, nome, terminal_input, senha_numero))
                        conn.commit()
                        st.success(f"Senha {senha_numero:03d} encerrada como 'não compareceu'!")
                        # Opcional: reseta o estado para que a interface volte ao estado inicial
                        st.session_state["chamar_clicked"] = False
                    else:
                        st.warning("Nenhum registro aberto encontrado para atualizar.")
                    conn.close()




    # --- Separador para Próxima senha sem chamar ---
    st.markdown("---")
    # Checkbox para "Próxima senha sem chamar"
    proxima_sem_chamar = st.checkbox("Próxima senha sem chamar", value=False)
    if proxima_sem_chamar:
        if st.button("Adiantar"):
            conn = sqlite3.connect("senhas.db")
            cursor = conn.cursor()
            # Obtém o maior número de senha na sessão e incrementa para a próxima senha
            cursor.execute("SELECT MAX(senha) FROM senha WHERE secao = ?", (st.session_state.secao,))
            max_senha = cursor.fetchone()[0]
            if max_senha is None:
                new_senha = 1
            else:
                new_senha = max_senha + 1
            hora_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO senha (secao, senha, hora, usuario, resposta, status, terminal)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (st.session_state.secao, new_senha, hora_atual, nome, "encerrado sem chamar", "encerrado", terminal_input))
            conn.commit()
            conn.close()
            st.success(f"Senha {new_senha:03d} inserida como 'encerrado sem chamar'.")



    st.markdown("---")
    st.write("## Senhas chamadas")
    conn = sqlite3.connect("senhas.db")
    query = """
        SELECT secao, senha, hora, usuario, resposta, status, terminal
        FROM senha
        WHERE secao = ? AND senha >= 1 AND status <> '0'
        ORDER BY senha ASC
    """
    df = pd.read_sql_query(query, conn, params=[st.session_state.secao])
    conn.close()
    st.table(df)












###############################################
# Aba "Senhas" (Gerar PDF)
###############################################
elif selected == "Senhas":
    st.write("## Gerar PDF de Senhas")
    # Cria 3 colunas: Senha Inicial, Senha Final e Unidade
   
    col1, col2, col3 = st.columns(3)
    senha_inicial = col1.number_input("Senha Inicial:", value=1, step=1)
    senha_final = col2.number_input("Senha Final:", value=10, step=1)
    unidade = col3.text_input("Unidade:", value="")

    # Cria duas colunas para os botões
    btn_col1, btn_col2 = st.columns(2)
    gerar_senhas = btn_col1.button("Gerar Senhas")
    gerar_impressao = btn_col2.button("Gerar Impressão")

    # Rotina para gerar novas senhas
    if gerar_senhas:
        if senha_final < senha_inicial:
            st.error("Senha Final deve ser maior ou igual à Senha Inicial.")
        else:
            conn = sqlite3.connect("senhas.db")
            cursor = conn.cursor()
            # Remove registros existentes para a sessão atual, exceto os que têm status 'admin'
            cursor.execute("""
                SELECT COUNT(*) FROM senha
                WHERE secao = ? AND status <> 'admin'
            """, (st.session_state.secao,))
            count_check = cursor.fetchone()[0]
            if count_check > 0:
                cursor.execute("""
                    DELETE FROM senha
                    WHERE secao = ? AND status <> 'admin'
                """, (st.session_state.secao,))
                conn.commit()
            # Insere novos registros para cada senha, usando 0 em vez de valores vazios
            for num in range(senha_inicial, senha_final + 1):
                cursor.execute("""
                    INSERT INTO senha (secao, senha, hora, usuario, resposta, status, terminal, unidade)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    st.session_state.secao,
                    num,
                    0,   # hora
                    0,   # usuario
                    "chamando",   # resposta
                    0,   # status
                    0,   # terminal
                    unidade
                ))
            conn.commit()
            conn.close()
            st.success("Senhas geradas com sucesso!")

    # Rotina para gerar a impressão (PDF)
    if gerar_impressao:
        conn = sqlite3.connect("senhas.db")
        cursor = conn.cursor()
        # Verifica se há registros com senha >= 1 na sessão atual
        cursor.execute("""
            SELECT COUNT(*) FROM senha
            WHERE secao = ? AND senha >= 1
        """, (st.session_state.secao,))
        count_senhas = cursor.fetchone()[0]
        if count_senhas < 1:
            st.error("Não há senhas geradas para impressão.")
            conn.close()
        else:
            # Busca as senhas (com senha >= 1) diretamente do banco de dados
            cursor.execute("""
                SELECT senha FROM senha
                WHERE secao = ? AND senha >= 1
                ORDER BY senha
            """, (st.session_state.secao,))
            cards = [row[0] for row in cursor.fetchall()]
            conn.close()

            # Função para desenhar um único card
            def draw_single_card(c, x, y, card_width, card_height, num, secao):
                c.rect(x, y, card_width, card_height, stroke=1, fill=0)
                c.setFillColorRGB(0, 0, 0)
                c.rect(x, y + card_height - 35, card_width, 35, fill=1, stroke=0)
                c.setFillColorRGB(1, 1, 1)
                c.setFont("Helvetica-Bold", 14)
                c.drawCentredString(x + card_width/2, y + card_height - 25, unidade)
                c.setFillColorRGB(0, 0, 0)
                c.setFont("Helvetica-Bold", 10)
                c.drawCentredString(x + card_width/2, y + card_height - 50, "SENHA")
                c.setFont("Helvetica-Bold", 24)
                c.drawCentredString(x + card_width/2, y + (card_height / 2) - 20, f"{num:03d}")
                band_height = 25
                c.setFillColorRGB(0, 0, 0)
                c.rect(x, y, card_width, band_height, fill=1, stroke=0)
                c.setFillColorRGB(1, 1, 1)
                c.setFont("Helvetica", 8)
                c.drawCentredString(x + card_width/2, y + band_height - 10, "DATA 04/03/2025")
                c.drawCentredString(x + card_width/2, y + band_height - 20, f"Seção {secao}")

            # Função para gerar o PDF dos cards com layout em páginas
            def generate_cards_pdf(cards, secao):
                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4
                card_width = 150
                card_height = 135
                margin_x = 57
                margin_y = 40
                spacing_x = 20
                spacing_y = 20
                cols = 3

                usable_height = height - 2 * margin_y
                row_space = card_height + spacing_y
                rows_per_page = int(usable_height // row_space)
                if rows_per_page < 1:
                    rows_per_page = 1

                cards_per_page = rows_per_page * cols
                total_cards = len(cards)
                current_index = 0

                while current_index < total_cards:
                    chunk = cards[current_index : current_index + cards_per_page]
                    for i, num_ in enumerate(chunk):
                        row = i // cols
                        col = i % cols
                        x = margin_x + col * (card_width + spacing_x)
                        y = height - margin_y - (row + 1) * card_height - row * spacing_y
                        draw_single_card(c, x, y, card_width, card_height, num_, st.session_state.secao)
                    current_index += cards_per_page
                    if current_index < total_cards:
                        c.showPage()
                c.save()
                pdf = buffer.getvalue()
                buffer.close()
                return pdf

            pdf_bytes = generate_cards_pdf(cards, st.session_state.secao)
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            pdf_iframe = f"""
            <iframe 
                src="data:application/pdf;base64,{pdf_base64}" 
                width="1000" 
                height="900"
                type="application/pdf">
            </iframe>
            """
            st.markdown(pdf_iframe, unsafe_allow_html=True)

    # Exibe as senhas geradas, buscando os registros no banco (apenas senhas >= 1)
    st.write("## Senhas geradas (buscadas do banco de dados)")
    st.markdown(f"*Seção {st.session_state.secao}*")
    conn = sqlite3.connect("senhas.db")
    query = """
        SELECT secao, senha, hora, usuario, resposta, status, terminal, unidade
        FROM senha
        WHERE secao = ? AND senha >= 1
        ORDER BY senha
    """
    df = pd.read_sql_query(query, conn, params=[st.session_state.secao])
    conn.close()
    st.table(df)