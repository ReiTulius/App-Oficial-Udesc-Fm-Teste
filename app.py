import streamlit as st
import pandas as pd
import re
import smtplib
import requests
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import datetime as dt

# ==========================================
# 📻 CONFIGURAÇÃO DO PAINEL & CREDENCIAIS
# ==========================================
st.set_page_config(page_title="Acervo Oficial Integrado - Udesc FM", page_icon="📻", layout="wide")

EMAIL_ROBO_REMETENTE = "heytuliusradio@gmail.com"
SENHA_ROBO_REMETENTE = "nvfxdrlzpkzbugao"
EMAIL_DESTINATARIO_OFICIAL = "heytuliusmusic@gmail.com"

# 📊 LINKS DE LEITURA (PLANILHAS ORIGINAIS PRO)
URL_SOM_DA_ILHA_PRO = "https://docs.google.com/spreadsheets/d/1zw7RPhpuInL7JqSylB_zOMu5zaqO4KgnJ7sD2eoM6gs/export?format=csv"
URL_TULIO_PRO = "https://docs.google.com/spreadsheets/d/16inPMqGCr50-MNJvwV1R4bykDgEGRwlxdbjWrlW6mfY/export?format=csv"
URL_JESSICA_PRO = "https://docs.google.com/spreadsheets/d/1MQ7OcghWNTZwaYVBTmZlMojYTXZMOe5vT1px5VALpS0/export?format=csv"
URL_GOOGLE_SHEETS = "https://docs.google.com/spreadsheets/d/1zkPm3F9W8QbOBhKvdV7jFCYqH-U8Qbru5w5TDyAHQLw/edit?usp=sharing"

# 📊 LINKS DE LEITURA DAS PLANILHAS CÓPIAS (DO APP)
URL_SOM_DA_ILHA_APP_CSV = "https://docs.google.com/spreadsheets/d/1HPirfRjmjZjG23x9kc9Y1zB9zhZv6_iOmB9DIZsCgNo/export?format=csv"
URL_TULIO_APP_CSV = "https://docs.google.com/spreadsheets/d/1iVgHYv58Aknbf0Pa1V2gENWtWZVzkkghdT7vV4nKxTE/export?format=csv"
URL_JESSICA_APP_CSV = "https://docs.google.com/spreadsheets/d/1MQ7OcghWNTZwaYVBTmZlMojYTXZMOe5vT1px5VALpS0/export?format=csv"

# 🚀 WEBHOOKS DE ESCRITA (LOTE COMPLETO)
WEBHOOK_SOM_DA_ILHA = "https://script.google.com/macros/s/AKfycbw1Rzkirio_e9qIqLziKCqFXCmYICaOTVHixIuRgV2WCLdo4pzN1OGQSFtpicrWxf_Z/exec"
WEBHOOK_TULIO = "https://script.google.com/macros/s/AKfycbxR5g2pWU_2_ClapUxY5PWCnH-C9NBrmiT8F1wf0GoLm2KV9jAmMlOQLSGdWsLHNzqX/exec"
WEBHOOK_JESSICA = "https://script.google.com/macros/s/AKfycbGif0xdjbzvo82mvG1CnrKwt8jvp-OWwHCFv3_FTQNJtGxT7m15hZGeO3k7ryWl3E9uQ/exec"

