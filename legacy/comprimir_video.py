import os
import sys
import time
import json
import re
import subprocess
import threading
from datetime import datetime
import psutil

class MonitorDesempenho:
    def __init__(self, intervalo=0.5):
        self.intervalo = intervalo
        self._ativo = False
        self._thread = None
        self.cpu_samples = []
        self.ram_samples = []
        self.gpu_samples = []

    def _obter_uso_gpu(self):
        try:
            cmd = ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"]
            out = subprocess.check_output(cmd, encoding="utf-8")
            return float(out.strip().split("\n")[0])
        except Exception:
            return 0.0

    def _coletar(self):
        while self._ativo:
            self.cpu_samples.append(psutil.cpu_percent())
            self.ram_samples.append(psutil.virtual_memory().percent)
            self.gpu_samples.append(self._obter_uso_gpu())
            time.sleep(self.intervalo)

    def iniciar(self):
        self._ativo = True
        self.cpu_samples.clear()
        self.ram_samples.clear()
        self.gpu_samples.clear()
        self._thread = threading.Thread(target=self._coletar)
        self._thread.daemon = True
        self._thread.start()

    def parar(self):
        self._ativo = False
        if self._thread:
            self._thread.join()
        return {
            "cpu_media": sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0,
            "cpu_max": max(self.cpu_samples) if self.cpu_samples else 0,
            "ram_max": max(self.ram_samples) if self.ram_samples else 0,
            "gpu_media": sum(self.gpu_samples) / len(self.gpu_samples) if self.gpu_samples else 0,
            "gpu_max": max(self.gpu_samples) if self.gpu_samples else 0,
        }

def obter_duracao(arquivo_entrada):
    """Obtém a duração usando ffprobe ou fallback para ffmpeg."""
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", arquivo_entrada]
        resultado = subprocess.run(cmd, capture_output=True, text=True, check=True)
        dados = json.loads(resultado.stdout)
        return float(dados["format"]["duration"])
    except Exception:
        cmd = ["ffmpeg", "-i", arquivo_entrada]
        resultado = subprocess.run(cmd, capture_output=True, text=True)
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", resultado.stderr)
        if match:
            h, m, s = match.groups()
            return int(h) * 3600 + int(m) * 60 + float(s)
        raise RuntimeError("Não foi possível obter a duração do vídeo.")

def gravar_log(caminho_log, info):
    linhas = [
        "=" * 60,
        f"DATA/HORA        : {info['timestamp']}",
        f"ARQUIVO ENTRADA  : {info['entrada']} ({info['tamanho_original_mb']:.2f} MB)",
        f"ARQUIVO SAÍDA    : {info['saida']} ({info['tamanho_final_mb']:.2f} MB)",
        f"FORMATO DESTINO  : {info['formato'].upper()}",
        f"DURAÇÃO DO VÍDEO : {info['duracao_s']:.1f} segundos",
        f"BITRATE VÍDEO    : {info['bitrate_video_k']} kbps (Áudio: {info['bitrate_audio_k']} kbps)",
        f"TEMPO DE PROCESSO: {info['tempo_gasto_s']:.2f} segundos ({info['tempo_gasto_s'] / 60:.2f} min)",
        f"VELOCIDADE MÉDIA : {info['velocidade_x']:.2f}x tempo real",
        f"USO CPU (MÉD/MAX): {info['cpu_media']:.1f}% / {info['cpu_max']:.1f}%",
        f"USO GPU (MÉD/MAX): {info['gpu_media']:.1f}% / {info['gpu_max']:.1f}%",
        f"PICO MEMÓRIA RAM : {info['ram_max']:.1f}%",
        f"STATUS           : {info['status']}",
        "=" * 60 + "\n"
    ]
    with open(caminho_log, "a", encoding="utf-8") as f:
        f.write("\n".join(linhas))

