import streamlit as st
import pandas as pd
import re
from datetime import datetime

# Configuração da página do aplicativo (Definida apenas UMA vez no topo do site)
st.set_page_config(page_title="Painel de Formatação Udesc FM", page_icon="📻", layout="wide")

# 🔗 LINK DA PLANILHA DO GOOGLE DO SEU GERADOR DE SETLIST
URL_GOOGLE_SHEETS = "https://docs.google.com/spreadsheets/d/1zkPm3F9W8QbOBhKvdV7jFCYqH-U8Qbru5w5TDyAHQLw/edit?usp=sharing"

# --- MENU LATERAL DE NAVEGAÇÃO ---
st.sidebar.title("📻 Painel de Controle")
st.sidebar.markdown("Escolha a ferramenta que deseja usar agora:")
opcao = st.sidebar.radio(
    "Navegar para:",
    ["💿 Formatador de Acervo", "📸 Gerador de Setlist (Instagram)"]
)
st.sidebar.markdown("---")
st.sidebar.caption("Desenvolvido para otimizar a programação da Udesc FM 🎧")


# ==========================================
# FUNÇÕES DE SUPORTE DO GERADOR DE SETLIST
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
# FUNÇÕES DE SUPORTE DO FORMATADOR DE ACERVO
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


# ==========================================
# PAINEL DE EXECUÇÃO DAS PÁGINAS
# ==========================================

if opcao == "💿 Formatador de Acervo":
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
                        partes = line_split = linha.split(" - ", 1)
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
