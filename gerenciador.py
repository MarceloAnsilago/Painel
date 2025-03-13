import psycopg2
import datetime
import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_autorefresh import st_autorefresh
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import base64
import time

# 🔹 Configuração do Supabase PostgreSQL
DATABASE_URL = "postgresql://postgres.pbtqsdupirqkikwtuncx:cLqwDiYNFFtwS6T4@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"

# Conectar ao banco
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# 🔹 Criar tabela automaticamente se não existir
def setup_database():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS senha (
        id SERIAL PRIMARY KEY,
        secao INTEGER,  -- Corrigido de 'seco' para 'secao'
        senha INTEGER,
        hora TIMESTAMP DEFAULT now(),
        usuario TEXT,
        resposta TEXT,
        status TEXT,
        terminal INTEGER,
        unidade TEXT
    )
    """)
    conn.commit()

setup_database()

# 🔹 Configurações da Página
st.set_page_config(layout="wide", page_title="Gerenciador")

# 🔹 Inicializar Session State
if "secao" not in st.session_state:
    st.session_state["secao"] = None
if "chamar_clicked" not in st.session_state:
    st.session_state["chamar_clicked"] = False

st.title("Gerenciador")
st.markdown("---")

# 🔹 Entrada da Seção
if st.session_state["secao"] is None:
    secao_input = st.text_input("Informe a seção (número):", value="")
    if secao_input.strip():
        try:
            secao_num = int(secao_input)
        except ValueError:
            st.error("Por favor, informe apenas números para a seção.")
            st.stop()

        # cursor.execute("SELECT COUNT(*) FROM senha WHERE secao = %s", (secao_num,))
        cursor.execute("SELECT secao FROM senha WHERE secao = %s", (secao_num,))
        secoes = cursor.fetchall()
        if not secoes:
            st.error("Seção não encontrada no banco de dados.")
            st.stop()
        else:
            st.session_state["secao"] = secao_num

    else:
        st.info("Digite o número da seção para prosseguir.")
        st.stop()

# 🔹 Menu Lateral
with st.sidebar:
    selected = option_menu(
        menu_title="Menu",
        options=["Chamar", "Senhas"],
        icons=["telephone", "table"],
        menu_icon="cast",
        default_index=0
    )
# Função de contagem regressiva para os botões "Chamar" e "Chamar Novamente"
def countdown_info(message, seconds):
    placeholder = st.empty()
    for i in range(seconds, 0, -1):
        placeholder.info(f"{message} em {i} segundos...")
        time.sleep(1)
    placeholder.empty()

if selected == "Chamar":

    if "chamar_info_message" not in st.session_state:
        st.session_state["chamar_info_message"] = ""
    if "nome" not in st.session_state:
        st.session_state["nome"] = ""
    if "terminal_input" not in st.session_state or st.session_state["terminal_input"] < 1:
        st.session_state["terminal_input"] = 1
    if "chamar_clicked" not in st.session_state:
        st.session_state["chamar_clicked"] = False
    if "senha_numero" not in st.session_state:
        st.session_state["senha_numero"] = 0
    if "next_chamar_novamente" not in st.session_state:
        st.session_state["next_chamar_novamente"] = 0

    # Exibe mensagem de informação, se houver
    if st.session_state.get("chamar_info_message"):
        st.info(st.session_state["chamar_info_message"])

    # Inputs: Nome e Terminal
    col_nome, col_terminal = st.columns(2)
    nome = col_nome.text_input("Informe seu nome:", value=st.session_state["nome"])
    terminal_input = col_terminal.number_input(
        "Informe seu terminal:",
        value=st.session_state["terminal_input"],
        min_value=1,
        step=1
    )
    st.session_state["nome"] = nome
    st.session_state["terminal_input"] = terminal_input

    if not nome or not terminal_input:
        st.warning("Por favor, informe seu nome e terminal para prosseguir.")
        st.stop()

    st.markdown("---")

    # Verifica se há registros para a sessão atual (exceto admin)
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM senha WHERE secao = %s AND status <> 'admin'",
        (st.session_state.secao,)
    )
    count_valid = cursor.fetchone()[0]
    conn.close()

    if count_valid == 0:
        st.info("Por favor, gere as senhas na aba 'Senhas' antes de chamar.")
        st.stop()

    # --- Layout em 2 colunas: Botões e Card ---
    col_buttons, col_card = st.columns([1, 1])

    ##################################
    # Coluna dos Botões (sem legenda)
    ##################################
    with col_buttons:
        # Se ainda não clicou "Chamar", mostra somente esse botão
        if not st.session_state["chamar_clicked"]:
            if st.button("Chamar Próximo"):
                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor()
                # Verifica se já existe algum registro "aberto"
                cursor.execute("""
                    SELECT usuario 
                    FROM senha
                    WHERE secao = %s AND status = 'aberto'
                    LIMIT 1
                """, (st.session_state.secao,))
                open_record = cursor.fetchone()
                if open_record:
                    st.session_state["chamar_info_message"] = (
                        f"Aguarde, {open_record[0]} ainda não encerrou sua chamada."
                    )
                    conn.close()
                    st.stop()
                else:
                    hora_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("""
                        SELECT senha 
                        FROM senha
                        WHERE secao = %s AND senha >= 1 AND status = '0'
                        ORDER BY senha ASC
                        LIMIT 1
                    """, (st.session_state.secao,))
                    row_chamar = cursor.fetchone()
                    if row_chamar:
                        senha_para_chamar = row_chamar[0]
                        cursor.execute("""
                            UPDATE senha
                            SET hora = %s, usuario = %s, resposta = %s, status = %s, terminal = %s
                            WHERE secao = %s AND senha = %s
                        """, (
                            hora_atual, nome, "chamando 1", "aberto", terminal_input,
                            st.session_state.secao, senha_para_chamar
                        ))
                        conn.commit()
                        st.success(f"Senha {senha_para_chamar:03d} chamada!")
                        st.session_state["next_chamar_novamente"] = time.time() + 5
                        st.session_state["chamar_clicked"] = True
                        st.session_state["chamar_info_message"] = ""
                        countdown_info("Chamando", 5)
                        st.rerun()
                    else:
                        st.warning("Nenhuma senha encontrada com status '0' para chamar.")
                    conn.close()
        else:
            if st.button("Chamar Novamente"):
                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT resposta 
                    FROM senha
                    WHERE secao = %s AND status = 'aberto' AND usuario = %s 
                        AND terminal = %s AND senha = %s
                    LIMIT 1
                """, (
                    st.session_state.secao, nome, terminal_input,
                    st.session_state["senha_numero"]
                ))
                open_record = cursor.fetchone()
                if open_record:
                    current_response = open_record[0] or ""
                    try:
                        parts = current_response.split()
                        if len(parts) == 2 and parts[0].lower() == "chamando":
                            new_count = int(parts[1]) + 1
                        else:
                            new_count = 1
                    except:
                        new_count = 1
                    new_response = f"chamando {new_count}"
                    cursor.execute("""
                        UPDATE senha
                        SET resposta = %s
                        WHERE secao = %s AND status = 'aberto' AND usuario = %s 
                            AND terminal = %s AND senha = %s
                    """, (
                        new_response, st.session_state.secao, nome,
                        terminal_input, st.session_state["senha_numero"]
                    ))
                    conn.commit()
                    st.success(f"Registro atualizado para: {new_response}")
                    st.session_state["next_chamar_novamente"] = time.time() + 5
                    countdown_info("Atualizando", 5)
                    st.rerun()
                else:
                    st.warning("Nenhum registro aberto encontrado para atualizar.")
                conn.close()

            if st.button("Compareceu"):
                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM senha
                    WHERE secao = %s AND status = 'aberto' AND usuario = %s 
                        AND terminal = %s AND senha = %s
                    LIMIT 1
                """, (
                    st.session_state.secao, nome, terminal_input,
                    st.session_state["senha_numero"]
                ))
                record = cursor.fetchone()
                if record:
                    hora_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("""
                        UPDATE senha
                        SET hora = %s, resposta = %s, status = %s
                        WHERE secao = %s AND status = 'aberto' AND usuario = %s 
                            AND terminal = %s AND senha = %s
                    """, (
                        hora_atual, "compareceu", "encerrado",
                        st.session_state.secao, nome, terminal_input,
                        st.session_state["senha_numero"]
                    ))
                    conn.commit()
                    st.success(f"Senha {st.session_state['senha_numero']:03d} encerrada como 'compareceu'!")
                    st.session_state["chamar_clicked"] = False
                    st.rerun()
                else:
                    st.warning("Nenhum registro aberto encontrado para atualizar.")
                conn.close()

            if st.button("Não Compareceu"):
                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM senha
                    WHERE secao = %s AND status = 'aberto' AND usuario = %s 
                        AND terminal = %s AND senha = %s
                    LIMIT 1
                """, (
                    st.session_state.secao, nome, terminal_input,
                    st.session_state["senha_numero"]
                ))
                record = cursor.fetchone()
                if record:
                    hora_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("""
                        UPDATE senha
                        SET hora = %s, resposta = %s, status = %s
                        WHERE secao = %s AND status = 'aberto' AND usuario = %s 
                            AND terminal = %s AND senha = %s
                    """, (
                        hora_atual, "não compareceu", "encerrado",
                        st.session_state.secao, nome, terminal_input,
                        st.session_state["senha_numero"]
                    ))
                    conn.commit()
                    st.success(f"Senha {st.session_state['senha_numero']:03d} encerrada como 'não compareceu'!")
                    st.session_state["chamar_clicked"] = False
                    st.rerun()
                else:
                    st.warning("Nenhum registro aberto encontrado para atualizar.")
                conn.close()

    ##################################
    # Separador e Próxima sem chamar
    ##################################
    st.markdown("---")

    # Exibe o botão "Adiantar Próxima sem chamar" apenas se "chamar_clicked" for False
    if not st.session_state["chamar_clicked"]:
        if st.button("Adiantar Próxima sem chamar"):
            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor()
            # Verifica se já existe algum registro "aberto"
            cursor.execute("""
                SELECT usuario 
                FROM senha
                WHERE secao = %s AND status = 'aberto'
                LIMIT 1
            """, (st.session_state.secao,))
            open_record = cursor.fetchone()
            if open_record:
                st.session_state["chamar_info_message"] = (
                    f"Aguarde, {open_record[0]} ainda não encerrou sua chamada."
                )
                conn.close()
                st.stop()
            else:
                # Busca a próxima senha com status '0' (menor disponível)
                cursor.execute("""
                    SELECT senha 
                    FROM senha
                    WHERE secao = %s AND senha >= 1 AND status = '0'
                    ORDER BY senha ASC
                    LIMIT 1
                """, (st.session_state.secao,))
                row_next = cursor.fetchone()
                if row_next:
                    next_senha = row_next[0]
                    hora_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("""
                        UPDATE senha
                        SET hora = %s, usuario = %s, resposta = %s, status = %s, terminal = %s
                        WHERE secao = %s AND senha = %s
                    """, (
                        hora_atual, nome, "não chamado", "encerrado", terminal_input,
                        st.session_state.secao, next_senha
                    ))
                    conn.commit()
                    conn.close()
                    st.success(f"Senha {next_senha:03d} inserida como 'não chamado'.")
                    # Restaura o estado para permitir nova chamada
                    st.session_state["chamar_clicked"] = False
                    st.rerun()
                else:
                    st.warning("Nenhuma senha disponível para adiantar.")
                    conn.close()

    ##################################
    # Coluna do Card – Atualização Manual
    ##################################
    with col_card:
        def render_card():
            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT unidade, senha, hora
                FROM senha
                WHERE secao = %s AND status <> '0'
                ORDER BY senha DESC
                LIMIT 1
            """, (st.session_state.secao,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                    SELECT unidade, senha, hora
                    FROM senha
                    WHERE secao = %s AND status = 'admin' AND senha = 0
                    LIMIT 1
                """, (st.session_state.secao,))
                row = cursor.fetchone()
            conn.close()

            if row:
                cabecalho = row[0] if row[0] else "SEM UNIDADE"
                senha_numero = row[1] if row[1] else 0
                hora_str = row[2] if row[2] else "Data não encontrada"
            else:
                cabecalho, senha_numero, hora_str = "SEM UNIDADE", 0, "Data não encontrada"

            st.session_state["senha_numero"] = senha_numero
            secao_str = st.session_state.secao

            card_html = f"""
                <div style="border: 1px solid black; text-align:center; width:300px; margin: auto;">
                    <div style="background-color:black; color:white; padding:10px; font-weight:bold;">
                        {cabecalho}
                    </div>
                    <div style="padding:20px;">
                        <div style="font-size:20px; font-weight:bold;">SENHA</div>
                        <div style="font-size:54px; font-weight:bold;">{senha_numero:03d}</div>
                    </div>
                    <div style="background-color:black; color:white; padding:15px; font-size:14px;">
                        DATA {hora_str} — Seção {secao_str}
                    </div>
                </div>
            """
            return card_html

        st.markdown(render_card(), unsafe_allow_html=True)

    # --- Tabela das Últimas Senhas Chamadas ---
    st.markdown("---")
    st.markdown("### Últimas Senhas Chamadas")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    query = """
        SELECT secao, senha, hora, usuario, resposta, status, terminal
        FROM senha
        WHERE secao = %s AND senha >= 1 AND status <> '0'
        ORDER BY senha ASC
    """
    import pandas as pd
    try:
        df = pd.read_sql_query(query, conn, params=[st.session_state.secao])
        st.table(df)
    except Exception as e:
        st.error(f"Erro ao carregar a tabela: {e}")
    conn.close()

