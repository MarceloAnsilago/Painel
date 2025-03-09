import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh
import sqlite3
import datetime
import random
import pandas as pd

st.set_page_config(layout="wide")

# 🔹 Criar banco de dados e sessão inicial
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
        terminal INTEGER,
        unidade TEXT
    )
    """)
    conn.commit()
    conn.close()

setup_database()

# Gerar sessão única se ainda não existir
if "secao" not in st.session_state:
    st.session_state.secao = random.randint(1000, 9999)

# Verificar se existe registro para a sessão atual
conn = sqlite3.connect("senhas.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM senha WHERE secao = ?", (st.session_state.secao,))
count = cursor.fetchone()[0]
conn.close()

# Se não existir, criar um registro inicial
if count == 0:
    conn = sqlite3.connect("senhas.db", check_same_thread=False)
    cursor = conn.cursor()
    hora_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO senha (secao, senha, hora, usuario, resposta, status, terminal, unidade)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (st.session_state.secao, 0, hora_atual, "admin", "chamando 1", "admin", 0, "São Miguel Idaron"))
    conn.commit()
    conn.close()

# 🔹 Criar botão "Iniciar Painel"
st.markdown("""
    <style>
    div.stButton > button {
        width: 300px;
        height: 100px;
        font-size: 24px;
    }
    .centered {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 25vh;
    }
    </style>
    """, unsafe_allow_html=True)

if "painel_iniciado" not in st.session_state:
    st.session_state.painel_iniciado = False

col1, col2, col3 = st.columns([1, 2, 1])  # Centralizar botão
with col2:
    if st.button("🚀 Iniciar Painel"):
        st.session_state.painel_iniciado = True
        st.rerun()

if not st.session_state.painel_iniciado:
    st.stop()

# 🔹 Criar colunas (vídeo + painel de senhas)
col_video, col_content = st.columns([5, 2])  # Ajuste de proporção

# 🎥 **Coluna do Vídeo (fixo, sem atualização)**
with col_video:
    components.html(
        """
        <style>
        .video-container {
            position: relative;
            width: 100%;
            padding-bottom: 56.25%;
            height: 0;
        }
        .video-container iframe {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border: none;
        }
        </style>
        <div class="video-container">
        <iframe 
            src="https://www.youtube.com/embed?listType=playlist&list=PLrBhE4oLMMj95y5nobzQgDT8ygY-Pqbk3"
            allow="autoplay; encrypted-media"
            allowfullscreen>
        </iframe>
        </div>
        """,
        height=400,
    )

# 🔄 **Coluna do Painel de Senhas**
with col_content:
    st_autorefresh(interval=4000, limit=1000, key="refresh_senhas")  # Apenas essa coluna será atualizada

    # Criar abas
    tab1, tab2 = st.tabs(["📢 Painel de Senhas", "📜 Últimas Senhas Chamadas"])

    # 🔹 **ABA 1: Painel de Senhas**
    with tab1:
        # Buscar dados da senha mais recente
        def verificar_senha_em_aberto():
            conn = sqlite3.connect("senhas.db", check_same_thread=False)
            c = conn.cursor()
            c.execute("""
                SELECT senha, resposta, status, hora, unidade, usuario, terminal
                FROM senha
                WHERE secao = ? AND status IN ('aberto','admin','encerrado')
                ORDER BY hora DESC
                LIMIT 1
            """, (st.session_state.secao,))
            row = c.fetchone()
            conn.close()
            return row if row else None

        row = verificar_senha_em_aberto()

        if row:
            senha_atual, resposta_atual, status_atual, hora_db, unidade, usuario, terminal = row
            hora_formatada = datetime.datetime.strptime(hora_db, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M:%S")
        else:
            senha_atual = resposta_atual = status_atual = hora_db = unidade = usuario = terminal = None
            hora_formatada = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Exibir **card da senha atual**
        st.markdown(
            f"""
            <div style="border:1px solid black; text-align:center; padding:40px; width:100%;">
                <div style="background-color:black; color:white; padding:10px; font-weight:bold;">
                    {unidade if unidade else "UNIDADE XYZ"}
                </div>
                <div style="padding:20px;">
                    <div style="font-size:20px; font-weight:bold;">SENHA</div>
                    <div style="font-size:54px; font-weight:bold;">{senha_atual if senha_atual else "000"}</div>
                </div>
                <div style="background-color:black; color:white; padding:10px; font-size:14px;">
                    DATA {hora_formatada} — Seção {st.session_state.secao}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # 🔹 **ABA 2: Últimas Senhas Chamadas**
    with tab2:
        st.write("## 📜 Últimas Senhas Chamadas")
        
        conn = sqlite3.connect("senhas.db")
        df = pd.read_sql_query("""
            SELECT senha, hora, resposta
            FROM senha
            WHERE secao = ? AND senha > 0 AND status <> '0'
            ORDER BY senha DESC
            LIMIT 5
        """, conn, params=[st.session_state.secao])
        conn.close()

        if df.empty:
            st.write("Nenhuma senha chamada recentemente.")
        else:
            # Criar tabela estilizada
            html_table = df.style.set_properties(
                subset=["senha"],
                **{'text-align': 'center', 'background-color': '#FFEEAA'}
            ).hide(axis="index").to_html()

            st.markdown(html_table, unsafe_allow_html=True)
