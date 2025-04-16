# uroflussometro_analysis.py (versione PDF 2 pagine)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
from matplotlib.backends.backend_pdf import PdfPages

# === CONFIG ===
FILE_PATH = "data/sample_data.csv"  # CSV con separatore '|'
SOGLIA_FLUSSO = 0.5  # mL/s
PAUSA_MIN = 0.5      # secondi

# === LETTURA DATI ===
df = pd.read_csv(FILE_PATH, sep="|", header=None, names=["timestamp", "peso_g"])
df["tempo_s"] = (df["timestamp"] - df["timestamp"].iloc[0]) / 1000.0

# === CALCOLI FLUSSO ===
df["flusso_ml_s"] = np.gradient(df["peso_g"], df["tempo_s"])

volume_totale = df["peso_g"].max()
tempo_totale = df["tempo_s"].iloc[-1] - df["tempo_s"].iloc[0]

flusso_attivo = df["flusso_ml_s"] > SOGLIA_FLUSSO
tempo_inizio_flusso = df.loc[flusso_attivo, "tempo_s"].iloc[0]
tempo_fine_flusso = df.loc[flusso_attivo, "tempo_s"].iloc[-1]
tempo_di_flusso = tempo_fine_flusso - tempo_inizio_flusso
tempo_svuotamento = df["tempo_s"].iloc[-1] - df["tempo_s"].iloc[0]

q_max = df["flusso_ml_s"].max()
tempo_qmax = df.loc[df["flusso_ml_s"].idxmax(), "tempo_s"]
q_medio = volume_totale / tempo_di_flusso

# === INTERRUZIONI ===
df["interruzione"] = df["flusso_ml_s"] < SOGLIA_FLUSSO
pause = []
start = None
for i in range(len(df)):
    if df["interruzione"].iloc[i]:
        if start is None:
            start = df["tempo_s"].iloc[i]
    else:
        if start is not None:
            end = df["tempo_s"].iloc[i]
            if end - start >= PAUSA_MIN:
                pause.append((start, end))
            start = None

# === CURVA DI RIFERIMENTO SIMULATA ===
tempo_sim = np.linspace(0, 25, 500)
qmax_sim = 24
media_sim = 12
std_sim = 4
flusso_sim = qmax_sim * norm.pdf(tempo_sim, loc=media_sim, scale=std_sim)
flusso_sim = flusso_sim / flusso_sim.max() * qmax_sim
volume_sim = np.trapz(flusso_sim, tempo_sim)
qmedio_sim = volume_sim / (tempo_sim[-1] - tempo_sim[0])

# === PDF A 2 PAGINE ===
pdf_path = "uroflussogramma_due_pagine.pdf"
with PdfPages(pdf_path) as pdf:
    # PAGINA 1 - Landscape: uroflussogramma completo
    fig1, ax1 = plt.subplots(figsize=(11.69, 8.27))
    ax1.plot(df["tempo_s"], df["peso_g"], label="Volume vuotato", color="green", linewidth=2)
    ax1b = ax1.twinx()
    ax1b.plot(df["tempo_s"], df["flusso_ml_s"], label="Flusso urinario", color="blue", alpha=0.4)
    ax1b.axvline(tempo_qmax, color="red", linestyle="--", label="T@Qmax")
    ax1b.axhline(q_max, color="red", linestyle="--")
    ax1b.text(tempo_qmax, q_max + 1, f"Qmax = {q_max:.1f} mL/s", color="red", fontsize=8)
    ax1b.axhline(q_medio, color="cyan", linestyle="--")
    ax1b.text(df["tempo_s"].iloc[0], q_medio + 1, f"Qavg = {q_medio:.1f} mL/s", color="cyan", fontsize=8)
    ax1.axvspan(tempo_inizio_flusso, tempo_fine_flusso, color="yellow", alpha=0.2)
    for p_start, p_end in pause:
        ax1b.axvspan(p_start, p_end, color="gray", alpha=0.2)
    ax1.set_title("Uroflussogramma completo con analisi estesa")
    ax1.set_xlabel("Tempo (s)")
    ax1.set_ylabel("Volume (mL)", color="green")
    ax1b.set_ylabel("Flusso (mL/s)", color="blue")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1b.get_legend_handles_labels()
    unique = dict(zip(labels1 + labels2, lines1 + lines2))
    ax1b.legend(unique.values(), unique.keys(), loc="upper right")
    fig1.tight_layout()
    pdf.savefig(fig1)
    plt.close(fig1)

    # PAGINA 2 - Portrait: confronto + referto
    fig2 = plt.figure(figsize=(8.27, 11.69))
    gs = fig2.add_gridspec(2, 1, height_ratios=[1, 1])

    ax2 = fig2.add_subplot(gs[0])
    ax2.plot(df["tempo_s"], df["flusso_ml_s"], label="Flusso reale", color="blue")
    ax2.plot(tempo_sim, flusso_sim, label="Curva di riferimento (simulata)", color="green", linestyle="--")
    ax2.set_title("Confronto tra flusso reale e curva di riferimento")
    ax2.set_xlabel("Tempo (s)")
    ax2.set_ylabel("Flusso (mL/s)")
    ax2.legend()
    ax2.grid(True)

    ax3 = fig2.add_subplot(gs[1])
    ax3.axis("off")
    referto = f"""
Dati misurati (reale):
- Volume totale: {volume_totale:.1f} mL
- Durata complessiva: {tempo_totale:.1f} s
- Tempo di svuotamento: {tempo_svuotamento:.1f} s
- Tempo di flusso attivo: {tempo_di_flusso:.1f} s
- Qmax: {q_max:.1f} mL/s (a {tempo_qmax:.1f} s)
- Qmedio: {q_medio:.1f} mL/s
- Interruzioni del flusso: {len(pause)}

Interruzioni rilevate:
""" + "\n".join([f"  {i+1}. Da {start:.2f} s a {end:.2f} s" for i, (start, end) in enumerate(pause)]) + f"""

Curva di riferimento simulata:
- Qmax: {qmax_sim} mL/s
- Qmedio: {qmedio_sim:.1f} mL/s
- Volume: {volume_sim:.1f} mL
- Durata: {tempo_sim[-1] - tempo_sim[0]:.1f} s
"""
    ax3.text(0, 1, referto, va="top", fontsize=10, family="monospace")
    fig2.tight_layout()
    pdf.savefig(fig2)
    plt.close(fig2)

print(f"PDF salvato in: {pdf_path}")
