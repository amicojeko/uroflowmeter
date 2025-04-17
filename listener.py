# listen_serial.py (interfaccia migliorata con Rich TUI a schermo intero e hotkey 'R')

import serial
import time
import os
from datetime import datetime
from uroflowmeter import load_data, analyze_flow, generate_pdf
from serial.tools import list_ports
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.table import Table
from rich.text import Text
from rich.prompt import IntPrompt
from rich.align import Align
import threading
import sys

console = Console()
BEGIN_MARKER = "BEGIN DATA"
END_MARKER = "END DATA"
TIMEOUT_SECONDS = 3


def list_serial_ports():
    ports = list(list_ports.comports())
    return [(p.device, p.description) for p in ports]


def create_layout():
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=2),
        Layout(name="footer", size=4)
    )
    layout["main"].split_row(
        Layout(name="status"),
        Layout(name="data")
    )
    layout["status"].update(Panel(Text("Pronto per la ricezione dati", style="bold yellow"), title="STATUS"))
    layout["data"].update(Panel(Text("", style="green"), title="DATA"))
    layout["footer"].update(Panel(Text("", style="dim"), title=""))
    return layout


def get_user_selection():
    ports = list_serial_ports()
    if not ports:
        console.print("[red]Nessuna porta seriale trovata.[/red]")
        sys.exit(1)

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID")
    table.add_column("Dispositivo")
    table.add_column("Descrizione")
    for i, (device, desc) in enumerate(ports):
        table.add_row(str(i), device, desc)

    console.print(table)
    choice = IntPrompt.ask("Seleziona la porta", choices=[str(i) for i in range(len(ports))])
    selected_port = ports[int(choice)][0]
    baudrate = IntPrompt.ask("Inserisci il baudrate", default=115200)

    return selected_port, baudrate


def listen_serial(output_dir="output"):
    selected_port, baudrate = get_user_selection()
    layout = create_layout()
    status_message = Text("Pronto per la ricezione dati", style="bold yellow")
    data_lines = []
    outcome_message = Text("")

    def keyboard_listener():
        import termios, tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while True:
                if sys.stdin.read(1).lower() == 'r':
                    console.bell()
                    return  # trigger restart
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    with Live(layout, refresh_per_second=10, screen=True):
        layout["header"].update(Panel(Text(f" UROFLUSSOMETRO - {selected_port} @ {baudrate} baud  [Premi R per resettare, Ctrl+C per uscire] ", style="bold white on blue")))

        while True:
            try:
                ser = serial.Serial(selected_port, baudrate, timeout=1)
                lines = []
                recording = False
                last_data_time = None
                status_message = Text("Pronto per la ricezione dati", style="bold yellow")

                key_thread = threading.Thread(target=keyboard_listener, daemon=True)
                key_thread.start()

                while key_thread.is_alive():
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue

                    if line == BEGIN_MARKER:
                        status_message = Text("Ricezione dati in corso...", style="bold green")
                        lines = []
                        data_lines = []
                        recording = True
                        last_data_time = time.time()
                        layout["data"].update(Panel(Text("", style="green"), title="DATA"))
                        continue  # FIXATO: prima c'era break, impediva la ricezione

                    if recording:
                        if line == END_MARKER:
                            status_message = Text("Elaborazione dati...", style="bold yellow")
                            break

                        lines.append(line)
                        data_lines.append(line)
                        last_data_time = time.time()

                        if last_data_time and (time.time() - last_data_time > TIMEOUT_SECONDS):
                            status_message = Text("Timeout: trasmissione interrotta", style="bold red")
                            break

                    layout["status"].update(Panel(status_message, title="STATUS"))
                    layout["data"].update(Panel(Text("\n".join(data_lines[-(layout["data"].size or 20):]), style="green"), title="DATA"))

                ser.close()

                if lines:
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = os.path.join(output_dir, f"uroflow_{timestamp}.csv")
                    with open(filename, "w") as f:
                        f.write("\n".join(lines))

                    try:
                        df = load_data(filename)
                        df, metrics = analyze_flow(df)
                        pdf_path = filename.replace(".csv", ".pdf")
                        generate_pdf(df, metrics, pdf_path=pdf_path)
                        outcome_message = Text("✓ Report generato con successo:\n", style="bold green")
                        outcome_message.append(f"{pdf_path}")
                        console.bell()
                    except Exception as e:
                        outcome_message = Text("Errore durante la generazione del report:\n", style="bold red")
                        outcome_message.append(str(e))

                    status_message = Text("Pronto per la ricezione dati", style="bold yellow")

                layout["status"].update(Panel(status_message, title="STATUS"))
                layout["data"].update(Panel(Text("\n".join(data_lines[-(layout["data"].size or 20):]), style="green"), title="DATA"))
                layout["footer"].update(Panel(outcome_message, title=""))

            except serial.SerialException as e:
                outcome_message = Text(f"Errore seriale: {e}", style="bold red")
                layout["footer"].update(Panel(outcome_message, title=""))
                time.sleep(3)
            except Exception as e:
                outcome_message = Text(f"Errore imprevisto: {e}", style="bold red")
                layout["footer"].update(Panel(outcome_message, title=""))
                time.sleep(3)


if __name__ == "__main__":
    try:
        listen_serial()
    except KeyboardInterrupt:
        console.print("\n[bold red]Interrotto dall'utente.[/bold red]")