def comprimir_video(arquivo_entrada, arquivo_saida, tamanho_alvo_mb=25, formato="webm"):
    arquivo_log = "historico_conversoes.log"
    if not os.path.exists(arquivo_entrada):
        print(f"Erro: Arquivo '{arquivo_entrada}' não encontrado.")
        return

    tamanho_original_mb = os.path.getsize(arquivo_entrada) / (1024 * 1024)
    duracao = obter_duracao(arquivo_entrada)

    total_kilobits = tamanho_alvo_mb * 8192
    audio_bitrate_k = 96
    total_bitrate_k = total_kilobits / duracao
    video_bitrate_k = int(total_bitrate_k - audio_bitrate_k)

    print(f"\nIniciando conversão monitorada de '{arquivo_entrada}'...")
    print(f"Tamanho original: {tamanho_original_mb:.2f} MB | Duração: {duracao:.1f}s")
    print(f"Bitrate calculado: {video_bitrate_k} kbps (Alvo: {tamanho_alvo_mb} MB)")

    if formato.lower() == "webm":
        cmd = [
            "ffmpeg", "-y", "-i", arquivo_entrada,
            "-vf", "scale=-2:720",
            "-c:v", "libvpx-vp9",
            "-b:v", f"{video_bitrate_k}k",
            "-maxrate", f"{int(video_bitrate_k * 1.05)}k",
            "-minrate", f"{int(video_bitrate_k * 0.5)}k",
            "-crf", "32",
            "-deadline", "realtime",
            "-cpu-used", "4",
            "-row-mt", "1",
            "-threads", "0",
            "-c:a", "libopus",
            "-b:a", f"{audio_bitrate_k}k",
            arquivo_saida
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-i", arquivo_entrada,
            "-vf", "scale=-2:720",
            "-c:v", "libx264",
            "-b:v", f"{video_bitrate_k}k",
            "-preset", "faster",
            "-c:a", "aac",
            "-b:a", f"{audio_bitrate_k}k",
            "-movflags", "+faststart",
            arquivo_saida
        ]

    monitor = MonitorDesempenho(intervalo=0.3)
    monitor.iniciar()
    tempo_inicio = time.time()
    status = "SUCESSO"

    try:
        subprocess.run(cmd, check=True)
    except Exception as erro:
        status = f"FALHA: {erro}"
        print(f"Ocorreu um erro no processo: {erro}")
        monitor.parar()
        return

    tempo_total = time.time() - tempo_inicio
    telemetria = monitor.parar()

    tamanho_final_mb = os.path.getsize(arquivo_saida) / (1024 * 1024)
    velocidade_media = duracao / tempo_total if tempo_total > 0 else 0

    dados_log = {
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "entrada": arquivo_entrada,
        "saida": arquivo_saida,
        "tamanho_original_mb": tamanho_original_mb,
        "tamanho_final_mb": tamanho_final_mb,
        "formato": formato,
        "duracao_s": duracao,
        "bitrate_video_k": video_bitrate_k,
        "bitrate_audio_k": audio_bitrate_k,
        "tempo_gasto_s": tempo_total,
        "velocidade_x": velocidade_media,
        "cpu_media": telemetria["cpu_media"],
        "cpu_max": telemetria["cpu_max"],
        "gpu_media": telemetria["gpu_media"],
        "gpu_max": telemetria["gpu_max"],
        "ram_max": telemetria["ram_max"],
        "status": status
    }

    gravar_log(arquivo_log, dados_log)

    print(f"\n[OK] Processo concluído em {tempo_total:.2f}s!")
    print(f"Telemetria CPU: Média {telemetria['cpu_media']:.1f}% | Pico {telemetria['cpu_max']:.1f}%")
    print(f"Telemetria GPU (RTX 5060): Média {telemetria['gpu_media']:.1f}% | Pico {telemetria['gpu_max']:.1f}%")
    print(f"Arquivo final: {arquivo_saida} ({tamanho_final_mb:.2f} MB)")
    print(f"Log gravado em: {arquivo_log}")

if __name__ == "__main__":
    comprimir_video(
        arquivo_entrada="8K_Thetestdata.mp4",
        arquivo_saida="8K_Thetestdata_720p.webm",
        tamanho_alvo_mb=25,
        formato="webm"
    )