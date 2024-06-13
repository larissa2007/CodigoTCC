import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import QTimer, Qt
import pyqtgraph as pg
import serial
from collections import deque
import csv
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import medfilt2d

# Configurações da porta serial
porta_serial = 'COM4'
baud_rate = 115200
conexao = serial.Serial(porta_serial, baud_rate)

# Configurações do PyQt5
app = QApplication(sys.argv)
window = QMainWindow()
central_widget = QWidget()
layout = QVBoxLayout(central_widget)
window.setCentralWidget(central_widget)
plot_widget = pg.PlotWidget()
layout.addWidget(plot_widget)
window.show()
status_label = QLabel("Dados salvos: NÃO")
layout.addWidget(status_label)

# Variáveis para os dados
max_data_length = 5000  # alteração dos segundos na tabela
x_vals = deque(maxlen=max_data_length)
y_vals = deque(maxlen=max_data_length)
timestamps = deque(maxlen=max_data_length)
curve = plot_widget.plot()
plot_widget.setYRange(0, 1023)

space_pressed = False

def salvar_dados(y_vals, timestamps, folder_path):
    existing_files = [name for name in os.listdir(folder_path) if name.endswith(".csv")]
    if existing_files:
        existing_numbers = [int(name.split("_")[1].split(".")[0]) for name in existing_files if name.split("_")[1].split(".")[0].isdigit()]
        new_number = max(existing_numbers) + 1 if existing_numbers else 1
    else:
        new_number = 1

    first_timestamp = timestamps[0]
    standardized_timestamps = [timestamp - first_timestamp for timestamp in timestamps]

    csv_file_name = f"dados_{new_number:04d}.csv"
    csv_file_path = os.path.join(folder_path, csv_file_name)
    try:
        with open(csv_file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Tempo', 'Tensão'])
            for timestamp, value in zip(standardized_timestamps, y_vals):
                writer.writerow([timestamp, value])
        status_label.setText("Dados salvos: SIM")
    except Exception as e:
        print(f"Erro ao salvar os dados: {str(e)}")
        status_label.setText("Dados salvos: NÃO")

def salvar_forma_de_onda_e_pseudocolor(y_vals, timestamps, folder_path, graph_name):
    y_vals = np.array(y_vals)
    timestamps = np.array(timestamps)
    standardized_timestamps = timestamps - timestamps[0]  # Convert to seconds

    existing_files = [name for name in os.listdir(folder_path) if name.startswith(graph_name)]
    if existing_files:
        existing_numbers = [int(name.split("_")[-1].split(".")[0]) for name in existing_files if name.split("_")[-1].split(".")[0].isdigit()]
        new_number = max(existing_numbers) + 1 if existing_numbers else 1
    else:
        new_number = 1

    graph_file_name = f"{graph_name}_{new_number:04d}.png"
    graph_file_path = os.path.join(folder_path, graph_file_name)

    try:
        plt.figure(figsize=(12, 10))

        # Primeiro gráfico: Forma de onda
        plt.subplot(2, 1, 1)
        plt.plot(standardized_timestamps, y_vals, color='red')
        plt.xlabel('Tempo [s]')
        plt.ylabel('Resposta do Conversor Analógico-Digital')
        plt.xlim([0, standardized_timestamps[-1]])  # Define o intervalo de tempo
        plt.ylim([0, 1000])
        plt.title('Forma de Onda')

        # Segundo gráfico: Espectrograma
        plt.subplot(2, 1, 2)
        Fs = len(y_vals) / (timestamps[-1] - timestamps[0])  # Calculating sampling frequency
        Pxx, freqs, bins, im = plt.specgram(y_vals, NFFT=256, Fs=Fs, noverlap=128, window=np.hanning(256))  # mexer nos valores proporcionais aqui para diferentes resoluções do pseudocolor
        Pxx = medfilt2d(Pxx, kernel_size=3)
        Pxx = 10 * np.log10(Pxx + 1e-8)
        plt.imshow(Pxx, aspect='auto', origin='lower', extent=[0, standardized_timestamps[-1], freqs.min(), freqs.max()], cmap='inferno')
        plt.colorbar(label='Intensidade [dB]')
        plt.xlabel('Tempo [s]')
        plt.ylabel('Frequência [Hz]')
        plt.title('Pseudocolor')

        plt.tight_layout()
        plt.savefig(graph_file_path)
        plt.close()
        print(f"Gráfico salvo: {graph_file_name}")
    except Exception as e:
        print(f"Erro ao salvar o gráfico: {str(e)}")

def update_plot():
    curve.setData(list(range(len(y_vals))), y_vals)

def read_data():
    try:
        while conexao.in_waiting > 0:
            dados = conexao.readline().decode('latin1').strip()  # Decodificar utilizando latin1
            try:
                valor = float(dados)
                timestamp = time.time()
                x_vals.append(timestamp)
                y_vals.append(valor)
                timestamps.append(timestamp)
            except ValueError:
                pass
        if x_vals:
            update_plot()
    except KeyboardInterrupt:
        print("Leitura de dados interrompida")

def keyReleaseEvent(event):
    global space_pressed
    if event.key() == Qt.Key_Space:
        space_pressed = False
        print("Botão de espaço liberado")
        if y_vals:
            #salvar_dados(list(y_vals), list(timestamps), r"C:\Users\lahpi\Desktop\DadosTCC")
            salvar_forma_de_onda_e_pseudocolor(list(y_vals), list(timestamps), r"C:\Users\lahpi\Desktop\DadosTCC", "Movimento")
        else:
            print("Nenhum dado disponível para salvar")

window.keyReleaseEvent = keyReleaseEvent

timer = QTimer()
timer.timeout.connect(read_data)
timer.start(0)

sys.exit(app.exec_())
