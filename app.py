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
    except:
        pass

# ==========================================
# 🔄 LEITOR INTEGRADO DAS PLANILHAS
# ==========================================
@st.cache_data(ttl=2)
def carregar_planilha_especifica(nome_acervo):
    url_map = {
        "Som da Ilha": URL_SOM_DA_ILHA_PRO,
        "Túlio": URL_TULIO_PRO,
        "Jéssica": URL_JESSICA_PRO
    }
    url = url_map.get(nome_ac
