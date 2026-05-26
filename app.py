import streamlit as st
import pandas as pd
import re
from datetime import datetime

# ==========================================
# 📻 CONFIGURAÇÃO DO PAINEL (MANTIDA ORIGINAL)
# ==========================================
st.set_page_config(page_title="Painel de Formatação Udesc FM", page_icon="📻", layout="wide")

# 🔗 LINKS ATUALIZADOS DAS SUAS PLANILHAS REAIS (EXPORTAÇÃO DIRETA EM CSV)
URL_SOM_DA_ILHA_CSV = "https://docs.google.com/spreadsheets/d/1zw7RPhpuInL7JqSylB_zOMu5zaqO4KgnJ7sD2eoM6gs/export?format=csv&gid=0"
URL_TULIO_CSV = "https://docs.google.com/spreadsheets/d/16inPMqGCr50-MNJvwV1R4bykDgEGRwlxdbjWrlW6mfY/export?format=csv&gid=0"
URL_JESSICA_CSV = "https://docs.google.com/spreadsheets/d/1MQ7OcghWNTZwaYVBTmZlMojYTXZMOe5vT1px5VALpS0/export?format=csv&gid=0"

# O gerador do instagram usa o link do seu arquivo original (Som da Ilha)
URL_GOOGLE_SHEETS = "https://docs.google.com/spreadsheets/d/1zw7RPhpuInL7JqSylB_zOMu5zaqO4KgnJ7sD2eoM6gs/edit?usp=sharing"

# ==========================================
# 🔄 MECANISMO ROBUSTO DE INTEGRAÇÃO DO ACERVO (LEITURA MULTI-SEPARADOR)
# ==========================================
@st.cache_data(ttl=60)
def carregar_linhas_do_acervo_real():
    urls_bancos = [URL_SOM_DA_ILHA_CSV, URL_TULIO_CSV, URL_JESSICA_CSV]
    tabelas_carregadas = []
    
    for url in urls_bancos:
        try:
            # Tenta ler tentando identificar se a planilha usa vírgula ou ponto e vírgula
            df_temp = pd.read_csv(url, sep=None, engine='python', on_bad_lines='skip')
            if not df_temp.empty:
                # Padroniza cabeçalhos removendo espaços extras
                df_temp.columns = [str(c).strip() for c in df_temp.columns]
                tabelas_carregadas.append(df_temp)
        except Exception:
            continue
            
    if tabelas_carregadas:
        df_unificado = pd.concat(tabelas_carregadas, ignore_index=True)
        df_unificado.dropna(how='all', inplace=True)
        return df_unificado
    return pd.DataFrame()

# ==========================================
# FUNÇÕES DE SUPORTE DO GERADOR DE SETLIST (INTOCADAS)
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
# FUNÇÕES DE SUPORTE DO FORMATADOR DE ACERVO (INTOCADAS)
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
# ABA NEW 1: BUSCADOR INTEGRADO INTELIGENTE
# ==========================================
if opcao == "🔍 Buscar no Acervo":
    st.title("🔍 Busca Unificada no Acervo - Udesc FM")
    df_completo = carregar_linhas_do_acervo_real()
    
    if not df_completo.empty:
        st.write(f"📊 **Total de linhas lidas das planilhas em tempo real:** {len(df_completo)}")
        termo_busca = st.text_input("Digite o artista, música ou termo para pesquisar no acervo:")
        
        if termo_busca:
            termo_lower = termo_busca.lower()
            # Procura em todas as colunas dinamicamente
            mascara = pd.Series(False, index=df_completo.index)
            for col in df_completo.columns:
                mascara |= df_completo[col].astype(str).str.lower().str.contains(termo_lower, na=False)
            
            resultados = df_completo[mascara]
            if not resultados.empty:
                st.success(f"🎉 Encontradas {len(resultados)} correspondências!")
                st.dataframe(resultados, use_container_width=True)
            else:
                st.error("Nenhuma música encontrada com esse nome.")
    else:
        st.warning("⚠️ Não foi possível processar os dados das planilhas. Verifique o acesso público dos links.")

# ==========================================
# ABA NEW 2: VISUALIZAÇÃO COMPLETA DO ACERVO
# ==========================================
elif opcao == "📋 Ver Todo o Acervo":
    st.title("📋 Acervo Geral Cadastrado")
    df_completo = carregar_linhas_do_acervo_real()
    
    if not df_completo.empty:
        st.markdown(f"Exibindo abaixo a tabela unificada contendo todas as **{len(df_completo)}** entradas encontradas:")
        st.dataframe(df_completo, use_container_width=True)
    else:
        st.warning("Nenhum dado encontrado para exibição.")

