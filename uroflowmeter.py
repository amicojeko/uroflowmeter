# uroflussometro_analysis.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# === CONFIG ===
FILE_PATH = "dati_uroflussometro.csv"  # CSV con separatore '|'
SOGLIA_FLUSSO = 0.5  # mL/s
PAUSA_MIN = 0.5      # secondi

# === LETTURA DATI ===
df = pd.read_csv(FILE_PATH, sep="|", header=None, names=["timestamp", "peso_g"])
df["tempo_s"] = (df["timestamp"] - df["timestamp"].iloc[0]) / 1000.0

# === CALCOLI ===
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

# === RILEVAZIONE INTERRUZIONI ===
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

# === GRAFICO ===
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(df["tempo_s"], df["peso_g"], label="Volume vuotato", color="green", linewidth=2)

ax2 = ax.twinx()
ax2.plot(df["tempo_s"], df["flusso_ml_s"], label="Flusso urinario", color="blue", alpha=0.4)

ax2.axvline(tempo_qmax, color="red", linestyle="--", label="T@Qmax")
ax2.axhline(q_max, color="red", linestyle="--")
ax2.text(tempo_qmax, q_max + 1, f"Qmax = {q_max:.1f} mL/s", color="red", fontsize=9)

ax2.axhline(q_medio, color="cyan", linestyle="--")
ax2.text(df["tempo_s"].iloc[0], q_medio + 1, f"Qavg = {q_medio:.1f} mL/s", color="cyan", fontsize=9)

ax.axvspan(tempo_inizio_flusso, tempo_fine_flusso, color="yellow", alpha=0.2, label="Tempo di flusso")
ax.text((tempo_inizio_flusso + tempo_fine_flusso) / 2, volume_totale * 0.1,
        f"Tempo di flusso = {tempo_di_flusso:.1f} s", ha='center', fontsize=9)

for p_start, p_end in pause:
    ax2.axvspan(p_start, p_end, color="gray", alpha=0.2, label="Interruzione del flusso")

ax.set_xlabel("Tempo (s)")
ax.set_ylabel("Volume (mL)", color="green")
ax2.set_ylabel("Flusso (mL/s)", color="blue")
plt.title("Uroflussogramma completo con analisi estesa")

lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
unique = dict(zip(labels1 + labels2, lines1 + lines2))
ax2.legend(unique.values(), unique.keys(), loc="upper left")

plt.tight_layout()
plt.show()

# === RISULTATI ===
print("\n--- RISULTATI ---")
print(f"Volume totale (mL): {volume_totale:.2f}")
print(f"Durata complessiva (s): {tempo_totale:.2f}")
print(f"Tempo di flusso (s): {tempo_di_flusso:.2f}")
print(f"Tempo di svuotamento (s): {tempo_svuotamento:.2f}")
print(f"Qmax (mL/s): {q_max:.2f} a {tempo_qmax:.2f} s")
print(f"Qmedio (mL/s): {q_medio:.2f}")
print(f"Numero di interruzioni: {len(pause)}")
for i, (start, end) in enumerate(pause, 1):
    print(f"  Interruzione {i}: da {start:.2f}s a {end:.2f}s")