# ==========================================
# 📧 FUNÇÃO DE NOTIFICAÇÃO POR E-MAIL
# ==========================================
def enviar_notificacao_email(nome_acervo, df_novas, nome_usuario):
    if "@" not in EMAIL_ROBO_REMETENTE or "@" not in EMAIL_DESTINATARIO_OFICIAL:
        return
    try:
        fuso_brasilia = dt.timezone(dt.timedelta(hours=-3))
        agora_local = datetime.now(fuso_brasilia)
        
        msg = MIMEMultipart()
        msg['From'] = f"Painel Udesc FM <{EMAIL_ROBO_REMETENTE}>"
        msg['To'] = EMAIL_DESTINATARIO_OFICIAL
        msg['Subject'] = f"📻 Novo Cadastro por: {nome_usuario} ({nome_acervo})"
        
        linhas_musicas = []
        for _, linha in df_novas.iterrows():
            nome_arq = linha.get('Nome do Arquivo', '')
            if not nome_arq and 'Música' in linha:
                nome_arq = f"{linha.get('Artista', 'Desconhecido')} - {linha.get('Música', 'Sem Nome')}"
            linhas_musicas.append(f"• {nome_arq}.mp3")
        lista_texto = "\n".join(linhas_musicas)
        
        corpo = f"""Olá Túlio,

Um novo lote de músicas foi processado e salvo na planilha!

👤 QUEM CADASTROU: {nome_usuario}
📍 DESTINO DO LOTE: {nome_acervo}
📅 DATA/HORA: {agora_local.strftime('%d/%m/%Y %H:%M:%S')}

🎵 Músicas Cadastradas ({len(df_novas)} itens):
{lista_texto}

---
Aviso automático do Painel de Controle Udesc FM."""
        
        msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ROBO_REMETENTE, SENHA_ROBO_REMETENTE)
        server.sendmail(EMAIL_ROBO_REMETENTE, EMAIL_DESTINATARIO_OFICIAL, msg.as_string())
        server.quit()
    except:
        pass

# ==========================================
# 🔄 LEITOR INTEGRADO DO ACERVO (BLINDADO)
# ==========================================
def puxar_dados_do_google(url, nome_acervo):
    try:
        # Garante a conversão correta de links editáveis para links de exportação direta
        if "docs.google.com" in url and "/export" not in url:
            if "/d/" in url:
                id_planilha = url.split("/d/")[1].split("/")[0]
                gid_part = ""
                if "gid=" in url:
                    gid_part = "&gid=" + url.split("gid=")[1].split("&")[0]
                url_base = f"https://docs.google.com/spreadsheets/d/{id_planilha}/export?format=csv{gid_part}"
            else:
                url_base = url
        else:
            url_base = url

        conector = "&" if "?" in url_base else "?"
        url_dinamica = f"{url_base}{conector}cachebuster={int(time.time())}"
        
        # Faz uma requisição rápida para testar se o Google Sheets dá permissão de acesso
        resposta = requests.get(url_dinamica, timeout=10)
        if resposta.status_code != 200 or "html" in resposta.headers.get('Content-Type', '').lower():
            st.sidebar.warning(f"⚠️ Planilha '{nome_acervo}' está privada ou inacessível no Google Drive.")
            return pd.DataFrame()

        df = pd.read_csv(url_dinamica, sep=',', on_bad_lines='skip', encoding='utf-8')
        
        if not df.empty:
            df.dropna(how='all', inplace=True)
            df.columns = [str(c).strip() for c in df.columns]
            df = df[[c for c in df.columns if "REF!" not in c and not c.startswith("Unnamed:")]]
            
            mapeamento = {
                "musica": "Música", "música": "Música", "artista": "Artista",
                "compositores": "Compositores", "compositor": "Compositores",
                "formato": "Formato", "ano": "Ano", "origem": "Origem",
                "genero": "Gênero", "gênero": "Gênero",
                "genero relacionado": "Gênero Relacionado", "gênero relacionado": "Gênero Relacionado",
                "est/idioma": "Est/Idioma", "idioma": "Est/Idioma", "est": "Est/Idioma",
                "classificacao": "Classificação", "classificação": "Classificação",
                "andamento": "Andamento", "data cadastro": "Data Cadastro", "data_cadastro": "Data Cadastro",
                "participacoes": "Participações", "participações": "Participações",
                "nome do arquivo": "Nome do Arquivo", "nome_arquivo": "Nome do Arquivo"
            }
            
            novas_colunas = []
            for col in df.columns:
                col_lower = col.lower().strip()
                if col_lower in mapeamento:
                    novas_colunas.append(mapeamento[col_lower])
                else:
                    novas_colunas.append(col)
            df.columns = novas_colunas
            df["Acervo Origem"] = nome_acervo
            return df
    except Exception as e:
        # Evita que erros na planilha derrubem o site inteiro
        st.sidebar.error(f"Erro ao carregar {nome_acervo}: {str(e)[:50]}")
    return pd.DataFrame()

