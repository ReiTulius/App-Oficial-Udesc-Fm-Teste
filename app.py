import streamlit as st
import pandas as pd
import requests
import base64
import json
import re
from datetime import datetime
from io import StringIO

# Configuração da página do aplicativo
st.set_page_config(page_title="Painel Udesc FM - Mídias", page_icon="📻", layout="wide")

# ==========================================
# ⚙️ CONFIGURAÇÕES DE CONEXÃO (GITHUB SECRETS)
# ==========================================
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPOSITORIO = st.secrets["REPOSITORIO"]
except Exception:
    st.error("🔑 Erro: Você precisa configurar o 'GITHUB_TOKEN' e o 'REPOSITORIO' nos Secrets do Streamlit!")
    st.stop()

ARQUIVO_BANCO = "acervo_udesc.csv"
URL_API_GITHUB = f"https://api.github.com/repos/{REPOSITORIO}/contents/{ARQUIVO_BANCO}"

# ==========================================
# 📊 LINKS DEFINITIVOS DAS PLANILHAS GOOGLE
# ==========================================
URL_CARGA_SOM_DA_ILHA = "https://docs.google.com/spreadsheets/d/1zw7RPhpuInL7JqSylB_zOMu5zaqO4KgnJ7sD2eoM6gs/edit?usp=drive_link"
URL_CARGA_TULIO = "https://docs.google.com/spreadsheets/d/16inPMqGCr50-MNJvwV1R4bykDgEGRwlxdbjWrlW6mfY/edit?usp=drive_link"
URL_CARGA_JESSICA = "https://docs.google.com/spreadsheets/d/1MQ7OcghWNTZwaYVBTmZlMojYTXZMOe5vT1px5VALpS0/edit?usp=drive_link"

# Usando o acervo do Som da Ilha também como banco inicial de arrobas do Instagram
URL_INSTAGRAM_SHEETS = URL_CARGA_SOM_DA_ILHA

# ==========================================
# 💾 REGRAS DE LEITURA E ESCRITA NO GITHUB
# ==========================================
def converter_link_google(url):
    if "docs.google.com/spreadsheets" in url:
        try:
            id_planilha = url.split("/d/")[1].split("/")[0]
            return f"https://docs.google.com/spreadsheets/d/{id_planilha}/export?format=csv"
        except Exception:
            return url
    return url

def salvar_banco_no_github(df, mensagem_commit, sha=None):
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    conteudo_csv = df.to_csv(index=False)
    conteudo_base64 = base64.b64encode(conteudo_csv.encode("utf-8")).decode("utf-8")
    
    dados_envio = {
        "message": mensagem_commit,
        "content": conteudo_base64
    }
    if sha:
        dados_envio["sha"] = sha
        
    res = requests.put(URL_API_GITHUB, headers=headers, data=json.dumps(dados_envio))
    if res.status_code in [200, 201]:
        st.cache_data.clear()
        return True
    else:
        st.error(f"Falha ao salvar dados no GitHub: {res.text}")
        return False

