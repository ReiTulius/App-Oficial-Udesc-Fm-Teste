import streamlit as st
import pandas as pd
import re
from datetime import datetime

# ==========================================
# 📻 CONFIGURAÇÃO DO PAINEL (MANTIDA ORIGINAL)
# ==========================================
st.set_page_config(page_title="Painel de Formatação Udesc FM", page_icon="📻", layout="wide")

# 📊 LINKS DAS PLANILHAS (Atualizados para o formato correto de leitura do Google)
URL_SOM_DA_ILHA = "https://docs.google.com/spreadsheets/d/1zw7RPhpuInL7JqSylB_zOMu5zaqO4KgnJ7sD2eoM6gs/export?format=csv"
URL_TULIO = "https://docs.google.com/spreadsheets/d/16inPMqGCr50-MNJvwV1R4bykDgEGRwlxdbjWrlW6mfY/export?format=csv"
URL_JESSICA = "https://docs.google.com/spreadsheets/d/1MQ7OcghWNTZwaYVBTmZlMojYTXZMOe5vT1px5VALpS0/export?format=csv"

# Link usado pelo seu gerador de setlist original do Instagram
URL_GOOGLE_SHEETS = "https://docs.google.com/spreadsheets/d/1zkPm3F9W8QbOBhKvdV7jFCYqH-U8Qbru5w5TDyAHQLw/edit?usp=sharing"

# ==========================================
# 🔄 FUNÇÃO PARA JUNTAR AS 3 PLANILHAS DE VERDADE
# ==========================================
@st.cache_data(ttl=60)
def carregar_todos_os_acervos():
    lista_dfs = []
    
    # Tenta ler a planilha 1 (Som da Ilha)
    try:
        df1 = pd.read_csv(URL_SOM_DA_ILHA, sep=None, engine='python', on_bad_lines='skip')
        if not df1.empty:
            lista_dfs.append(df1)
    except: pass

    # Tenta ler a planilha 2 (Túlio)
    try:
        df2 = pd.read_csv(URL_TULIO, sep=None, engine='python', on_bad_lines='skip')
        if not df2.empty:
            lista_dfs.append(df2)
    except: pass

    # Tenta ler a planilha 3 (Jéssica)
    try:
        df3 = pd.read_csv(URL_JESSICA, sep=None, engine='python', on_bad_lines='skip')
        if not df3.empty:
            lista_dfs.append(df3)
    except: pass

    if lista_dfs:
        # Junta todas as planilhas uma embaixo da outra
        df_unificado = pd.concat(lista_dfs, ignore_index=True)
        # Limpa linhas totalmente vazias
        df_unificado.dropna(how='all', inplace=True)
        # Padroniza os nomes das colunas tirando espaços invisíveis
        df_unificado.columns = [str(c).strip() for c in df_unificado.columns]
        return df_unificado
    return pd.DataFrame()


# ==========================================
# FUNÇÕES DE SUPORTE DO GERADOR DE SETLIST (CONFORME SEU CÓDIGO)
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
# FUNÇÕES DE SUPORTE DO FORMATADOR DE ACERVO (CONFORME SEU CÓDIGO)
# ==========================================
def processar_linha_musica(linha_bruta):
    linha_original = linha_bruta.strip().replace('"', '')
    if not linha_original:
        return None
        
    linha_limpa_fim = linha_original.lower()
    if linha_limpa_fim.endswith(".mp3"):
        linha_limpa_fim = linha_limpa_fim[:-4].strip()
        
    eh_sc = False
    if linha_limpa_fim.endswith("- sc") or linha_limpa_fim.endswith("-sc"):
        eh_sc = True
        
    if "\\" in linha_original:
        linha_trabalho = linha_original.split("\\")[-1]
    else:
        linha_trabalho = linha_original
        
    if linha_trabalho.lower().endswith(".mp3"):
        linha_trabalho = linha_trabalho[:-4]
        
    if eh_sc:
        linha_trabalho = re.sub(r'\s*-\s*sc\s*$', '', linha_trabalho, flags=re.IGNORECASE).strip()
        
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
    
    if len(partes) < 2:
        return None
        
    artista = partes[0]
    
    indice_atual = 1
    if indice_atual < len(partes) and ("part." in partes[indice_atual].lower() or "part " in partes[indice_atual].lower()):
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

    part_str = f" - (part. {participacao})" if participacao else ""
    comp_str = f" (comp. {compositores})" if compositores else ""
    formato_str = f" - {formato}" if formato else ""
    ano_str = f" - {ano}" if ano else ""
    sc_str = " - SC" if eh_sc else ""
    
    nome_arquivo_formatado = f"{artista}{part_str} - {musica}{comp_str}{formato_str}{ano_str}{sc_str}"
    nome_arquivo_formatado = re.sub(r'\s+', ' ', nome_arquivo_formatado).strip()

    return {
        "eh_sc": eh_sc,
        "Música": musica,
        "Artista": artista,
        "Compositores": compositores,
        "Formato": formato,
        "Ano": ano,
        "Origem": "",
        "Gênero": "",
        "Gênero Relacionado": "",
        "Est/Idioma": "SC" if eh_sc else "",
        "Classificação": "",
        "Andamento": "",
        "Data Cadastro": datetime.now().strftime("%d/%m/%Y"),
        "Participações": participacao,
        "Nome do Arquivo": nome_arquivo_formatado
    }


