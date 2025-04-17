# uroflowmeter.py (modularized version)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from scipy.ndimage import gaussian_filter1d

def load_data(file_path):
    df = pd.read_csv(file_path, sep="|", header=None, names=["timestamp", "weight_g"])
    df["time_s"] = (df["timestamp"] - df["timestamp"].iloc[0]) / 1000.0
    df["flow_ml_s"] = np.gradient(df["weight_g"], df["time_s"])
    return df

def analyze_flow(df, flow_threshold=0.5, min_pause_duration=0.5, smoothing_sigma=0.35):
    df["flow_ml_s"] = gaussian_filter1d(df["flow_ml_s"], sigma=smoothing_sigma)

    start_index = df.index[df["flow_ml_s"] > flow_threshold][0]
    end_index = df.index[df["flow_ml_s"] > flow_threshold][-1]
    df = df.loc[start_index:end_index].reset_index(drop=True)
    df["time_s"] = df["time_s"] - df["time_s"].iloc[0]

    df["interruption"] = df["flow_ml_s"] < flow_threshold
    pauses = []
    start = None
    for i in range(len(df)):
        if df["interruption"].iloc[i]:
            if start is None:
                start = df["time_s"].iloc[i]
        else:
            if start is not None:
                end = df["time_s"].iloc[i]
                if end - start >= min_pause_duration:
                    pauses.append((start, end))
                start = None

    total_volume = df["weight_g"].max()
    total_duration = df["time_s"].iloc[-1] - df["time_s"].iloc[0]
    emptying_time = df["time_s"].iloc[-1]
    active_flow_time = df[~df["interruption"]].shape[0] * (df["time_s"].iloc[-1] / len(df))

    q_max = df["flow_ml_s"].max()
    time_qmax = df.loc[df["flow_ml_s"].idxmax(), "time_s"]
    q_avg = total_volume / total_duration

    return df, {
        "total_volume": total_volume,
        "total_duration": total_duration,
        "emptying_time": emptying_time,
        "active_flow_time": active_flow_time,
        "q_max": q_max,
        "time_qmax": time_qmax,
        "q_avg": q_avg,
        "pauses": pauses
    }

def generate_pdf(df, metrics, pdf_path="uroflow_report_two_pages.pdf"):
    with PdfPages(pdf_path) as pdf:
        fig1, ax1 = plt.subplots(figsize=(11.69, 8.27))
        ax1.plot(df["time_s"], df["weight_g"], label="Voided volume", color="green", linewidth=2)
        ax1b = ax1.twinx()
        ax1b.plot(df["time_s"], df["flow_ml_s"], label="Urine flow (smoothed)", color="blue", alpha=0.6)
        ax1b.axvline(metrics["time_qmax"], color="red", linestyle="--", label="T@Qmax")
        ax1b.axhline(metrics["q_max"], color="red", linestyle="--")
        ax1b.text(metrics["time_qmax"], metrics["q_max"] - 0.5, f"Qmax = {metrics['q_max']:.1f} mL/s", color="red", fontsize=10)
        ax1b.axhline(metrics["q_avg"], color="magenta", linestyle="--")
        ax1b.text(df["time_s"].iloc[0], metrics["q_avg"] - 0.5, f"Qavg = {metrics['q_avg']:.1f} mL/s", color="magenta", fontsize=10)
        ax1.axvspan(df["time_s"].iloc[0], df["time_s"].iloc[-1], color="yellow", alpha=0.2)
        for p_start, p_end in metrics["pauses"]:
            ax1b.axvspan(p_start, p_end, color="gray", alpha=0.2)
        ax1.set_title("Complete uroflowgram with extended analysis")
        ax1.set_xlabel("Time (s)")
        ax1.set_ylabel("Volume (mL)", color="green")
        ax1b.set_ylabel("Flow (mL/s)", color="blue")
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1b.get_legend_handles_labels()
        unique = dict(zip(labels1 + labels2, lines1 + lines2))
        ax1b.legend(unique.values(), unique.keys(), loc="lower left")
        fig1.tight_layout()
        pdf.savefig(fig1)
        plt.close(fig1)

        fig2 = plt.figure(figsize=(8.27, 11.69))
        ax = fig2.add_subplot(111)
        ax.axis("off")

        report = (
            f"""
Measured parameters:
- Total voided volume: {metrics['total_volume']:.1f} mL
- Total duration: {metrics['total_duration']:.1f} s
- Emptying time: {metrics['emptying_time']:.1f} s
- Active flow time: {metrics['active_flow_time']:.1f} s
- Qmax: {metrics['q_max']:.1f} mL/s (at {metrics['time_qmax']:.1f} s)
- Qavg: {metrics['q_avg']:.1f} mL/s
- Number of interruptions: {len(metrics['pauses'])}

Detected interruptions:
"""
            + "\n".join([
                f"  {i+1}. From {start:.2f} s to {end:.2f} s (duration: {end - start:.2f} s)"
                for i, (start, end) in enumerate(metrics["pauses"])
            ])
        )

        ax.text(0, 1, report, va="top", fontsize=10, family="monospace")
        fig2.tight_layout()
        pdf.savefig(fig2)
        plt.close(fig2)

    print(f"PDF saved to: {pdf_path}")

if __name__ == "__main__":
    FILE_PATH = "data/sample_data.csv"
    df = load_data(FILE_PATH)
    df, metrics = analyze_flow(df)
    generate_pdf(df, metrics)
