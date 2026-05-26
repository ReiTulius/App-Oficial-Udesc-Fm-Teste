import streamlit as st
import pandas as pd
import requests
import base64
import json
import re
from datetime import datetime

# Configuração da página do aplicativo
st.set_page_config(page_title="Painel Udesc FM - Tulio", page_icon="📻", layout="wide")

# ==========================================
# ⚙️ CONFIGURAÇÕES DE CONEXÃO (GITHUB SECRETS)
# ==========================================
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPOSITORIO = st.secrets["REPOSITORIO"] # Formato: "usuario/repositorio"
except Exception:
    st.error("🔑 Erro: Você precisa configurar o 'GITHUB_TOKEN' e o 'REPOSITORIO' nos Secrets do Streamlit!")
    st.stop()

ARQUIVO_BANCO = "acervo_udesc.csv"
URL_API_GITHUB = f"https://api.github.com/repos/{REPOSITORIO}/contents/{ARQUIVO_BANCO}"

# Link do Google Sheets antigo (apenas para puxar a carga inicial das 9 mil linhas caso o arquivo do GitHub ainda não exista)
URL_CARGA_INICIAL_GOOGLE = "https://docs.google.com/spreadsheets/d/1zkPm3F9W8QbOBhKvdV7jFCYqH-U8Qbru5w5TDyAHQLw/edit?usp=sharing"
URL_INSTAGRAM_SHEETS = "https://docs.google.com/spreadsheets/d/1zkPm3F9W8QbOBhKvdV7jFCYqH-U8Qbru5w5TDyAHQLw/edit?usp=sharing"

# --- MENU LATERAL DE NAVEGAÇÃO ---
st.sidebar.title("📻 Painel de Controle")
st.sidebar.markdown("Escolha a ferramenta que deseja usar agora:")
opcao = st.sidebar.radio(
    "Navegar para:",
    ["🔍 Buscar no Acervo", "📝 Cadastrar Novas Músicas", "💿 Formatador de Linhas", "📸 Gerador de Setlist (Instagram)"]
)
st.sidebar.markdown("---")
st.sidebar.caption("Desenvolvido para otimizar a programação da Udesc FM 🎧")


# ==========================================
# 💾 REGRAS DE LEITURA E ESCRITA NO GITHUB
# ==========================================
def converter_link_google(url):
    if "docs.google.com/spreadsheets" in url:
        id_planilha = url.split("/d/")[1].split("/")[0]
        return f"https://docs.google.com/spreadsheets/d/{id_planilha}/export?format=csv"
    return url

@st.cache_data(ttl=60)
def carregar_banco_oficial_github():
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(URL_API_GITHUB, headers=headers)
    
    if response.status_code == 200:
        dados_json = response.json()
        conteudo_base64 = dados_json["content"]
        conteudo_csv = base64.b64decode(conteudo_base64).decode("utf-8")
        from io import StringIO
        df = pd.read_csv(StringIO(conteudo_csv))
        return df, dados_json["sha"]
    
    elif response.status_code == 404:
        # Se o arquivo não existe no GitHub, faz a carga inicial a partir do Google Sheets antigo (As 9 mil linhas)
        try:
            st.info("📥 Criando banco de dados oficial no GitHub com base no histórico das planilhas antigas...")
            url_csv = converter_link_google(URL_CARGA_INICIAL_GOOGLE)
            df_inicial = pd.read_csv(url_csv)
            salvar_banco_no_github(df_inicial, "Carga inicial do acervo histórico")
            return df_inicial, None
        except Exception as e:
            return pd.DataFrame(), None
    else:
        st.error(f"Erro ao conectar ao GitHub: {response.status_code}")
        return pd.DataFrame(), None

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
        st.cache_data.clear() # Limpa o cache para atualizar o app na hora
        return True
    else:
        st.error(f"Falha ao salvar dados no GitHub: {res.text}")
        return False

@st.cache_data(ttl=300)
def carregar_banco_instagram(url):
    try:
        url_direta = converter_link_google(url)
        df = pd.read_csv(url_direta)
        df.columns = [str(c).strip().lower() for c in df.columns]
        col_artista = df.columns[0]
        col_insta = df.columns[1]
        banco = {}
        for _, linha in df.iterrows():
            nome_art = str(linha[col_artista]).strip().lower()
            insta = str(linha[col_insta]).strip() if pd.notna(linha[col_insta]) else ""
            if insta.lower() in ["nan", "null", "none", "0"]: insta = ""
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
        "Música": musica, "Artista": artist_name := artista, "Compositores": compositores, "Formato": formato, "Ano": ano,
        "Origem": "", "Gênero": "", "Gênero Relacionado": "", "Est/Idioma": "SC" if eh_sc else "", "Classificação": "",
        "Andamento": "", "Data Cadastro": datetime.now().strftime("%d/%m/%Y"), "Participações": participacao, "Nome do Arquivo": nome_final, "eh_sc": eh_sc
    }


# ==========================================
# 🖥️ CORPO E EXECUÇÃO DAS ABAS DO SITE
# ==========================================

# --- ABA 1: BUSCA NO ACERVO ---
if opcao == "🔍 Buscar no Acervo":
    st.title("🔍 Acervo Oficial Integrado - Udesc FM")
    st.markdown("Busca instantânea e inteligente nas músicas cadastradas no acervo oficial.")
    
    df_acervo, _ = carregar_banco_oficial_github()
    
    if not df_acervo.empty:
        termo = st.text_input("Digite o artista, nome da música ou nome do arquivo:", placeholder="Ex: Tulio Mota...")
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
            else:
                st.error("Nenhuma música encontrada com esse nome.")
        else:
            st.info(f"💡 O banco de dados definitivo está operando perfeitamente diretamente via GitHub! Atualmente existem **{len(df_acervo)}** músicas catalogadas.")
    else:
        st.error("O banco de dados está vazio ou não pôde ser carregado.")