# ==========================================
# ABA ORIGINAL 1: FORMATADOR (CÓDIGO ORIGINAL SEU)
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
                            "Música": res["Música"],
                            "Artista": res["Artista"],
                            "Compositores": res["Compositores"],
                            "Formato": res["Formato"],
                            "Ano": res["Ano"],
                            "Origem": res["Origem"],
                            "Gênero": res["Gênero"],
                            "Gênero Relacionado": res["Gênero Relacionado"],
                            "Est": "SC",
                            "Classificação": res["Classificação"],
                            "Andamento": res["Andamento"],
                            "Data Cadastro": res["Data Cadastro"],
                            "Participações": res["Participações"],
                            "Nome do Arquivo": res["Nome do Arquivo"]
                        }
                        lista_sc.append(dados_sc)
                    else:
                        dados_geral = {
                            "Música": res["Música"],
                            "Artista": res["Artista"],
                            "Compositores": res["Compositores"],
                            "Formato": res["Formato"],
                            "Ano": res["Ano"],
                            "Origem": res["Origem"],
                            "Gênero": res["Gênero"],
                            "Gênero Relacionado": res["Gênero Relacionado"],
                            "Idioma": "",
                            "Classificação": res["Classificação"],
                            "Andamento": res["Andamento"],
                            "Data Cadastro": res["Data Cadastro"],
                            "Participações": res["Participações"],
                            "Nome do Arquivo": res["Nome do Arquivo"]
                        }
                        lista_geral.append(dados_geral)
            
            if lista_geral:
                df_geral = pd.DataFrame(lista_geral)
                df_geral.drop_duplicates(subset=["Nome do Arquivo"], keep="first", inplace=True)
                st.success(f"🎉 {len(df_geral)} músicas prontas para o ACERVO GERAL!")
                st.markdown("👉 *Clique na tabela abaixo, use **Ctrl+A** e **Ctrl+C**, e cole na sua planilha do Acervo Geral.*")
                st.dataframe(df_geral, use_container_width=True)
                
            if lista_sc:
                df_sc = pd.DataFrame(lista_sc)
                df_sc.drop_duplicates(subset=["Nome do Arquivo"], keep="first", inplace=True)
                st.warning(f"🏝️ {len(df_sc)} músicas de Santa Catarina identificadas para o SOM DA ILHA!")
                st.markdown("👉 *Clique na tabela abaixo, use **Ctrl+A** e **Ctrl+C**, e cole na sua planilha do Som da Ilha.*")
                st.dataframe(df_sc, use_container_width=True)
                
            if lista_geral or lista_sc:
                st.balloons()
            else:
                st.warning("Nenhuma linha válida encontrada no padrão.")
        else:
            st.warning("Cole os dados antes de processar.")

# ==========================================
# ABA ORIGINAL 2: INSTAGRAM (CÓDIGO ORIGINAL SEU)
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
                    
                    # --- REMOÇÃO DE PARTICIPAÇÕES ---
                    linha = re.sub(r'\s*-\s*\(?part\.?[^)]+\)?\s*', ' ', linha, flags=re.IGNORECASE)
                    linha = re.sub(r'\s*\(?part\.?[^)]+\)?\s*', ' ', linha, flags=re.IGNORECASE)
                    
                    if " - " in linha:
                        partes = linha.split(" - ", 1)
                        artista_original = partes[0].strip()
                        artista_busca = artista_original.lower()
                        resto = partes[1]
                        
                        # --- LÓGICA DE LIMPEZA DA MÚSICA ---
                        padrao_corte = r'(\(comp|\(compa|Álbum|EP|Single|\d{4}|\d{2}:\d{2})'
                        musica_limpa = re.split(padrao_corte, resto, flags=re.IGNORECASE)[0].strip()
                        musica_limpa = musica_limpa.rstrip('-').strip()
                        
                        # Busca o arroba na planilha do Sheets
                        instagram = banco_instagram.get(artista_busca, "")
                        
                        linha_final = f"{artista_original} - {musica_limpa} {instagram}".strip()
                        resultado.append(linha_final)
                
                texto_formatado = "\n".join(resultado)
                
                st.subheader("📋 Roteiro Pronto para as Redes Sociais:")
                st.text_area("Selecione tudo e copie:", value=texto_formatado, height=350)
                st.balloons()
            else:
                st.warning("Por favor, cole o roteiro do Sysrad antes de formatar.")