def inicializar_acervos(forcar_recarga=False):
    if "banco_completo" not in st.session_state or forcar_recarga:
        with st.spinner("Sincronizando acervos em tempo real..."):
            df_som_pro = puxar_dados_do_google(URL_SOM_DA_ILHA_PRO, "Som da Ilha")
            df_tulio_pro = puxar_dados_do_google(URL_TULIO_PRO, "Túlio")
            df_jessica_pro = puxar_dados_do_google(URL_JESSICA_PRO, "Jéssica")
            
            df_som_app = puxar_dados_do_google(URL_SOM_DA_ILHA_APP_CSV, "Som da Ilha")
            df_tulio_app = puxar_dados_do_google(URL_TULIO_APP_CSV, "Túlio")
            df_jessica_app = puxar_dados_do_google(URL_JESSICA_APP_CSV, "Jéssica")
            
            lista_dfs = [df_som_pro, df_tulio_pro, df_jessica_pro, df_som_app, df_tulio_app, df_jessica_app]
            dfs = [df for df in lista_dfs if not df.empty]
            
            if dfs:
                df_unificado = pd.concat(dfs, ignore_index=True)
                if "Nome do Arquivo" not in df_unificado.columns:
                    df_unificado["Nome do Arquivo"] = ""
                
                df_unificado["Nome do Arquivo"] = df_unificado["Nome do Arquivo"].fillna("")
                mask_vazio = df_unificado["Nome do Arquivo"].astype(str).str.strip() == ""
                
                if "Artista" in df_unificado.columns and "Música" in df_unificado.columns:
                    df_unificado.loc[mask_vazio, "Nome do Arquivo"] = (
                        df_unificado.loc[mask_vazio, "Artista"].astype(str) + " - " + df_unificado.loc[mask_vazio, "Música"].astype(str)
                    )
                
                df_unificado.drop_duplicates(subset=["Nome do Arquivo"], keep="first", inplace=True)
                st.session_state["banco_completo"] = df_unificado
            else:
                st.session_state["banco_completo"] = pd.DataFrame()

inicializar_acervos()

def converter_link_google(url):
    if "docs.google.com/spreadsheets" in url:
        id_planilha = url.split("/d/")[1].split("/")[0]
        return f"https://docs.google.com/spreadsheets/d/{id_planilha}/export?format=csv"
    return url

@st.cache_data(ttl=600)
def carregar_banco_instagram(url):
    try:
        url_direta = converter_link_google(url)
        df = pd.read_csv(url_direta, sep=',')
        df.columns = [str(c).strip().lower() for c in df.columns]
        col_artista = df.columns[0]
        col_insta = df.columns[1]
        
        banco = {}
        for _, linha_planilha in df.iterrows():
            nome_artista = str(linha_planilha[col_artista]).strip().lower()
            insta = str(linha_planilha[col_insta]).strip() if pd.notna(linha_planilha[col_insta]) else ""
            if insta.lower() in ["nan", "null", "none", "0"]:
                insta = ""
            banco[nome_artista] = insta
        return banco, None
    except Exception as e:
        return {}, f"Erro ao conectar com o Google Drive: {e}"

