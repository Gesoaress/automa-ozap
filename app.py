import customtkinter as ctk
from tkinter import messagebox, filedialog
import pandas as pd
import re, time, urllib.parse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- Aparência ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

driver = None

# --- Normalização ---
def normalizar_contatos(lista):
    contatos_ok = []
    for num in lista:
        if not num:
            continue
        dig = re.sub(r"\D", "", str(num))  # só dígitos
        if not dig.startswith("55"):
            dig = "55" + dig
        contatos_ok.append(dig)
    return contatos_ok

# --- Importar contatos ---
def importar_contatos():
    caminho = filedialog.askopenfilename(
        title="Selecione arquivo de contatos",
        filetypes=[("Planilhas", "*.csv *.xlsx")]
    )
    if not caminho:
        return
    try:
        if caminho.lower().endswith(".csv"):
            df = pd.read_csv(caminho)
        else:
            df = pd.read_excel(caminho)

        if "numero" not in df.columns:
            messagebox.showerror("Erro", "O arquivo deve ter uma coluna chamada 'numero'.")
            return

        contatos = normalizar_contatos(df["numero"].dropna().astype(str).tolist())
        entry_contatos.delete("1.0", "end")
        entry_contatos.insert("1.0", "\n".join(contatos))
        messagebox.showinfo("Sucesso", f"{len(contatos)} contatos importados.")
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao importar: {e}")

# --- Iniciar navegador com perfil persistente ---
def iniciar_sessao():
    global driver
    if driver is not None:
        return driver

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument(r"--user-data-dir=C:\zap_session")  # sessão fica salva aqui

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://web.whatsapp.com")

    messagebox.showinfo(
        "Login",
        "Se for a primeira vez, escaneie o QR Code no navegador.\nDepois clique em OK para continuar."
    )
    return driver

# --- Disparar mensagens ---
def disparar():
    global driver
    contatos_texto = entry_contatos.get("1.0", "end").strip()
    mensagem = entry_mensagem.get("1.0", "end").strip()

    if not contatos_texto or not mensagem:
        messagebox.showwarning("Atenção", "Preencha os contatos e a mensagem!")
        return

    contatos = normalizar_contatos([c for c in contatos_texto.splitlines() if c.strip()])
    if not contatos:
        messagebox.showwarning("Atenção", "Nenhum número válido.")
        return

    intervalo = max(5, int(spin_intervalo.get()))
    driver = iniciar_sessao()

    btn_disparar.configure(state="disabled")
    log.insert("end", f"🟢 Iniciando disparo para {len(contatos)} número(s)...\n")
    log.see("end"); app.update()

    for i, numero in enumerate(contatos, start=1):
        try:
            texto = urllib.parse.quote(mensagem)
            link = f"https://web.whatsapp.com/send?phone={numero}&text={texto}"
            driver.get(link)

            # Espera a caixa de mensagem carregar
            caixa = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab]'))
            )
            time.sleep(2)  # dá tempo de carregar o texto

            # Clica no botão de enviar (aviãozinho)
            try:
                btn_enviar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Enviar"]'))
                )
                btn_enviar.click()
                log.insert("end", f"✅ ({i}/{len(contatos)}) Mensagem enviada para {numero}\n")
            except Exception as e:
                # fallback: usa ENTER se não achou botão
                caixa.send_keys("\n")
                log.insert("end", f"⚠️ ({i}/{len(contatos)}) Mensagem enviada (via ENTER) para {numero}\n")

        except Exception as e:
            log.insert("end", f"❌ ({i}/{len(contatos)}) Erro: {e}\n")

        log.see("end"); app.update()
        time.sleep(intervalo)

    log.insert("end", "🏁 Finalizado.\n"); log.see("end")
    btn_disparar.configure(state="normal")

# --- Layout ---
app = ctk.CTk()
app.title("📲 Disparador WhatsApp (Sessão Persistente)")
app.geometry("780x740")

ctk.CTkLabel(app, text="Números (um por linha):").pack(anchor="w", padx=12, pady=(14,4))
entry_contatos = ctk.CTkTextbox(app, height=170, width=720)
entry_contatos.pack(padx=12, pady=4)

frame_botoes = ctk.CTkFrame(app); frame_botoes.pack(pady=6)
ctk.CTkButton(frame_botoes, text="📂 Importar Excel/CSV", command=importar_contatos).grid(row=0, column=0, padx=8)

ctk.CTkLabel(app, text="Mensagem:").pack(anchor="w", padx=12, pady=(14,4))
entry_mensagem = ctk.CTkTextbox(app, height=170, width=720)
entry_mensagem.pack(padx=12, pady=4)

cfg = ctk.CTkFrame(app); cfg.pack(padx=12, pady=10, fill="x")
ctk.CTkLabel(cfg, text="⏱️ Intervalo entre envios (s):").grid(row=0, column=0, padx=8, pady=6, sticky="w")
spin_intervalo = ctk.CTkEntry(cfg, width=90); spin_intervalo.insert(0, "10")
spin_intervalo.grid(row=0, column=1, padx=8, pady=6)

btn_disparar = ctk.CTkButton(app, text="🚀 Disparar Mensagens", command=disparar)
btn_disparar.pack(pady=12)

ctk.CTkLabel(app, text="Log de envio:").pack(anchor="w", padx=12, pady=(12,4))
log = ctk.CTkTextbox(app, height=220, width=740)
log.pack(padx=12, pady=4)

app.mainloop()