@st.cache_data(ttl=60)
def carregar_banco_oficial_github():
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(URL_API_GITHUB, headers=headers)
    
    if response.status_code == 200:
        dados_json = response.json()
        conteudo_base64 = dados_json["content"]
        conteudo_csv = base64.b64decode(conteudo_base64).decode("utf-8")
        df = pd.read_csv(StringIO(conteudo_csv))
        return df, dados_json["sha"]
    
    elif response.status_code == 404:
        try:
            st.info("📥 Sincronizando o histórico integrado das 3 planilhas (Som da Ilha, Tulio e Jéssica) pela primeira vez...")
            
            # Download da Planilha Som da Ilha
            url_csv_ilha = converter_link_google(URL_CARGA_SOM_DA_ILHA)
            df_ilha = pd.read_csv(url_csv_ilha)
            
            # Download da Planilha Tulio
            url_csv_tulio = converter_link_google(URL_CARGA_TULIO)
            df_tulio = pd.read_csv(url_csv_tulio)
            
            # Download da Planilha Jéssica
            url_csv_jessica = converter_link_google(URL_CARGA_JESSICA)
            df_jessica = pd.read_csv(url_csv_jessica)
            
            # Une as 3 planilhas em um único banco de dados unificado
            df_consolidado = pd.concat([df_ilha, df_tulio, df_jessica], ignore_index=True)
            df_consolidado.columns = [str(c).strip() for c in df_consolidado.columns]
            
            # Elimina linhas duplicadas baseadas no nome do arquivo
            for col_nome in ["Nome do Arquivo", "Nome do arquivo"]:
                if col_nome in df_consolidado.columns:
                    df_consolidado.drop_duplicates(subset=[col_nome], keep="first", inplace=True)
                    break
                
            salvar_banco_no_github(df_consolidado, "Migração inicial unificada das 3 planilhas")
            st.success("🎉 Histórico integrado com sucesso! O site agora controla o acervo oficial.")
            return df_consolidado, None
        except Exception as e:
            st.error(f"Erro na migração inicial: {e}. Certifique-se de que os links possuem permissão de leitura para qualquer pessoa.")
            return pd.DataFrame(), None
    else:
        st.error(f"Erro ao conectar ao GitHub: {response.status_code}. Verifique as permissões do seu token.")
        return pd.DataFrame(), None

@st.cache_data(ttl=300)
def carregar_banco_instagram(url):
    try:
        url_direta = converter_link_google(url)
        df = pd.read_csv(url_direta)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Procura colunas correspondentes a artista e arroba
        col_artista = df.columns[0]
        col_insta = df.columns[1]
        for c in df.columns:
            if "artista" in c: col_artista = c
            if "insta" in c or "arroba" in c: col_insta = c
            
        banco = {}
        for _, linha in df.iterrows():
            nome_art = str(linha[col_artista]).strip().lower()
            insta = str(linha[col_insta]).strip() if pd.notna(linha[col_insta]) else ""
            if insta.lower() in ["nan", "null", "none", "0", ""]: insta = ""
            elif not insta.startswith("@"): insta = "@" + insta
            banco[nome_art] = insta
        return banco, None
    except Exception as e:
        return {}, str(e)

# ==========================================
# 💿 LÓGICA DO FORMATADOR DE ARQUIVOS
# ==========================================
def processar_linha_musica(linha_bruta):
    linha_original = linha_bruta.strip().replace('"', '')
    if not linha_original: return None
    linha_limpa = linha_original.lower()
    if linha_limpa.endswith(".mp3"): linha_limpa = linha_limpa[:-4].strip()
    eh_sc = True if (linha_limpa.endswith("- sc") or linha_limpa.endswith("-sc")) else False
    
    linha_trabalho = linha_original.split("\\")[-1] if "\\" in linha_original else linha_original
    if linha_trabalho.lower().endswith(".mp3"): linha_trabalho = linha_trabalho[:-4]
    if eh_sc: linha_trabalho = re.sub(r'\s*-\s*sc\s*$', '', linha_trabalho, flags=re.IGNORECASE).strip()
    
    artista, participacao, musica, formato, ano, compositores = "", "", "", "", "", ""
    busca_comp = re.search(r'\((comp\.|compa)[^)]+\)', linha_trabalho, flags=re.IGNORECASE)
    if busca_comp:
        comp_parentese = busca_comp.group(0)
        compositores = re.sub(r'\((comp\.|compa)\s*', '', comp_parentese, flags=re.IGNORECASE).rstrip(')')
        linha_trabalho = linha_trabalho.replace(comp_parentese, "").replace("  ", " ")

    partes = [p.strip() for p in linha_trabalho.split(" - ")]
    if len(partes) < 2: return None
    artista = partes[0]
    idx = 1
    if idx < len(partes) and ("part." in partes[idx].lower() or "part " in partes[idx].lower()):
        participacao = re.sub(r'\(?part\.?\s*', '', partes[idx], flags=re.IGNORECASE).rstrip(')')
        idx += 1
    if idx < len(partes): musica = partes[idx]; idx += 1
    if idx < len(partes):
        if not (idx == len(partes) - 1 and partes[idx].isdigit()):
            formato = partes[idx]; idx += 1
    if len(partes) > idx and partes[-1].isdigit(): ano = partes[-1]

    p_str = f" - (part. {participacao})" if participacao else ""
    c_str = f" (comp. {compositores})" if compositores else ""
    f_str = f" - {formato}" if formato else ""
    a_str = f" - {ano}" if ano else ""
    s_str = " - SC" if eh_sc else ""
    nome_final = re.sub(r'\s+', ' ', f"{artista}{p_str} - {musica}{c_str}{f_str}{a_str}{s_str}").strip()

    return {
        "Música": musica, "Artista": artista, "Compositores": compositores, "Formato": formato, "Ano": ano,
        "Origem": "", "Gênero": "", "Gênero Relacionado": "", "Est/Idioma": "SC" if eh_sc else "", "Classificação": "",
        "Andamento": "", "Data Cadastro": datetime.now().strftime("%d/%m/%Y"), "Participações": participacao, "Nome do Arquivo": nome_final
    }

