import streamlit as st
import pandas as pd
import re
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import datetime as dt

# ==========================================
# 📻 CONFIGURAÇÃO DO PAINEL & CREDENCIAIS
# ==========================================
st.set_page_config(page_title="Acervo Oficial Integrado - Udesc FM", page_icon="📻", layout="wide")

# 🔐 CONTA DO ROBÔ DE E-MAIL
EMAIL_ROBO_REMETENTE = "heytuliusradio@gmail.com"
SENHA_ROBO_REMETENTE = "nvfxdrlzpkzbugao"
EMAIL_DESTINATARIO_OFICIAL = "heytuliusmusic@gmail.com"

# 📊 LINKS DE LEITURA (PLANILHAS ORIGINAIS)
URL_SOM_DA_ILHA_PRO = "https://docs.google.com/spreadsheets/d/1zw7RPhpuInL7JqSylB_zOMu5zaqO4KgnJ7sD2eoM6gs/export?format=csv"
URL_TULIO_PRO = "https://docs.google.com/spreadsheets/d/16inPMqGCr50-MNJvwV1R4bykDgEGRwlxdbjWrlW6mfY/export?format=csv"
URL_JESSICA_PRO = "https://docs.google.com/spreadsheets/d/1MQ7OcghWNTZwaYVBTmZlMojYTXZMOe5vT1px5VALpS0/export?format=csv"
URL_GOOGLE_SHEETS = "https://docs.google.com/spreadsheets/d/1zkPm3F9W8QbOBhKvdV7jFCYqH-U8Qbru5w5TDyAHQLw/edit?usp=sharing"

# 🚀 WEBHOOKS DE ESCRITA (APPS SCRIPT)
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
            linhas_musicas.append(f"• {linha['Nome do Arquivo']}.mp3")
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
    except Exception as e:
        pass

# ==========================================
# 🔄 LEITOR INTEGRADO DAS PLANILHAS
# ==========================================
@st.cache_data(ttl=5)
def carregar_planilha_especifica(nome_acervo):
    url_map = {
        "Som da Ilha": URL_SOM_DA_ILHA_PRO,
        "Túlio": URL_TULIO_PRO,
        "Jéssica": URL_JESSICA_PRO
    }
    url = url_map.get(nome_acervo)
    try:
        df = pd.read_csv(url, sep=None, engine='python', on_bad_lines='skip', encoding='utf-8')
        if df.empty:
            df = pd.read_csv(url, sep=None, engine='python', on_bad_lines='skip', encoding='latin1')
        if not df.empty:
            df.dropna(how='all', inplace=True)
            df.columns = [str(c).strip() for c in df.columns]
            df["Acervo Origem"] = nome_acervo
            return df
    except:
        pass
    return pd.DataFrame()

def carregar_todos_os_acervos_reais():
    lista_dfs = []
    for nome in ["Som da Ilha", "Túlio", "Jéssica"]:
        df_part = carregar_planilha_especifica(nome)
        if not df_part.empty:
            lista_dfs.append(df_part)
    if lista_dfs:
        return pd.concat(lista_dfs, ignore_index=True)
    return pd.DataFrame()

# ==========================================
# FUNÇÕES DO GERADOR DE SETLIST (INSTAGRAM)
# ==========================================
def converter_link_google(url):
    if "docs.google.com/spreadsheets" in url:
        id_planilha = url.split("/d/")[1].split("/")[0]
        return f"https://docs.google.com/spreadsheets/d/{id_planilha}/export?format=csv"
    return url

@st.cache_data(ttl=300)
def carregar_banco_instagram(url):
    try:
        url_direta = converter_link_google(url)
        df = pd.read_csv(url_direta)
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
# LÓGICA DO FORMATADOR DE ACERVO ORIGINAL
# ==========================================
def processar_linha_acervo_original(linha_bruta):
    linha_original = linha_bruta.strip().replace('"', '')
    if not linha_original:
        return None
        
    linha_limpa_fim = linha_original.lower()
    if linha_limpa_fim.endswith(".mp3"):
        linha_original = linha_original[:-4].strip()
        linha_limpa_fim = linha_limpa_fim[:-4].strip()
        
    eh_sc = False
    if linha_limpa_fim.endswith("- sc") or linha_limpa_fim.endswith("-sc"):
        eh_sc = True
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
        "eh_sc": eh_sc, "Música": musica, "Artista": artist, "Compositores": compositores,
        "Formato": formato, "Ano": ano, "Origem": "", "Gênero": "", "Gênero Relacionado": "",
        "Est/Idioma": "SC" if eh_sc else "", "Classificação": "", "Andamento": "",
        "Data Cadastro": data_hoje, "Participações": participacao, "Nome do Arquivo": nome_arquivo_formatado
    }