# --- ABA 2: CADASTRO MANUAL DE MÚSICAS ---
elif opcao == "📝 Cadastrar Novas Músicas":
    st.title("📝 Incluir Nova Música no Acervo Oficial")
    st.markdown("Use este formulário limpo para alimentar o banco de dados oficial diretamente pelo app.")
    
    df_acervo, sha_atual = carregar_banco_oficial_github()
    
    with st.form("form_cadastro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            artista = st.text_input("Nome do Artista:")
            musica = st.text_input("Nome da Música:")
            participacao = st.text_input("Participações (opcional):", placeholder="Ex: Jéssica Lourenço")
            compositores = st.text_input("Compositores (opcional):")
        with col2:
            ano = st.text_input("Ano de Lançamento (opcional):")
            formato = st.text_input("Formato/Álbum (opcional):", placeholder="Ex: Álbum Roteiro")
            origem = st.text_input("Origem (Pasta de destino no Sysrad):", placeholder="Ex: PRA COLOCAR NA PLANILHA")
            est_idioma = st.selectbox("Classificação de Estado / Estilo:", ["", "SC", "Nacional", "Internacional"])
            
        botao_salvar = st.form_submit_button("Salvar Música no Acervo 💾", type="primary")
        
        if botao_salvar:
            if not artista or not musica:
                st.error("⚠️ Os campos 'Artista' e 'Música' são obrigatórios!")
            else:
                # Gera o nome do arquivo padronizado automaticamente
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
                if salvar_banco_no_github(df_novo, f"Adicionado artista {artista} - {musica}", sha_atual):
                    st.success(f"🎉 Sucesso! '{nome_arq}' foi gravada com sucesso no Acervo Oficial!")
                    st.balloons()

# --- ABA 3: FORMATADOR EM LOTE ---
elif opcao == "💿 Formatador de Linhas":
    st.title("💿 Automatizador de Linhas do Acervo")
    st.markdown("Processa texto bruto em lote para você conferir a formatação antes de enviar para o banco de dados oficial.")
    
    df_acervo, sha_atual = carregar_banco_oficial_github()
    texto_bruto = st.text_area("Cole aqui as linhas brutas:", height=200, placeholder="M:\\...")
    
    if st.button("Processar Linhas 🚀", type="primary"):
        if texto_bruto:
            linhas = texto_bruto.split('\n')
            lista_novas = []
            for l in linhas:
                res = processar_linha_musica(l)
                if res:
                    res.pop("eh_sc") # Remove controle interno
                    lista_novas.append(res)
            
            if lista_novas:
                df_novas = pd.DataFrame(lista_novas)
                st.success(f"Foram identificadas {len(df_novas)} linhas válidas!")
                st.dataframe(df_novas, use_container_width=True)
                
                if st.button("Gravar Todas essas músicas no Acervo definitivo? 📥"):
                    df_final = pd.concat([df_acervo, df_novas], ignore_index=True)
                    df_final.drop_duplicates(subset=["Nome do Arquivo"], keep="first", inplace=True)
                    if salvar_banco_no_github(df_final, f"Adicionadas {len(df_novas)} musicas via formatador em lote", sha_atual):
                        st.success("Tudo gravado no repositório oficial com sucesso!")
                        st.balloons()
            else:
                st.warning("Nenhuma linha no padrão foi encontrada.")

# --- ABA 4: GERADOR DE SETLIST INSTAGRAM ---
elif opcao == "📸 Gerador de Setlist (Instagram)":
    st.title("📸 Formatador de Roteiro - Som da Ilha")
    banco_instagram, erro = carregar_banco_instagram(URL_INSTAGRAM_SHEETS)
    if erro: st.error(f"Erro ao carregar arrobas do Insta: {erro}")
    else:
        st.success("✅ Banco de Instagrams conectado!")
        texto_sysrad = st.text_area("Cole aqui o roteiro bruto do Sysrad:", height=200)
        if st.button("Formatar Roteiro ✨", type="primary"):
            if texto_sysrad:
                linhas = texto_sysrad.split('\n')
                resultado = [datetime.now().strftime("%d/%m/%Y"), ""]
                for linha in linhas:
                    linha = linha.strip()
                    if not linha or any(x in linha for x in ["Marcador", "Total:", "DescriçãoDuração"]): continue
                    linha = re.sub(r'\s*-\s*\(?part\.?[^)]+\)?\s*', ' ', linha, flags=re.IGNORECASE)
                    linha = re.sub(r'\s*\(?part\.?[^)]+\)?\s*', ' ', linha, flags=re.IGNORECASE)
                    if " - " in linha:
                        partes = linha.split(" - ", 1)
                        art_orig = partes[0].strip()
                        resto = partes[1]
                        mus_limpa = re.split(r'(\(comp|\(compa|Álbum|EP|Single|\d{4}|\d{2}:\d{2})', resto, flags=re.IGNORECASE)[0].strip().rstrip('-').strip()
                        insta = banco_instagram.get(art_orig.lower(), "")
                        resultado.append(f"{art_orig} - {mus_limpa} {insta}".strip())
                st.text_area("Pronto para as Redes Sociais:", value="\n".join(resultado), height=300)
                st.balloons()