# --- MENU LATERAL DE NAVEGAÇÃO ---
st.sidebar.title("📻 Painel de Controle")
opcao = st.sidebar.radio(
    "Navegar para:",
    ["🔍 Buscar no Acervo", "📝 Cadastrar Novas Músicas", "💿 Formatador de Linhas", "📸 Gerador de Setlist (Instagram)"]
)

# --- ABA 1: BUSCA NO ACERVO ---
if opcao == "🔍 Buscar no Acervo":
    st.title("🔍 Acervo Oficial Integrado - Udesc FM")
    df_acervo, _ = carregar_banco_oficial_github()
    
    if not df_acervo.empty:
        termo = st.text_input("Digite o artista, nome da música ou nome do arquivo:")
        if termo:
            termo = termo.lower()
            mascara = pd.Series(False, index=df_acervo.index)
            for col in ["Artista", "Música", "Nome do Arquivo", "Nome do arquivo"]:
                if col in df_acervo.columns:
                    mascara |= df_acervo[col].astype(str).str.lower().str.contains(termo, na=False)
            resultados = df_acervo[mascara]
            if not resultados.empty:
                st.success(f"🎉 Encontradas {len(resultados)} músicas!")
                st.dataframe(resultados, use_container_width=True)
            else: st.error("Nenhuma música encontrada.")
        else: st.info(f"💡 Banco integrado operando via GitHub! Atualmente existem {len(df_acervo)} músicas unificadas no sistema.")