# ==========================================
# 🛠️ PARSER DE LINHAS
# ==========================================
def processar_linha_acervo_original(linha_bruta):
    linha_original = linha_bruta.strip()
    if not linha_original:
        return None

    eh_sc = bool(re.search(r'-\s*sc\b', linha_original, flags=re.IGNORECASE))

    linha_original = linha_original.replace('"', '')
    linha_original = re.sub(r'\.(mp3|wav|mpeg|mp4|m4a|flac|aac|ogg)$', '', linha_original, flags=re.IGNORECASE).strip()
    linha_original = re.sub(r'\s*-\s*sc\s*$', '', linha_original, flags=re.IGNORECASE).strip()
        
    if "\\" in linha_original:
        linha_trabalho = linha_original.split("\\")[-1]
    else:
        linha_trabalho = linha_original

    artista = ""
    participacao = ""
    musica = ""
    formato = ""
    ano = ""
    compositores = ""
    
    padrao_comp = r'\((comp\.|compa)[^)]+\)'
    busca_comp = re.search(padrao_comp, linha_trabalho, flags=re.IGNORECASE)
    if busca_comp:
        compositores_com_parentese = busca_comp.group(0)
        compositores = re.sub(r'\((comp\.|compa)\s*', '', compositores_com_parentese, flags=re.IGNORECASE).rstrip(')')
        linha_trabalho = linha_trabalho.replace(compositores_com_parentese, "").replace("  ", " ")

    partes = [p.strip() for p in linha_trabalho.split(" - ")]
    
    if len(partes) >= 2:
        artista = partes[0]
        indice_atual = 1
        if "part." in partes[indice_atual].lower() or "part " in partes[indice_atual].lower():
            participacao = re.sub(r'\(?part\.?\s*', '', partes[indice_atual], flags=re.IGNORECASE).rstrip(')')
            indice_atual += 1
            
        if indice_atual < len(partes):
            musica = partes[indice_atual]
            indice_atual += 1
            
        if indice_atual < len(partes):
            if indice_atual == len(partes) - 1 and partes[indice_atual].isdigit():
                pass
            else:
                formato = partes[indice_atual]
                indice_atual += 1
                
        if len(partes) > indice_atual and partes[-1].isdigit():
            ano = partes[-1]
    else:
        musica = linha_trabalho

    part_str = f" - (part. {participacao})" if participacao else ""
    comp_str = f" (comp. {compositores})" if compositores else ""
    formato_str = f" - {formato}" if formato else ""
    ano_str = f" - {ano}" if ano else ""
    sc_str = " - SC" if eh_sc else ""
    
    nome_arquivo_formatado = f"{artista}{part_str} - {musica}{comp_str}{formato_str}{ano_str}{sc_str}"
    nome_arquivo_formatado = re.sub(r'\s+', ' ', nome_arquivo_formatado).strip()

    fuso_brasilia = dt.timezone(dt.timedelta(hours=-3))
    data_hoje = datetime.now(fuso_brasilia).strftime("%d/%m/%Y")

    return {
        "Música": musica, "Artista": artista, "Compositores": compositores,
        "Formato": formato, "Ano": ano, "Origem": "", "Gênero": "", "Gênero Relacionado": "",
        "Est/Idioma": "SC" if eh_sc else "", "Classificação": "", "Andamento": "",
        "Data Cadastro": data_hoje, "Participações": participacao, "Nome do Arquivo": nome_arquivo_formatado,
        "eh_sc": eh_sc
    }

def enviar_lote_completo_google(url, pacote_json):
    try:
        r = requests.post(url, json=pacote_json, headers={"Content-Type": "application/json"}, timeout=30)
        if r.status_code == 200:
            if "error" in r.text.lower():
                return False, f"Google processou com erro interno: {r.text[:100]}"
            return True, "OK"
        return False, f"Google rejeitou o bloco inteiro (Código HTTP {r.status_code})"
    except Exception as e:
        return False, f"Falha crítica de conexão: {str(e)}"

# --- INTERFACE DE NAVEGAÇÃO ---
st.sidebar.title("Painel de Controle")
if st.sidebar.button("🔄 Forçar Sincronização Completa", use_container_width=True):
    inicializar_acervos(forcar_recarga=True)
    st.rerun()

