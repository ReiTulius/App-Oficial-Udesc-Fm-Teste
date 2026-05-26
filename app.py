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
# 📊 LINKS DAS PLANILHAS GOOGLE (DECLARAÇÃO INICIAL)
# ==========================================
URL_CARGA_SOM_DA_ILHA = "https://docs.google.com/spreadsheets/d/1zw7RPhpuInL7JqSylB_zOMu5zaqO4KgnJ7sD2eoM6gs/edit?usp=drive_link"
URL_CARGA_TULIO = "https://docs.google.com/spreadsheets/d/16inPMqGCr50-MNJvwV1R4bykDgEGRwlxdbjWrlW6mfY/edit?usp=drive_link"
URL_CARGA_JESSICA = "https://docs.google.com/spreadsheets/d/1MQ7OcghWNTZwaYVBTmZlMojYTXZMOe5vT1px5VALpS0/edit?usp=drive_link"

URL_INSTAGRAM_SHEETS = URL_CARGA_SOM_DA_ILHA

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
# 💾 REGRAS DE LEITURA E ESCRITA
# ==========================================
def converter_link_google(url):
    if "docs.google.com/spreadsheets" in url:
        try:
            id_planilha = url.split("/d/")[1].split("/")[0]
            return f"