# --- ABA 2: CADASTRO MANUAL ---
elif opcao == "📝 Cadastrar Novas Músicas":
    st.title("📝 Incluir Nova Música no Acervo Oficial")
    df_acervo, sha_atual = carregar_banco_oficial_github()
    
    with st.form("form_cadastro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            artista = st.text_input("Nome do Artista:")
            musica = st.text_input("Nome da Música:")
            participacao = st.text_input("Participações (opcional):")
            compositores = st.text_input("Compositores (opcional):")
        with col2:
            ano = st.text_input("Ano de Lançamento (opcional):")
            formato = st.text_input("Formato/Álbum (opcional):")
            origem = st.text_input("Origem (Pasta no Sysrad):")
            est_idioma = st.selectbox("Classificação:", ["", "SC", "Nacional", "Internacional"])
            
        if st.form_submit_button("Salvar Música no Acervo 💾", type="primary"):
            if not artista or not musica: st.error("⚠️ Artista e Música são obrigatórios!")
            else:
                p_str = f" - (part. {participacao})" if participacao else ""
                c_str = f" (comp. {compositores})" if compositores else ""
                f_str = f" - {formato}" if formato else ""
                a_str = f" - {ano}" if ano else ""
                s_str = " - SC" if est_idioma == "SC" else ""
                nome_arq = re.sub(r'\s+', ' ', f"{artista}{p_str} - {musica}{c_str}{f_str}{a_str}{s_str}").strip()
                
                nova_linha = {
                    "Música": musica, "Artista": artista, "Compositores": compositores, "Formato": formato, "Ano": ano,
                    "Origem": origem, "Gênero": "", "Gênero Relacionado": "", "Est/Idioma": est_idioma, "Classificação": "",
                    "Andamento": "", "Data Cadastro": datetime.now().strftime("%d/%m/%Y"), "Participações": participacao, "Nome do Arquivo": nome_arq
                }
                df_novo = pd.concat([df_acervo, pd.DataFrame([nova_linha])], ignore_index=True)
                if salvar_banco_no_github(df_novo, f"Adicionado {artista} - {musica}", sha_atual):
                    st.success("🎉 Gravada com sucesso no Acervo Oficial!")

# --- ABA 3: FORMATADOR EM LOTE ---
elif opcao == "💿 Formatador de Linhas":
    st.title("💿 Automatizador de Linhas do Acervo")
    df_acervo, sha_atual = carregar_banco_oficial_github()
    texto_bruto = st.text_area("Cole aqui as linhas brutas:", height=200)
    
    if st.button("Processar Linhas 🚀", type="primary"):
        if texto_bruto:
            linhas = texto_bruto.split('\n')
            lista_novas = []
            for l in lines:
                res = processar_linha_musica(l)
                if res: lista_novas.append(res)
            if lista_novas:
                df_novas = pd.DataFrame(lista_novas)
                st.success(f"Identificadas {len(df_novas)} linhas!")
                st.dataframe(df_novas, use_container_width=True)
                st.session_state["df_lote_temporario"] = df_novas
            else: st.warning("Nenhuma linha válida encontrada.")

    if "df_lote_temporario" in st.session_state:
        if st.button("📥 CONFIRMAR: Gravar Todas no Acervo definitivo?"):
            df_novas = st.session_state["df_lote_temporario"]
            df_final = pd.concat([df_acervo, df_novas], ignore_index=True)
            for col_nome in ["Nome do Arquivo", "Nome do arquivo"]:
                if col_nome in df_final.columns:
                    df_final.drop_duplicates(subset=[col_nome], keep="first", inplace=True)
                    break
            if salvar_banco_no_github(df_final, "Lote adicionado", sha_atual):
                st.success("Gravado com sucesso!")
                del st.session_state["df_lote_temporario"]

# --- ABA 4: INSTAGRAM ---
elif opcao == "📸 Gerador de Setlist (Instagram)":
    st.title("📸 Formatador de Roteiro")
    banco_instagram, erro = carregar_banco_instagram(URL_INSTAGRAM_SHEETS)
    if erro: st.error(f"Erro ao ler banco de Instagram: {erro}")
    else:
        texto_sysrad = st.text_area("Cole aqui o roteiro do Sysrad:", height=200)
        if st.button("Formatar Roteiro ✨", type="primary"):
            if texto_sysrad:
                linhas = texto_sysrad.split('\n')
                resultado = [datetime.now().strftime("%d/%m/%Y"), ""]
                for linha in linhas:
                    linha = linha.strip()
                    if not linha or any(x in linha for x in ["Marcador", "Total:", "DescriçãoDuração"]): continue
                    linha = re.sub(r'\s*-\s*\(?part\.?[^)]+\)?\s*', ' ', linha, flags=re.IGNORECASE)
                    if " - " in linha:
                        partes = linha.split(" - ", 1)
                        art_orig = partes[0].strip()
                        mus_limpa = re.split(r'(\(comp|\(compa|Álbum|EP|Single|\d{4}|\d{2}:\d{2})', partes[1], flags=re.IGNORECASE)[0].strip().rstrip('-').strip()
                        insta = banco_instagram.get(art_orig.lower(), "")
                        resultado.append(f"{art_orig} - {mus_limpa} {insta}".strip())
                st.text_area("Pronto para as Redes Sociais:", value="\n".join(resultado), height=300)
