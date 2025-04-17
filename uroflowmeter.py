import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from scipy.ndimage import gaussian_filter1d


def load_data(file_path):
    # Carica i dati e filtra eventuali valori di peso negativi
    df = pd.read_csv(file_path, sep="|", header=None, names=["timestamp", "weight_g"])
    df = df[df["weight_g"] >= 0].reset_index(drop=True)
    # Calcola il tempo in secondi dal primo campione valido
    df["time_s"] = (df["timestamp"] - df["timestamp"].iloc[0]) / 1000.0
    # Calcola il flusso come derivata del volume nel tempo
    df["flow_ml_s"] = np.gradient(df["weight_g"], df["time_s"])
    return df


def analyze_flow(df, flow_threshold=0.4, min_pause_duration=0.5, smoothing_sigma=0.4):
    # Applica smoothing sul flusso per ridurre rumore
    df["flow_smoothed"] = gaussian_filter1d(df["flow_ml_s"], sigma=smoothing_sigma)

    # Definisce l'intervallo di flusso valido (superiore alla soglia)
    valid_idx = df.index[df["flow_smoothed"] > flow_threshold]
    if valid_idx.empty:
        raise ValueError("Nessun intervallo di flusso valido trovato")
    start_idx, end_idx = valid_idx[0], valid_idx[-1]
    df_valid = df.loc[start_idx:end_idx].reset_index(drop=True)
    # Riporta il tempo relativo al nuovo inizio
    df_valid["time_s"] = df_valid["time_s"] - df_valid["time_s"].iloc[0]

    # Identifica le interruzioni (> min_pause_duration)
    df_valid["interruption"] = df_valid["flow_smoothed"] < flow_threshold
    pauses = []
    pause_start = None
    for i, row in df_valid.iterrows():
        if row["interruption"]:
            if pause_start is None:
                pause_start = row["time_s"]
        else:
            if pause_start is not None:
                pause_end = row["time_s"]
                if pause_end - pause_start >= min_pause_duration:
                    pauses.append((pause_start, pause_end))
                pause_start = None

    # Parametri principali
    total_volume = df_valid["weight_g"].iloc[-1] - df_valid["weight_g"].iloc[0]
    total_duration = df_valid["time_s"].iloc[-1]
    emptying_time = total_duration
    active_flow_time = df_valid[~df_valid["interruption"]].shape[0] * (total_duration / len(df_valid))

    # Massimo e tempo a Qmax basati sul flusso smussato
    q_max = df_valid["flow_smoothed"].max()
    time_qmax = df_valid.loc[df_valid["flow_smoothed"].idxmax(), "time_s"]
    q_avg = total_volume / total_duration if total_duration > 0 else 0

    metrics = {
        "total_volume": total_volume,
        "total_duration": total_duration,
        "emptying_time": emptying_time,
        "active_flow_time": active_flow_time,
        "q_max": q_max,
        "time_qmax": time_qmax,
        "q_avg": q_avg,
        "pauses": pauses
    }

    return df_valid, metrics


def generate_pdf(df, metrics, pdf_path="uroflow_report_two_pages.pdf"):
    with PdfPages(pdf_path) as pdf:
        # Primo grafico: volume vs tempo e flusso smussato
        fig1, ax1 = plt.subplots(figsize=(11.69, 8.27))
        ax1.plot(df["time_s"], df["weight_g"], label="Voided volume", color="green", linewidth=2)
        ax1b = ax1.twinx()
        ax1b.plot(df["time_s"], df["flow_smoothed"], label="Flow smoothed", color="blue", alpha=0.6)
        # Linea e etichetta per Qmax
        ax1b.axvline(metrics["time_qmax"], color="red", linestyle="--", label="T@Qmax")
        ax1b.axhline(metrics["q_max"], color="red", linestyle="--")
        ax1b.text(metrics["time_qmax"], metrics["q_max"] * 0.9,
                  f"Qmax = {metrics['q_max']:.1f} mL/s", color="red", fontsize=10)
        # Etichetta Qavg
        ax1b.axhline(metrics["q_avg"], color="magenta", linestyle="--")
        ax1b.text(df["time_s"].min(), metrics["q_avg"] * 0.9,
                  f"Qavg = {metrics['q_avg']:.1f} mL/s", color="magenta", fontsize=10)
        # Evidenziazione pause
        for start, end in metrics["pauses"]:
            ax1b.axvspan(start, end, color="gray", alpha=0.2)
        ax1.set_title("Uroflowgram")
        ax1.set_xlabel("Time (s)")
        ax1.set_ylabel("Volume (mL)", color="green")
        ax1b.set_ylabel("Flow (mL/s)", color="blue")
        handles1, labels1 = ax1.get_legend_handles_labels()
        handles2, labels2 = ax1b.get_legend_handles_labels()
        ax1b.legend(handles1 + handles2, labels1 + labels2, loc="lower left")
        fig1.tight_layout()
        pdf.savefig(fig1)

        # Seconda pagina: report testuale
        fig2 = plt.figure(figsize=(8.27, 11.69))
        ax2 = fig2.add_subplot(111)
        ax2.axis('off')
        report_lines = [
            f"Total voided volume: {metrics['total_volume']:.1f} mL",
            f"Total duration: {metrics['total_duration']:.1f} s",
            f"Emptying time: {metrics['emptying_time']:.1f} s",
            f"Active flow time: {metrics['active_flow_time']:.1f} s",
            f"Qmax (max flow): {metrics['q_max']:.1f} mL/s at {metrics['time_qmax']:.1f} s",
            f"Qavg (avg flow): {metrics['q_avg']:.1f} mL/s",
            f"Interruptions: {len(metrics['pauses'])}"
        ]
        report_text = "Measured parameters:\n" + "\n".join(["- " + line for line in report_lines]) + "\n\nDetected interruptions:" + "\n" + "\n".join([
            f"  {i+1}. From {start:.2f}s to {end:.2f}s (duration {end-start:.2f}s)"
            for i, (start, end) in enumerate(metrics['pauses'])
        ])
        ax2.text(0, 1, report_text, va='top', fontsize=10, family='monospace')
        fig2.tight_layout()
        pdf.savefig(fig2)
        plt.close('all')

    print(f"PDF saved to: {pdf_path}")

if __name__ == '__main__':
    FILE_PATH = 'data/sample_data.csv'
    df = load_data(FILE_PATH)
    df_valid, metrics = analyze_flow(df)
    generate_pdf(df_valid, metrics)