opcao = st.sidebar.radio(
    "Navegar para:",
    ["🔍 Buscar no Acervo", "📂 Ver Todo o Acervo", "💿 Formatador de Acervo", "📸 Gerador de Setlist (Instagram)"]
)
st.sidebar.markdown("---")
st.sidebar.caption("Udesc FM 🎧")

# ==========================================
# 🔍 ABA: BUSCAR NO ACERVO
# ==========================================
if opcao == "🔍 Buscar no Acervo":
    st.title("🔍 Acervo Oficial Integrado - Udesc FM")
    df_total = st.session_state["banco_completo"]
    
    if not df_total.empty:
        total_musicas = len(df_total)
        total_sc = len(df_total[df_total["Acervo Origem"] == "Som da Ilha"])
        total_tulio = len(df_total[df_total["Acervo Origem"] == "Túlio"])
        total_jessica = len(df_total[df_total["Acervo Origem"] == "Jéssica"])
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 Total no Site", f"{total_musicas} mscs")
        col2.metric("🏝️ Som da Ilha", f"{total_sc}")
        col3.metric("🎙️ Banco Túlio", f"{total_tulio}")
        col4.metric("🎙️ Banco Jéssica", f"{total_jessica}")
        
        st.markdown("---")

    st.write("Digite o artista, nome da música ou nome do arquivo:")
    termo = st.text_input("", label_visibility="collapsed")
    
    if termo and not df_total.empty:
        termo_lower = termo.lower().strip()
        mascara = pd.Series(False, index=df_total.index)
        
        for col in df_total.columns:
            if col != "Acervo Origem":
                mascara |= df_total[col].astype(str).str.lower().str.contains(termo_lower, na=False)
        
        resultados = df_total[mascara]
        if not resultados.empty:
            st.dataframe(resultados, use_container_width=True)
        else:
            st.error("Nenhuma música encontrada.")
            
    if not termo and not df_total.empty:
        st.write("### 📅 Adicionadas Recentemente no Sistema:")
        ultimas_cadastradas = df_total.tail(10).iloc[::-1]
        
        colunas_exibicao = [c for c in ["Nome do Arquivo", "Acervo Origem", "Data Cadastro"] if c in ultimas_cadastradas.columns]
        st.dataframe(ultimas_cadastradas[colunas_exibicao], use_container_width=True, hide_index=True)

# ==========================================
# 📂 ABA: VER TODO O ACERVO
# ==========================================
elif opcao == "📂 Ver Todo o Acervo":
    st.title("📋 Visualização Geral do Acervo")
    filtro_banco = st.selectbox("Selecione qual acervo deseja analisar:", ["Todos os Acervos Juntos", "Apenas Túlio", "Apenas Jéssica", "Apenas Som da Ilha"])
    
    df_exibir = st.session_state["banco_completo"]
    
    if not df_exibir.empty:
        if filtro_banco == "Apenas Túlio":
            df_exibir = df_exibir[df_exibir["Acervo Origem"] == "Túlio"]
        elif filtro_banco == "Apenas Jéssica":
            df_exibir = df_exibir[df_exibir["Acervo Origem"] == "Jéssica"]
        elif filtro_banco == "Apenas Som da Ilha":
            df_exibir = df_exibir[df_exibir["Acervo Origem"] == "Som da Ilha"]
            
        st.dataframe(df_exibir, use_container_width=True)