# --- MENU LATERAL DE NAVEGAÇÃO ---
st.sidebar.title("📻 Painel de Controle")
opcao = st.sidebar.radio(
    "Navegar para:",
    ["🔍 Buscar no Acervo", "📋 Ver Todo o Acervo", "💿 Formatador de Acervo", "📸 Gerador de Setlist (Instagram)"]
)
st.sidebar.markdown("---")
st.sidebar.caption("Desenvolvido para otimizar a programação da Udesc FM 🎧")


# ==========================================
# 🔍 ABA: BUSCAR NO ACERVO (TODAS AS PLANILHAS)
# ==========================================
if opcao == "🔍 Buscar no Acervo":
    st.title("🔍 Busca Integrada no Acervo")
    df_total = carregar_todos_os_acervos()
    
    if not df_total.empty:
        st.write(f"📊 **Total de músicas integradas (Som da Ilha + Túlio + Jéssica):** {len(df_total)}")
        termo = st.text_input("Digite o artista, nome da música ou arquivo para pesquisar:")
        
        if termo:
            termo_lower = termo.lower()
            mascara = pd.Series(False, index=df_total.index)
            for col in df_total.columns:
                mascara |= df_total[col].astype(str).str.lower().str.contains(termo_lower, na=False)
            
            resultados = df_total[mascara]
            if not resultados.empty:
                st.success(f"🎉 Encontradas {len(resultados)} correspondências!")
                st.dataframe(resultados, use_container_width=True)
            else:
                st.error("Nenhuma música encontrada com este termo.")
    else:
        st.warning("⚠️ Não foi possível carregar os dados das planilhas do Google.")

# ==========================================
# 📋 ABA: VER TODO O ACERVO (TODAS AS PLANILHAS)
# ==========================================
elif opcao == "📋 Ver Todo o Acervo":
    st.title("📋 Visualização Completa do Acervo Unificado")
    df_total = carregar_todos_os_acervos()
    
    if not df_total.empty:
        st.write(f"Exibindo a lista combinada de todas as **{len(df_total)}** linhas encontradas nas suas 3 planilhas:")
        st.dataframe(df_total, use_container_width=True)
    else:
        st.warning("Nenhum dado disponível para exibir.")

