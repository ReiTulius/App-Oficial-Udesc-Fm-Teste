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
# 📊 LINKS DAS PLANILHAS GOOGLE
# ==========================================
URL_CARGA_SOM_DA_ILHA = "https://docs.google.com/spreadsheets/d/1zw7RPhpuInL7JqSylB_zOMu5zaqO4KgnJ7sD2eoM6gs/edit?usp=drive_link"
URL_CARGA_TULIO = "https://docs.google.com/spreadsheets/d/16inPMqGCr50-MNJvwV1R4bykDgEGRwlxdbjWrlW6mfY/edit?usp=drive_link"
URL_CARGA_JESSICA = "https://docs.google.com/spreadsheets/d/1MQ7OcghWNTZwaYVBTmZlMojYTXZMOe5vT1px5VALpS0/edit?usp=drive_link"

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
    return False

def padronizar_df(df_bruto):
    """Garante que o DataFrame tenha as colunas limpas e padronizadas"""
    if df_bruto.empty:
        return pd.DataFrame(columns=["Artista", "Música", "Nome do Arquivo"])
    
    # Limpa espaços nos nomes das colunas e converte para string
    df_bruto.columns = [str(c).strip() for c in df_bruto.columns]
    
    # Cria mapeamento inteligente ignorando maiúsculas/minúsculas
    mapeamento = {}
    for col in df_bruto.columns:
        col_lower = col.lower()
        if "artista" in col_lower: mapeamento[col] = "Artista"
        elif "música" in col_lower or "musica" in col_lower: mapeamento[col] = "Música"
        elif "arquivo" in col_lower: mapeamento[col] = "Nome do Arquivo"
        
    df_renomeado = df_bruto.rename(columns=mapeamento)
    
    # Garante a existência das colunas principais de busca
    for principal in ["Artista", "Música", "Nome do Arquivo"]:
        if principal not in df_renomeado.columns:
            df_renomeado[principal] = ""
            
    return df_renomeado

@st.cache_data(ttl=60)
def carregar_banco_oficial_github():
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(URL_API_GITHUB, headers=headers)
    
    if response.status_code == 200:
        dados_json = response.json()
        conteudo_base64 = dados_json["content"]
        conteudo_csv = base64.b64decode(conteudo_base64).decode("utf-8")
        df = pd.read_csv(StringIO(conteudo_csv))
        return padronizar_df(df), dados_json["sha"]
    
    else:
        # Se der erro ou não achar no GitHub, lê e junta direto as planilhas do Google em tempo real
        try:
            df_list = []
            for url in [URL_CARGA_SOM_DA_ILHA, URL_CARGA_TULIO, URL_CARGA_JESSICA]:
                url_csv = converter_link_google(url)
                df_temp = pd.read_csv(url_csv)
                df_list.append(padronizar_df(df_temp))
                
            df_consolidado = pd.concat(df_list, ignore_index=True)
            df_consolidado.drop_duplicates(subset=["Nome do Arquivo"], keep="first", inplace=True)
            
            # Tenta salvar no GitHub para as próximas vezes, mas se não conseguir, não trava o app
            salvar_banco_no_github(df_consolidado, "Carga inicial unificada", response.json().get("sha") if response.status_code == 200 else None)
            return df_consolidado, None
        except Exception:
            return pd.DataFrame(columns=["Artista", "Música", "Nome do Arquivo"]), None

@st.cache_data(ttl=300)
def carregar_banco_instagram(url):
    try:
        url_direta = converter_link_google(url)
        df = pd.read_csv(url_direta)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
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
# 💿 LÓGICA DO FORMATADOR DE ARQUIVOS (PRESERVADA)
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
            # Filtro inteligente e tolerante a erros
            mascara = (
                df_acervo["Artista"].astype(str).str.lower().str.contains(termo, na=False) |
                df_acervo["Música"].astype(str).str.lower().str.contains(termo, na=False) |
                df_acervo["Nome do Arquivo"].astype(str).str.lower().str.contains(termo, na=False)
            )
            resultados = df_acervo[mascara]
            if not resultados.empty:
                st.success(f"🎉 Encontradas {len(resultados)} músicas!")
                st.dataframe(resultados, use_container_width=True)
            else: 
                st.error("Nenhuma música encontrada com esse termo.")
        else: 
            st.info(f"💡 Banco conectado com sucesso! Há {len(df_acervo)} músicas carregadas no sistema prontas para consulta.")
    else:
        st.error("Erro ao processar as col