# --- INTERFACE DE NAVEGAÇÃO ---
st.sidebar.title("Painel de Controle")
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
    df_total = carregar_todos_os_acervos_reais()
    
    st.write("Digite o artista, nome da música ou nome do arquivo:")
    termo = st.text_input("", label_visibility="collapsed")
    
    if termo:
        termo_lower = termo.lower()
        mascara = pd.Series(False, index=df_total.index)
        for col in df_total.columns:
            if col != "Acervo Origem":
                mascara |= df_total[col].astype(str).str.lower().str.contains(termo_lower, na=False)
        
        resultados = df_total[mascara]
        if not resultados.empty:
            st.dataframe(resultados, use_container_width=True)
        else:
            st.error("Nenhuma música encontrada.")

# ==========================================
# 📂 ABA: VER TODO O ACERVO
# ==========================================
elif opcao == "📂 Ver Todo o Acervo":
    st.title("📋 Visualização Geral do Acervo")
    filtro_banco = st.selectbox("Selecione qual acervo deseja analisar:", ["Todos os Acervos Juntos", "Apenas Túlio", "Apenas Jéssica", "Apenas Som da Ilha"])
    
    if filtro_banco == "Todos os Acervos Juntos":
        df_exibir = carregar_todos_os_acervos_reais()
    elif filtro_banco == "Apenas Túlio":
        df_exibir = carregar_planilha_especifica("Túlio")
    elif filtro_banco == "Apenas Jéssica":
        df_exibir = carregar_planilha_especifica("Jéssica")
    else:
        df_exibir = carregar_planilha_especifica("Som da Ilha")
        
    if not df_exibir.empty:
        st.dataframe(df_exibir, use_container_width=True)

# ==========================================
# 💿 ABA: FORMATADOR DE ACERVO + SUPORTE A REDIRECIONAMENTO (ANTI-LOOP)
# ==========================================
elif opcao == "💿 Formatador de Acervo":
    st.title("💿 Formatador & Hospedagem de Novos Cadastros")
    st.markdown("Insira os títulos estruturados abaixo. Ao confirmar, o site enviará os dados diretamente via API para as planilhas.")

    texto_bruto = st.text_area("Cole aqui as linhas do seu acervo:", height=150)

    if st.button("Formatar Acervo ⚡", type="primary"):
        if texto_bruto:
            linhas = texto_bruto.split('\n')
            lista_geral = []
            lista_sc = []
            
            for linha in linhas:
                res = processar_linha_acervo_original(linha)
                if res:
                    eh_sc = res.get("eh_sc", False)
                    if eh_sc:
                        dados_sc = {
                            "Música": res["Música"], "Artista": res["Artista"], "Compositores": res["Compositores"],
                            "Formato": res["Formato"], "Ano": res["Ano"], "Origem": res["Origem"],
                            "Gênero": res["Gênero"], "Gênero Relacionado": res["Gênero Relacionado"], "Est": "SC",
                            "Classificação": res["Classificação"], "Andamento": res["Andamento"],
                            "Data Cadastro": res["Data Cadastro"], "Participações": res["Participações"], "Nome do Arquivo": res["Nome do Arquivo"]
                        }
                        lista_sc.append(dados_sc)
                    else:
                        dados_geral = {
                            "Música": res["Música"], "Artista": res["Artista"], "Compositores": res["Compositores"],
                            "Formato": res["Formato"], "Ano": res["Ano"], "Origem": res["Origem"],
                            "Gênero": res["Gênero"], "Gênero Relacionado": res["Gênero Relacionado"], "Idioma": "",
                            "Classificação": res["Classificação"], "Andamento": res["Andamento"],
                            "Data Cadastro": res["Data Cadastro"], "Participações": res["Participações"], "Nome do Arquivo": res["Nome do Arquivo"]
                        }
                        lista_geral.append(dados_geral)
            
            if lista_geral: st.session_state["lote_geral_atual"] = pd.DataFrame(lista_geral)
            if lista_sc: st.session_state["lote_sc_atual"] = pd.DataFrame(lista_sc)
            st.balloons()

    # Fluxo Lote Geral
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
                    sucessos = 0
                    
                    with st.spinner("Hospedando dados via API (Seguindo Redirecionamento)..."):
                        for _, r in df_editado_g.iterrows():
                            payload = {
                                "musica": str(r["Música"]), "artista": str(r["Artista"]), "compositores": str(r["Compositores"]),
                                "formato": str(r["Formato"]), "ano": str(r["Ano"]), "origem": str(r["Origem"]),
                                "genero": str(r["Gênero"]), "genero_relacionado": str(r["Gênero Relacionado"]),
                                "idioma_est": str(r["Idioma"]), "classificacao": str(r["Classificação"]),
                                "andamento": str(r["Andamento"]), "data_cadastro": str(r["Data Cadastro"]),
                                "participacoes": str(r["Participações"]), "nome_arquivo": str(r["Nome do Arquivo"])
                            }
                            try:
                                headers = {"Content-Type": "application/json"}
                                # CRUCIAL: allow_redirects=True impede o Python de travar carregando para sempre no Google
                                res = requests.post(url_webhook, json=payload, headers=headers, allow_redirects=True, timeout=15)
                                if res.status_code == 200 or "Sucesso" in res.text:
                                    sucessos += 1
                            except Exception as e:
                                pass
                                
                    if sucessos > 0:
                        st.success(f"🔥 Sucesso! {sucessos} músicas foram salvas na {destino_geral}!")
                        enviar_notificacao_email(destino_geral, df_editado_g, u_nome_g)
                        st.session_state["lote_geral_atual"] = pd.DataFrame()
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("O Google não acusou recebimento. Verifique se a implantação do script aceita JSON.")

    # Fluxo Lote SC
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
                    sucessos = 0
                    with st.spinner("Hospedando dados via API..."):
                        for _, r in df_editado_s.iterrows():
                            payload = {
                                "musica": str(r["Música"]), "artista": str(r["Artista"]), "compositores": str(r["Compositores"]),
                                "formato": str(r["Formato"]), "ano": str(r["Ano"]), "origem": str(r["Origem"]),
                                "genero": str(r["Gênero"]), "genero_relacionado": str(r["Gênero Relacionado"]),
                                "idioma_est": str(r["Est"]), "classificacao": str(r["Classificação"]),
                                "andamento": str(r["Andamento"]), "data_cadastro": str(r["Data Cadastro"]),
                                "participacoes": str(r["Participações"]), "nome_arquivo": str(r["Nome do Arquivo"])
                            }
                            try:
                                headers = {"Content-Type": "application/json"}
                                # Força o redirecionamento seguro para evitar carregamento infinito
                                res = requests.post(WEBHOOK_SOM_DA_ILHA, json=payload, headers=headers, allow_redirects=True, timeout=15)
                                if res.status_code == 200 or "Sucesso" in res.text:
                                    sucessos += 1
                            except Exception as e:
                                pass
                                
                    if sucessos > 0:
                        st.success(f"🔥 Sucesso! {sucessos} músicas foram gravadas no Som da Ilha!")
                        enviar_notificacao_email("Som da Ilha (Ponte)", df_editado_s, u_nome_s)
                        st.session_state["lote_sc_atual"] = pd.DataFrame()
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Erro ao processar lote no Som da Ilha.")