# ==========================================
# 💿 ABA: FORMATADOR DE ACERVO + AGORA COM INTERAÇÃO DE SALVAR!
# ==========================================
elif opcao == "💿 Formatador de Acervo":
    st.title("💿 Automatizador de Acervo Para Udesc FM")
    st.markdown("Insira a lista de músicas para limpar, formatar e separar para o Acervo Geral ou Som da Ilha (SC).")

    texto_bruto = st.text_area("Cole aqui as linhas brutas das músicas baixadas (pode misturar normais e com SC):", height=250, placeholder="M:\\...")

    if st.button("Processar e Organizar Acervos 🚀", type="primary"):
        if texto_bruto:
            linhas = texto_bruto.split('\n')
            lista_geral = []
            lista_sc = []
            
            for linha in linhas:
                res = processar_linha_musica(linha)
                if res:
                    eh_sc = res.pop("eh_sc")
                    
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
            
            # Salva na memória temporária para que você veja o resultado na tela
            if lista_geral:
                df_g = pd.DataFrame(lista_geral)
                df_g.drop_duplicates(subset=["Nome do Arquivo"], keep="first", inplace=True)
                st.session_state["lote_geral_atual"] = df_g
                
            if lista_sc:
                df_s = pd.DataFrame(lista_sc)
                df_s.drop_duplicates(subset=["Nome do Arquivo"], keep="first", inplace=True)
                st.session_state["lote_sc_atual"] = df_s
                
            st.balloons()

    # Exibição dos resultados formatados (Mantendo o comportamento visual idêntico ao seu)
    if "lote_geral_atual" in st.session_state:
        df_g = st.session_state["lote_geral_atual"]
        st.success(f"🎉 {len(df_g)} músicas prontas para o ACERVO GERAL!")
        st.markdown("👉 *Clique na tabela abaixo, use **Ctrl+A** e **Ctrl+C**, e cole na sua planilha do Acervo Geral.*")
        st.dataframe(df_g, use_container_width=True)
        
    if "lote_sc_atual" in st.session_state:
        df_s = st.session_state["lote_sc_atual"]
        st.warning(f"🏝️ {len(df_s)} músicas de Santa Catarina identificadas para o SOM DA ILHA!")
        st.markdown("👉 *Clique na tabela abaixo, use **Ctrl+A** e **Ctrl+C**, e cole na sua planilha do Som da Ilha.*")
        st.dataframe(df_s, use_container_width=True)

# ==========================================
# 📸 ABA: GERADOR DE SETLIST INSTAGRAM (CONFORME SEU CÓDIGO)
# ==========================================
elif opcao == "📸 Gerador de Setlist (Instagram)":
    st.title("📸 Formatador de Roteiro - Som da Ilha")
    st.markdown("Instruções: Cole o texto do Sysrad e clique em formatar. A lista de Instagrams é atualizada automaticamente via Google Drive.")

    banco_instagram, erro = carregar_banco_instagram(URL_GOOGLE_SHEETS)
    
    if erro:
        st.error(erro)
    else:
        st.success("✅ Banco de dados dos artistas conectado e atualizado em tempo real!")

        texto_bruto_sysrad = st.text_area("1. Cole aqui o roteiro bruto copiado do Sysrad:", height=250)

        if st.button("Formatar Roteiro ✨", type="primary"):
            if texto_bruto_sysrad:
                linhas = texto_bruto_sysrad.split('\n')
                resultado = [datetime.now().strftime("%d/%m/%Y"), ""] 
                
                for linha in linhas:
                    linha = linha.strip()
                    if not linha or "Marcador" in linha or "Total:" in linha or "DescriçãoDuração" in linha:
                        continue
                    
                    linha = re.sub(r'\s*-\s*\(?part\.?[^)]+\)?\s*', ' ', linha, flags=re.IGNORECASE)
                    linha = re.sub(r'\s*\(?part\.?[^)]+\)?\s*', ' ', linha, flags=re.IGNORECASE)
                    
                    if " - " in linha:
                        partes = linha.split(" - ", 1)
                        artista_original = partes[0].strip()
                        artista_busca = artista_original.lower()
                        resto = partes[1]
                        
                        padrao_corte = r'(\(comp|\(compa|Álbum|EP|Single|\d{4}|\d{2}:\d{2})'
                        musica_limpa = re.split(padrao_corte, resto, flags=re.IGNORECASE)[0].strip()
                        musica_limpa = musica_limpa.rstrip('-').strip()
                        
                        instagram = banco_instagram.get(artista_busca, "")
                        
                        linha_final = f"{artista_original} - {musica_limpa} {instagram}".strip()
                        resultado.append(linha_final)
                
                texto_formatado = "\n".join(resultado)
                
                st.subheader("📋 Roteiro Pronto para as Redes Sociais:")
                st.text_area("Selecione tudo e copie:", value=texto_formatado, height=350)
                st.balloons()
            else:
                st.warning("Por favor, cole o roteiro do Sysrad antes de formatar.")
