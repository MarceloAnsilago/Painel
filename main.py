import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh
import sqlite3
import datetime
import random
import pandas as pd
import base64

st.set_page_config(layout="wide")

# 🔹 Função para criar o banco de dados (se não existir)
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
    """, (st.session_state.secao, 0, hora_atual, "admin", "chamando 1", "aberto", 0, "São Miguel Idaron"))
    conn.commit()
    conn.close()

# Inicializar painel_iniciado e ultima_resposta
if "painel_iniciado" not in st.session_state:
    st.session_state.painel_iniciado = False

# Inicializa 'ultima_resposta' com valor vazio para garantir que a primeira chamada dispare o áudio
if "ultima_resposta" not in st.session_state:
    st.session_state.ultima_resposta = ""

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

if not st.session_state.painel_iniciado:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Iniciar Painel", key="iniciar_painel"):
            st.session_state.painel_iniciado = True
            st.rerun()
    st.stop()

# Função para consultar a senha aberta no banco
def verificar_senha_em_aberto():
    conn = sqlite3.connect("senhas.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        SELECT senha, resposta, status, hora, unidade, usuario, terminal
        FROM senha
        WHERE secao = ? AND status = 'aberto'
        ORDER BY hora DESC
        LIMIT 1
    """, (st.session_state.secao,))
    row = c.fetchone()
    conn.close()
    return row if row else None

# Alternância automática: se houver senha aberta, ativa o modo Painel; caso contrário, ativa Última Senha
row_aberto = verificar_senha_em_aberto()
if row_aberto:
    st.session_state.active_tab = "Painel"
else:
    st.session_state.active_tab = "Última Senha"

# Definir as colunas de acordo com o modo ativo
if st.session_state.active_tab == "Painel":
    col_video, col_content = st.columns([5, 3])
    audio_path = "1430_mobile-rington.mp3"
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        audio_html = f"""
        <script>
            var audio = new Audio("data:audio/mp3;base64,{audio_base64}");
            audio.play();
        </script>
        """
        components.html(audio_html, height=0)
    except Exception as e:
        st.error(f"Erro ao tocar áudio: {e}")




else:
    col_video, col_content = st.columns([5, 1])

# 🎥 Coluna do Vídeo (fixo)
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
        height=700,
    )

# 🔄 Coluna do Painel de Senhas / Últimas Senhas Chamadas
with col_content:
    st_autorefresh(interval=4000, limit=1000, key="refresh_senhas")
    
    if st.session_state.active_tab == "Painel":
        row = verificar_senha_em_aberto()
        if row:
            senha_atual, resposta_atual, status_atual, hora_db, unidade, usuario, terminal = row
            hora_formatada = datetime.datetime.strptime(hora_db, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M:%S")
        else:
            senha_atual = resposta_atual = status_atual = hora_db = unidade = usuario = terminal = None
            hora_formatada = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
        st.markdown(
            f"""
            <style>
                .card-container {{
                    border: 2px solid black;
                    text-align: center;
                    padding: 0;
                    width: 100%;
                    max-width: 300px;
                    margin: auto;
                }}
                .card-header, .card-footer {{
                    background-color: black;
                    color: white;
                    padding: 15px;
                    font-weight: bold;
                    font-size: 16px;
                    margin: 0;
                }}
                .card-body {{
                    padding: 20px;
                    font-size: 24px;
                    font-weight: bold;
                }}
                .senha-number {{
                    font-size: 54px;
                    font-weight: bold;
                    letter-spacing: 2px;
                }}
            </style>
            <div class="card-container">
                <div class="card-header">
                    {unidade if unidade else "UNIDADE XYZ"}
                </div>
                <div class="card-body">
                    <div style="font-size:20px; font-weight:bold;">SENHA</div>
                    <div class="senha-number">{str(senha_atual).zfill(3) if senha_atual else "000"}</div>
                </div>
                <div class="card-footer">
                    DATA {hora_formatada} — Seção {st.session_state.secao}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
        def formatar_resposta(resposta):
            if resposta and resposta.startswith("chamando "):
                try:
                    num_chamadas = int(resposta.split(" ")[1])
                    return f"chamando {num_chamadas} vez" if num_chamadas == 1 else f"chamando {num_chamadas} vezes"
                except ValueError:
                    return resposta
            return resposta
    
        resposta_formatada = formatar_resposta(resposta_atual)
    
        st.markdown(
            f"""
            <div style="border:1px solid #ddd; padding:15px; font-size:18px;">
                <p><strong>🛑 Atenção:</strong> {resposta_formatada if resposta_formatada else "N/A"}</p>
                <p><strong>👨‍💼 Atendente:</strong> {usuario if usuario else "N/A"}</p>
                <p><strong>🖥 Terminal:</strong> {terminal if terminal else "N/A"}</p>
                <p><strong>🕒 Hora da Chamada:</strong> {hora_formatada}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
        # Tocar áudio automaticamente quando uma nova senha for chamada (inclui a primeira chamada)
        if status_atual == "aberto" and resposta_atual and resposta_atual.startswith("chamando"):
            if st.session_state.ultima_resposta != resposta_atual:
                st.session_state.ultima_resposta = resposta_atual
                audio_path = "1430_mobile-rington.mp3"
                try:
                    with open(audio_path, "rb") as f:
                        audio_bytes = f.read()
                    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                    audio_html = f"""
                    <script>
                        var audio = new Audio("data:audio/mp3;base64,{audio_base64}");
                        audio.play();
                    </script>
                    """
                    components.html(audio_html, height=0)
                except Exception as e:
                    st.error(f"Erro ao tocar áudio: {e}")
    else:
        st.write("## 📜 Últimas Senhas Chamadas")
        st.markdown(f"### Seção: {st.session_state.secao}")
    
        conn = sqlite3.connect("senhas.db")
        df = pd.read_sql_query("""
            SELECT senha, hora, resposta
            FROM senha
            WHERE secao = ? AND senha > 0 AND status <> '0'
            ORDER BY senha DESC
            LIMIT 5
        """, conn, params=[st.session_state.secao])
        conn.close()
    
        if not df.empty:
            df = df.rename(columns={"senha": "Senha", "hora": "Horário", "resposta": "Status"})
            html_table = df.style \
                .set_properties(subset=["Senha"], **{'text-align': 'center', 'color': 'red', 'font-weight': 'bold'}) \
                .hide(axis="index") \
                .set_table_styles([
                    {'selector': 'thead th', 'props': 'background-color: black; color: white; font-size: 18px; text-align: center;'},
                    {'selector': 'tbody td', 'props': 'text-align: center; font-size: 16px; padding: 8px;'}
                ]) \
                .to_html()
    
            st.markdown(html_table, unsafe_allow_html=True)