# ==========================================
# 📸 ABA: GERADOR DE SETLIST INSTAGRAM
# ==========================================
elif opcao == "📸 Gerador de Setlist (Instagram)":
    st.title("📸 Formatador de Roteiro - Som da Ilha")
    st.markdown("Instruções: Cole o texto do Sysrad e clique em formatar.")
    banco_instagram, erro = carregar_banco_instagram(URL_GOOGLE_SHEETS)
    
    if erro: st.error(erro)
    else:
        st.success("✅ Banco de dados dos artistas conectado em tempo real!")
        texto_bruto_sysrad = st.text_area("1. Cole aqui o roteiro bruto copiado do Sysrad:", height=250)

        if st.button("Formatar Roteiro ✨", type="primary"):
            if texto_bruto_sysrad:
                linhas = texto_bruto_sysrad.split('\n')
                resultado = [datetime.now().strftime("%d/%m/%Y"), ""] 
                for linha in lines:
                    linha = linha.strip()
                    if not linha or "Marcador" in linha or "Total:" in linha or "DescriçãoDuração" in linha: continue
                    linha = re.sub(r'\s*-\s*\(?part\.?[^)]+\)?\s*', ' ', linha, flags=re.IGNORECASE)
                    linha = re.sub(r'\s*\(?part\.?[^)]+\)?\s*', ' ', linha, flags=re.IGNORECASE)
                    if " - " in linha:
                        partes = inline_split := linha.split(" - ", 1)
                        artista_original = partes[0].strip()
                        artista_busca = artista_original.lower()
                        resto = partes[1]
                        padrao_corte = r'(\(comp|\(compa|Álbum|EP|Single|\d{4}|\d{2}:\d{2})'
                        musica_limpa = re.split(padrao_corte, resto, flags=re.IGNORECASE)[0].strip().rstrip('-').strip()
                        instagram = banco_instagram.get(artista_busca, "")
                        linha_final = f"{artista_original} - {musica_limpa} {instagram}".strip()
                        resultado.append(linha_final)
                texto_formatated = "\n".join(resultado)
                st.subheader("📋 Roteiro Pronto para as Redes Sociais:")
                st.text_area("Selecione tudo e copie:", value=texto_formatated, height=350)
                st.balloons()