# ###############################################
# # Aba "Senhas" (Gerar PDF)
# ###############################################

elif selected == "Senhas":
    st.write("## Gerar PDF de Senhas")
    col1, col2, col3 = st.columns(3)
    senha_inicial = col1.number_input("Senha Inicial:", value=1, step=1)
    senha_final = col2.number_input("Senha Final:", value=10, step=1)
    unidade = col3.text_input("Unidade:", value="")

    btn_col1, btn_col2 = st.columns(2)
    gerar_senhas = btn_col1.button("Gerar Senhas")
    gerar_impressao = btn_col2.button("Gerar Impressão")

    # Rotina para gerar novas senhas
    if gerar_senhas:
        if senha_final < senha_inicial:
            st.error("Senha Final deve ser maior ou igual à Senha Inicial.")
        else:
            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM senha
                WHERE secao = %s AND status <> 'admin'
            """, (st.session_state.secao,))
            count_check = cursor.fetchone()[0]

            if count_check > 0:
                cursor.execute("""
                    DELETE FROM senha
                    WHERE secao = %s AND status <> 'admin'
                """, (st.session_state.secao,))
                conn.commit()

            for num in range(senha_inicial, senha_final + 1):
                cursor.execute("""
                    INSERT INTO senha (secao, senha, hora, usuario, resposta, status, terminal, unidade)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    st.session_state.secao,
                    num,
                    None,   # hora
                    None,   # usuario
                    "chamando",   # resposta
                    "0",   # status
                    "0",   # terminal
                    unidade
                ))
            conn.commit()
            conn.close()
            st.success("Senhas geradas com sucesso!")

    # Rotina para gerar a impressão (PDF) - desindentado para ficar independente
    if gerar_impressao:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM senha
            WHERE secao = %s AND senha >= 1
        """, (st.session_state.secao,))
        count_senhas = cursor.fetchone()[0]

        if count_senhas < 1:
            st.error("Não há senhas geradas para impressão.")
            conn.close()
        else:
            cursor.execute("""
                SELECT senha FROM senha
                WHERE secao = %s AND senha >= 1
                ORDER BY senha
            """, (st.session_state.secao,))
            cards = [row[0] for row in cursor.fetchall()]
            conn.close()

            import io  # Certifique-se de ter importado io, canvas e A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4

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

    st.write("## Senhas geradas (buscadas do banco de dados)")
    st.markdown(f"*Seção {st.session_state.secao}*")
    conn = psycopg2.connect(DATABASE_URL)
    query = """
        SELECT secao, senha, hora, usuario, resposta, status, terminal, unidade
        FROM senha
        WHERE secao = %s AND senha >= 1
        ORDER BY senha
    """
    df = pd.read_sql_query(query, conn, params=[st.session_state.secao])
    conn.close()
    st.table(df)
