import psycopg2
import datetime
import random
import pandas as pd
import streamlit as st
import base64
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# 🔹 Configuração do Supabase PostgreSQL
DATABASE_URL = "postgresql://postgres.pbtqsdupirqkikwtuncx:cLqwDiYNFFtwS6T4@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"

# Conectar ao banco (global)
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

def setup_database():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS senha (
        id SERIAL PRIMARY KEY,
        secao INTEGER,
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

st.set_page_config(layout="wide", page_title="Painel de Senhas")

# Sessões
# Gera uma nova seção sempre que o painel for iniciado
if not st.session_state.get("painel_iniciado", False):
    st.session_state["secao"] = random.randint(1000, 9999)
    st.session_state["painel_iniciado"] = True

    # Insere a nova seção no banco de dados se não houver registro para ela
    cursor.execute("SELECT COUNT(*) FROM senha WHERE secao = %s", (st.session_state["secao"],))
    count = cursor.fetchone()[0]
    if count == 0:
        hora_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO senha (secao, senha, hora, usuario, resposta, status, terminal, unidade)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            st.session_state["secao"],
            0,
            hora_atual,
            "admin",
            "chamando 1",
            "aberto",
            0,
            "São Miguel Idaron"
        ))
        conn.commit()

# ❌ Removemos a linha que exibia "Seção: {st.session_state.secao}" no topo

# Variáveis de sessão
if "ultima_resposta" not in st.session_state:
    st.session_state.ultima_resposta = ""

if "ultima_resposta_formatada" not in st.session_state:
    st.session_state.ultima_resposta_formatada = ""

if "ultima_senha" not in st.session_state:
    st.session_state.ultima_senha = None

if "play_audio" not in st.session_state:
    st.session_state.play_audio = False

def verificar_senha_em_aberto():
    cursor.execute("""
        SELECT senha, resposta, status, hora, unidade, usuario, terminal
        FROM senha
        WHERE secao = %s AND status = 'aberto'
        ORDER BY hora DESC
        LIMIT 1
    """, (st.session_state.secao,))
    row = cursor.fetchone()
    return row if row else None

# Determina se a aba será "Painel" ou "Última Senha"
row_aberto = verificar_senha_em_aberto()
st.session_state.active_tab = "Painel" if row_aberto else "Última Senha"

# Se não for Painel, limpamos info de resposta/última senha
if st.session_state.active_tab != "Painel":
    st.session_state.ultima_resposta_formatada = ""
    st.session_state.ultima_senha = None

# Layout das colunas conforme a aba
if st.session_state.active_tab == "Painel":
    col_video, col_content = st.columns([5, 3])
else:
    col_video, col_content = st.columns([5, 1])

# 🎥 Coluna do Vídeo
with col_video:
    components.html(
        """
        <div style="position: relative; width: 100%; padding-bottom: 56.25%; height: 0;">
            <iframe 
                src="https://www.youtube.com/embed?listType=playlist&list=PLrBhE4oLMMj95y5nobzQgDT8ygY-Pqbk3"
                allow="autoplay; encrypted-media"
                style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;">
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

        # Card principal com a seção dentro do cabeçalho
        st.markdown(f"""
            <div style="border: 2px solid black; text-align: center; width: 100%; max-width: 300px; margin: auto;">
                <div style="background-color: black; color: white; padding: 15px; font-weight: bold; font-size: 16px;">
                    {unidade if unidade else "UNIDADE XYZ"}<br/>
                    Seção: {st.session_state.secao}
                </div>
                <div style="padding: 20px; font-size: 24px; font-weight: bold;">
                    <div>SENHA</div>
                    <div style="font-size: 54px;">{str(senha_atual).zfill(3) if senha_atual else "000"}</div>
                </div>
                <div style="background-color: black; color: white; padding: 15px; font-size: 14px;">
                    DATA {hora_formatada}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Card adicional (informações extras)
        def formatar_resposta(resposta):
            if resposta and resposta.startswith("chamando"):
                try:
                    parts = resposta.split(" ")
                    if len(parts) == 2:
                        num_chamadas = int(parts[1])
                        return f"chamando {num_chamadas} vez" if num_chamadas == 1 else f"chamando {num_chamadas} vezes"
                except ValueError:
                    return resposta
            return resposta if resposta else "N/A"

        resposta_formatada = formatar_resposta(resposta_atual)

        st.markdown(f"""
            <div style="border:1px solid #ddd; padding:15px; font-size:18px; margin-top: 20px;">
                <p><strong>🛑 Atenção:</strong> {resposta_formatada}</p>
                <p><strong>👨‍💼 Atendente:</strong> {usuario if usuario else "N/A"}</p>
                <p><strong>🖥 Terminal:</strong> {terminal if terminal else "N/A"}</p>
                <p><strong>🕒 Hora da Chamada:</strong> {hora_formatada}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Dispara áudio se houver mudança
        if (st.session_state.ultima_resposta_formatada != resposta_formatada) or (st.session_state.ultima_senha != senha_atual):
            st.session_state.ultima_resposta_formatada = resposta_formatada
            st.session_state.ultima_senha = senha_atual
            st.session_state.play_audio = True

    else:
        st.write("## 📜 Últimas Senhas Chamadas")
        st.markdown(f"### Seção: {st.session_state.secao}")

        cursor.execute("""
            SELECT senha, hora, resposta
            FROM senha
            WHERE secao = %s AND senha > 0 AND status <> '0'
            ORDER BY senha DESC
            LIMIT 5
        """, (st.session_state.secao,))
        df = pd.DataFrame(cursor.fetchall(), columns=["Senha", "Horário", "Status"])

        if not df.empty:
            # Gera HTML sem índice
            df_html = df.to_html(index=False, classes="my_table", border=0)
            
            # CSS customizado
            custom_css = """
            <style>
            .my_table th {
                background-color: black;
                color: white;
                font-size: 18px;
                text-align: center;
                padding: 8px;
            }
            .my_table td {
                text-align: center;
                font-size: 16px;
                padding: 8px;
            }
            /* Cor de fundo especial na primeira coluna (Senha) */
            .my_table td:nth-child(1) {
                background-color: #FFEEAA;
                color: red;
                font-weight: bold;
            }
            </style>
            """
            st.markdown(custom_css, unsafe_allow_html=True)
            st.markdown(df_html, unsafe_allow_html=True)

# 🔊 Disparo de áudio fora do auto refresh
if st.session_state.get("play_audio", False):
    try:
        audio_path = "1430_mobile-rington.mp3"
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
    st.session_state.play_audio = False

# Fechar cursor e conexão global
cursor.close()
conn.close()
