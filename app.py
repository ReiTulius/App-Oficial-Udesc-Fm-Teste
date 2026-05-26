import streamlit as st
import pandas as pd
import re
from datetime import datetime

# Configuração da página do aplicativo
st.set_page_config(page_title="Painel Udesc FM - Mídias", page_icon="📻", layout="wide")

# ==========================================
# 📊 LINKS DIRETOS PARA EXPORTAÇÃO (ABAS CORRETAS)
# ==========================================
# Mudamos o final para gid=0 para garantir que pegue a aba principal de cada uma
URL_SOM_DA_ILHA = "https://docs.google.com/spreadsheets/d/1zw7RPhpuInL7JqSylB_zOMu5zaqO4KgnJ7sD2eoM6gs/export?format=csv&gid=0"
URL_TULIO = "https://docs.google.com/spreadsheets/d/16inPMqGCr50-MNJvwV1R4bykDgEGRwlxdbjWrlW6mfY/export?format=csv&gid=0"
URL_JESSICA = "https://docs.google.com/spreadsheets/d/1MQ7OcghWNTZwaYVBTmZlMojYTXZMOe5vT1px5VALpS0/export?format=csv&gid=0"

# ==========================================
# 🔄 CARREGAMENTO EM TEMPO REAL (SEM DEPENDER DO GITHUB PARA LER)
# ==========================================
@st.cache_data(ttl=30)  # Atualiza a cada 30 segundos se houver mudanças nas planilhas
def carregar_tudo_do_google():
    dfs = []
    # Planilha 1: Som da Ilha
    try:
        df1 = pd.read_csv(URL_SOM_DA_ILHA)
        if not df1.empty: dfs.append(df1)
    except: pass
    
    # Planilha 2: Túlio
    try:
        df2 = pd.read_csv(URL_TULIO)
        if not df2.empty: dfs.append(df2)
    except: pass
    
    # Planilha 3: Jéssica
    try:
        df3 = pd.read_csv(URL_JESSICA)
        if not df3.empty: dfs.append(df3)
    except: pass

    if dfs:
        df_total = pd.concat(dfs, ignore_index=True)
        # Remove linhas totalmente em branco
        df_total.dropna(how='all', inplace=True)
        return df_total
    return pd.DataFrame()

@st.cache_data(ttl=300)
def carregar_banco_instagram():
    try:
        df = pd.read_csv(URL_SOM_DA_ILHA)
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
        return banco
    except:
        return {}

# ==========================================
# 💿 LÓGICA ORIGINAL DO FORMATADOR (IDENTICA À VERSÃO INICIAL)
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
        "Origem": "", "Gênero": "", "Gênero Relacionado": "", "Idioma": "", "Classifi.": "",
        "Andan.": "", "Data Cadastro": datetime.now().strftime("%d/%m/%Y"), "Participações": participacao, "Nome do Arquivo": nome_final
    }

# --- MENU LATERAL ---
st.sidebar.title("📻 Painel de Controle")
opcao = st.sidebar.radio(
    "Navegar para:",
    ["🔍 Buscar no Acervo", "📋 Ver Todo o Acervo", "💿 Formatador de Linhas", "📸 Gerador de Setlist (Instagram)"]
)

# --- ABA 1: BUSCA NO ACERVO ---
if opcao == "🔍 Buscar no Acervo":
    st.title("🔍 Busca Instantânea no Acervo")
    df_acervo = carregar_tudo_do_google()
    
    if not df_acervo.empty:
        st.write(f"📊 **Total de músicas integradas em tempo real:** {len(df_acervo)}")
        termo = st.text_input("Digite o artista, nome da música ou arquivo:")
        
        if termo:
            termo_lower = termo.lower()
            # Varre todas as colunas existentes atrás do termo digitado
            mascara = pd.Series(False, index=df_acervo.index)
            for col in df_acervo.columns:
                mascara |= df_acervo[col].astype(str).str.lower().str.contains(termo_lower, na=False)
            
            resultados = df_acervo[mascara]
            if not resultados.empty:
                st.success(f"🎉 Encontradas {len(resultados)} correspondências!")
                st.dataframe(resultados, use_container_width=True)
            else:
                st.error("Nenhuma música encontrada com esse termo. Verifique a grafia.")
    else:
        st.warning("⚠️ Nenhuma informação foi retornada das planilhas do Google. Verifique as permissões de compartilhamento.")

# --- ABA 2: VER TODO O ACERVO (NOVO PEDIDO!) ---
elif opcao == "📋 Ver Todo o Acervo":
    st.title("📋 Todas as Músicas Cadastradas")
    df_acervo = carregar_tudo_do_google()
    
    if not df_acervo.empty:
        st.write(f"Exibindo a lista completa contendo as **{len(df_acervo)}** linhas unificadas das planilhas:")
        # Exibe a tabela completa estruturada
        st.dataframe(df_acervo, use_container_width=True)
    else:
        st.warning("Não há dados para exibir.")

# --- ABA 3: FORMATADOR EM LOTE (VERSÃO QUE DEU CERTO) ---
elif opcao == "💿 Formatador de Linhas":
    st.title("💿 Formatador de Linhas (Original)")
    texto_bruto = st.text_area("Cole aqui as suas linhas brutas do Sysrad:", height=250)
    
    if st.button("Processar Linhas 🚀", type="primary"):
        if texto_bruto:
            linhas = texto_bruto.split('\n')
            lista_novas = []
            for l in linhas:
                res = processar_linha_musica(l)
                if res: lista_novas.append(res)
            if lista_novas:
                df_novas = pd.DataFrame(lista_novas)
                st.success(f"Identificadas {len(df_novas)} linhas com sucesso!")
                st.dataframe(df_novas, use_container_width=True)
            else:
                st.warning("Nenhuma linha válida pôde ser convertida.")

# --- ABA 4: INSTAGRAM (VERSÃO QUE DEU CERTO) ---
elif opcao == "📸 Gerador de Setlist (Instagram)":
    st.title("📸 Gerador de Setlist - Redes Sociais")
    banco_instagram = carregar_banco_instagram()
    texto_sysrad = st.text_area("Cole aqui o roteiro bruto extraído do Sysrad:", height=250)
    
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
            st.text_area("Pronto para copiar e colar no Instagram:", value="\n".join(resultado), height=300)