# ==========================================
# 💿 ABA: FORMATADOR DE ACERVO
# ==========================================
elif opcao == "💿 Formatador de Acervo":
    st.title("💿 Formatador & Hospedagem de Novos Cadastros")
    st.markdown("Insira os títulos estruturados abaixo para enviar diretamente para as planilhas cópias.")

    texto_bruto = st.text_area("Cole aqui as linhas do seu acervo:", height=150)

    if st.button("Formatar Acervo ⚡", type="primary"):
        if texto_bruto:
            linhas = texto_bruto.split('\n')
            lista_geral = []
            lista_sc = []
            
            for line in linhas:
                res = processar_linha_acervo_original(line)
                if res:
                    eh_sc = res.pop("eh_sc", False)
                    if eh_sc:
                        lista_sc.append(res)
                    else:
                        lista_geral.append(res)
            
            st.session_state["lote_geral_atual"] = pd.DataFrame(lista_geral) if lista_geral else pd.DataFrame()
            st.session_state["lote_sc_atual"] = pd.DataFrame(lista_sc) if lista_sc else pd.DataFrame()
            st.balloons()

    if "lote_geral_atual" in st.session_state and not st.session_state["lote_geral_atual"].empty:
        st.success("🎉 Lote GERAL formatado com sucesso:")
        df_editado_g = st.data_editor(st.session_state["lote_geral_atual"], use_container_width=True, key="edit_g_real")
        st.session_state["lote_geral_atual"] = df_editado_g
        
        with st.expander("📥 SALVAR NO BANCO DE DADOS (Geral)"):
            u_nome_g = st.text_input("Seu Nome (Identificação):", key="usr_g")
            destino_geral = st.selectbox("Escolha a planilha destino:", ["Planilha Túlio (Ponte)", "Planilha Jéssica (Direto)"])
            
            if st.button("Gravar Lote Geral nas Nuvens 💾", key="save_g_btn"):
                if not u_nome_g.strip():
                    st.error("Por favor, digite seu nome.")
                else:
                    url_webhook = WEBHOOK_TULIO if "Túlio" in destino_geral else WEBHOOK_JESSICA
                    total_g = len(df_editado_g)
                    
                    pacote_lote = []
                    for _, r in df_editado_g.iterrows():
                        pacote_lote.append({
                            "musica": str(r["Música"]), "artista": str(r["Artista"]), "compositores": str(r["Compositores"]),
                            "formato": str(r["Formato"]), "ano": str(r["Ano"]), "origem": str(r["Origem"]),
                            "genero": str(r["Gênero"]), "genero_relacionado": str(r["Gênero Relacionado"]),
                            "idioma_est": str(r["Est/Idioma"]), "classificacao": str(r["Classificação"]),
                            "andamento": str(r["Andamento"]), "data_cadastro": str(r["Data Cadastro"]),
                            "participacoes": str(r["Participações"]), "nome_arquivo": str(r["Nome do Arquivo"])
                        })
                    
                    with st.spinner(f"🚀 Despachando lote completo de {total_g} músicas..."):
                        sucesso, motivo = enviar_lote_completo_google(url_webhook, pacote_lote)
                    
                    if sucesso:
                        st.write("📧 Enviando e-mail de notificação...")
                        enviar_notificacao_email(destino_geral, df_editado_g, u_nome_g)
                        
                        st.write("🔄 Sincronizando banco...")
                        inicializar_acervos(forcar_recarga=True)
                        
                        st.success(f"🔥 Sucesso total! As {total_g} músicas foram salvas e integradas!")
                        st.session_state["lote_geral_atual"] = pd.DataFrame()
                        time.sleep(1.0)
                        st.rerun()
                    else:
                        st.error(f"❌ Falha no envio em bloco: {motivo}")

    if "lote_sc_atual" in st.session_state and not st.session_state["lote_sc_atual"].empty:
        st.warning("🏝️ Lote SOM DA ILHA (Catarinenses) formatado:")
        df_editado_s = st.data_editor(st.session_state["lote_sc_atual"], use_container_width=True, key="edit_s_real")
        st.session_state["lote_sc_atual"] = df_editado_s
        
        with st.expander("📥 SALVAR NO BANCO DE DADOS (Som da Ilha Ponte)"):
            u_nome_s = st.text_input("Seu Nome (Identificação):", key="usr_s")
            
            if st.button("Gravar Lote Som da Ilha nas Nuvens 💾", key="save_s_btn"):
                if not u_nome_s.strip():
                    st.error("Por favor, digite seu nome.")
                else:
                    total_s = len(df_editado_s)
                    
                    pacote_lote_s = []
                    for _, r in df_editado_s.iterrows():
                        pacote_lote_s.append({
                            "musica": str(r["Música"]), "artista": str(r["Artista"]), "compositores": str(r["Compositores"]),
                            "formato": str(r["Formato"]), "ano": str(r["Ano"]), "origem": str(r["Origem"]),
                            "genero": str(r["Gênero"]), "genero_relacionado": str(r["Gênero Relacionado"]),
                            "idioma_est": str(r["Est/Idioma"]), "classificacao": str(r["Classificação"]),
                            "andamento": str(r["Andamento"]), "data_cadastro": str(r["Data Cadastro"]),
                            "participacoes": str(r["Participações"]), "nome_arquivo": str(r["Nome do Arquivo"])
                        })
                    
                    with st.spinner(f"🚀 Despachando lote Som da Ilha de {total_s} músicas..."):
                        sucesso, motivo = enviar_lote_completo_google(WEBHOOK_SOM_DA_ILHA, pacote_lote_s)
                                
                    if sucesso:
                        st.write("📧 Enviando e-mail de notificação...")
                        enviar_notificacao_email("Som da Ilha (Ponte)", df_editado_s, u_nome_s)
                        
                        st.write("🔄 Sincronizando banco...")
                        inicializar_acervos(forcar_recarga=True)
                        
                        st.success(f"🔥 Sucesso total! As {total_s} músicas do Som da Ilha foram salvas!")
                        st.session_state["lote_sc_atual"] = pd.DataFrame()
                        time.sleep(1.0)
                        st.rerun()
                    else:
                        st.error(f"❌ Falha no envio: {motivo}")

# ==========================================
# 📸 ABA: GERADOR DE SETLIST INSTAGRAM
# ==========================================
elif opcao == "📸 Gerador de Setlist (Instagram)":
    st.title("📸 Formatador de Roteiro - Som da Ilha")
    st.markdown("Instruções: Cole o texto do Sysrad e clique em formatar.")
    banco_instagram, erro = carregar_banco_instagram(URL_GOOGLE_SHEETS)
    
    if erro: st.error(erro)
    else:
        st.success("✅ Banco de dados dos artistas conectado!")
        texto_bruto_sysrad = st.text_area("1. Cole aqui o roteiro bruto copiado do Sysrad:", height=250)

        if st.button("Formatar Roteiro ✨", type="primary"):
            if texto_bruto_sysrad:
                linhas = texto_bruto_sysrad.split('\n')
                resultado = [datetime.now().strftime("%d/%m/%Y"), ""] 
                for line in linhas:
                    line = line.strip()
                    if not line or "Marcador" in line or "Total:" in line or "DescriçãoDuração" in line:
                        continue
                    line = re.sub(r'\s*-\s*\(?part\.?[^)]+\)?\s*', ' ', line, flags=re.IGNORECASE)
                    line = re.sub(r'\s*\(?part\.?[^)]+\)?\s*', ' ', line, flags=re.IGNORECASE)
                    if " - " in line:
                        partes = line.split(" - ", 1)
                        artista_original = partes[0].strip()
                        artista_busca = artista_original.lower()
                        resto = partes[1]
                        padrao_corte = r'(\(comp|\(compa|Álbum|EP|Single|\d{4}|\d{2}:\d{2})'
                        musica_limpa = re.split(padrao_corte, resto, flags=re.IGNORECASE)[0].strip().rstrip('-').strip()
                        instagram = banco_instagram.get(artista_busca, "")
                        linha_final = f"{artista_original} - {musica_limpa} {instagram}".strip()
                        resultado.append(linha_final)
                texto_formatado = "\n".join(resultado)
                st.subheader("📋 Roteiro Pronto para as Redes Sociais:")
                st.text_area("Selecione tudo e copie:", value=texto_formatado, height=350)
                st.balloons()
