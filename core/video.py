"""
Módulo de compressão de vídeo via FFmpeg com monitoramento de telemetria.
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from typing import Optional
import psutil

from core.calculadora import calcular_bitrate_alvo_kbps

_CREATIONFLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_processos_ativos: set[subprocess.Popen] = set()
_lock_processos = threading.Lock()


def _matar_arvore_processo(processo: subprocess.Popen) -> None:
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(processo.pid)],
                capture_output=True,
                timeout=10,
                creationflags=_CREATIONFLAGS,
            )
            return
        except Exception:
            pass
    try:
        processo.kill()
    except Exception:
        pass


def cancelar_processos_ativos() -> None:
    with _lock_processos:
        processos = list(_processos_ativos)
    for processo in processos:
        if processo.poll() is None:
            _matar_arvore_processo(processo)
            try:
                processo.wait(timeout=10)
            except Exception:
                pass


@dataclass
class EstatisticasHardware:
    cpu_media: float
    cpu_pico: float
    ram_media_mb: float
    ram_pico_mb: float
    gpu_media: float
    gpu_pico: float
    vram_pico_mb: float
    modelo_gpu: str


class MonitorHardware:

    def __init__(self, intervalo: float = 0.5):
        self.intervalo = intervalo
        self._ativo = False
        self._thread: Optional[threading.Thread] = None
        self._cpu_samples: list[float] = []
        self._ram_samples: list[float] = []
        self._gpu_samples: list[float] = []
        self._vram_samples: list[float] = []
        self._modelo_gpu: str = self._obter_modelo_gpu()

    def _obter_modelo_gpu(self) -> str:
        try:
            cmd = ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"]
            out = subprocess.check_output(
                cmd, encoding="utf-8", timeout=2, creationflags=_CREATIONFLAGS
            )
            return out.strip().split("\n")[0]
        except Exception:
            return "N/A"

    def _obter_telemetria_gpu(self) -> tuple[float, float]:
        try:
            cmd = [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used",
                "--format=csv,noheader,nounits",
            ]
            out = subprocess.check_output(
                cmd, encoding="utf-8", timeout=2, creationflags=_CREATIONFLAGS
            )
            dados = out.strip().split("\n")[0].split(",")
            return float(dados[0].strip()), float(dados[1].strip())
        except Exception:
            return 0.0, 0.0

    def _loop_coleta(self):
        while self._ativo:
            self._cpu_samples.append(psutil.cpu_percent())
            self._ram_samples.append(
                psutil.virtual_memory().used / (1024 * 1024)
            )
            gpu_util, vram_usada = self._obter_telemetria_gpu()
            self._gpu_samples.append(gpu_util)
            self._vram_samples.append(vram_usada)
            time.sleep(self.intervalo)

    def iniciar(self):
        self._ativo = True
        self._cpu_samples.clear()
        self._ram_samples.clear()
        self._gpu_samples.clear()
        self._vram_samples.clear()
        self._thread = threading.Thread(target=self._loop_coleta, daemon=True)
        self._thread.start()

    def parar(self) -> EstatisticasHardware:
        self._ativo = False
        if self._thread:
            self._thread.join(timeout=2.0)

        def media(lista: list[float]) -> float:
            return sum(lista) / len(lista) if lista else 0.0

        def pico(lista: list[float]) -> float:
            return max(lista) if lista else 0.0

        return EstatisticasHardware(
            cpu_media=media(self._cpu_samples),
            cpu_pico=pico(self._cpu_samples),
            ram_media_mb=media(self._ram_samples),
            ram_pico_mb=pico(self._ram_samples),
            gpu_media=media(self._gpu_samples),
            gpu_pico=pico(self._gpu_samples),
            vram_pico_mb=pico(self._vram_samples),
            modelo_gpu=self._modelo_gpu,
        )


@dataclass
class ResultadoCompressaoVideo:
    caminho_origem: Path
    caminho_destino: Path
    duracao_segundos: float
    tamanho_original_bytes: int
    tamanho_final_bytes: int
    bitrate_k: int
    telemetria: EstatisticasHardware
    sucesso: bool
    tempo_processamento_s: float = 0.0
    mensagem_erro: str = ""


def obter_duracao_video(origem: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(origem),
    ]
    resultado = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
        creationflags=_CREATIONFLAGS,
    )
    dados = json.loads(resultado.stdout)
    return float(dados["format"]["duration"])


def comprimir_video(
    origem: Path,
    destino: Path,
    tamanho_alvo_mb: float = 25.0,
    audio_bitrate_kbps: int = 96,
) -> ResultadoCompressaoVideo:
    telemetria_vazia = EstatisticasHardware(0, 0, 0, 0, 0, 0, 0, "N/A")
    t_inicio = time.perf_counter()

    if not origem.is_file():
        return ResultadoCompressaoVideo(
            caminho_origem=origem,
            caminho_destino=destino,
            duracao_segundos=0,
            tamanho_original_bytes=0,
            tamanho_final_bytes=0,
            bitrate_k=0,
            telemetria=telemetria_vazia,
            sucesso=False,
            tempo_processamento_s=0.0,
            mensagem_erro="Arquivo de origem não existe.",
        )

    try:
        duracao = obter_duracao_video(origem)
        tamanho_original = origem.stat().st_size
        bitrate_v = calcular_bitrate_alvo_kbps(
            duracao, tamanho_alvo_mb, audio_bitrate_kbps
        )
    except Exception as e:
        return ResultadoCompressaoVideo(
            caminho_origem=origem,
            caminho_destino=destino,
            duracao_segundos=0,
            tamanho_original_bytes=0,
            tamanho_final_bytes=0,
            bitrate_k=0,
            telemetria=telemetria_vazia,
            sucesso=False,
            tempo_processamento_s=time.perf_counter() - t_inicio,
            mensagem_erro=f"Falha de sonda: {e}",
        )

    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return ResultadoCompressaoVideo(
            caminho_origem=origem,
            caminho_destino=destino,
            duracao_segundos=duracao,
            tamanho_original_bytes=tamanho_original,
            tamanho_final_bytes=0,
            bitrate_k=0,
            telemetria=telemetria_vazia,
            sucesso=False,
            tempo_processamento_s=time.perf_counter() - t_inicio,
            mensagem_erro=f"Falha ao criar diretório de saída: {e}",
        )

    if destino.suffix.lower() == ".webm":
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(origem),
            "-vf",
            "scale=-2:720",
            "-c:v",
            "libvpx-vp9",
            "-b:v",
            f"{bitrate_v}k",
            "-minrate",
            f"{int(bitrate_v * 0.5)}k",
            "-maxrate",
            f"{int(bitrate_v * 1.05)}k",
            "-crf",
            "32",
            "-deadline",
            "realtime",
            "-cpu-used",
            "4",
            "-row-mt",
            "1",
            "-c:a",
            "libopus",
            "-b:a",
            f"{audio_bitrate_kbps}k",
            str(destino),
        ]
    elif destino.suffix.lower() == ".mp4":
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(origem),
            "-vf",
            "scale=-2:720",
            "-c:v",
            "libx264",
            "-preset",
            "faster",
            "-b:v",
            f"{bitrate_v}k",
            "-maxrate",
            f"{int(bitrate_v * 1.2)}k",
            "-bufsize",
            f"{bitrate_v * 2}k",
            "-c:a",
            "aac",
            "-b:a",
            f"{audio_bitrate_kbps}k",
            "-movflags",
            "+faststart",
            str(destino),
        ]
    else:
        return ResultadoCompressaoVideo(
            caminho_origem=origem,
            caminho_destino=destino,
            duracao_segundos=duracao,
            tamanho_original_bytes=tamanho_original,
            tamanho_final_bytes=0,
            bitrate_k=0,
            telemetria=telemetria_vazia,
            sucesso=False,
            tempo_processamento_s=time.perf_counter() - t_inicio,
            mensagem_erro="Formato inválido. Use .mp4 ou .webm",
        )

    monitor = MonitorHardware()
    monitor.iniciar()
    processo: Optional[subprocess.Popen] = None

    try:
        processo = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=_CREATIONFLAGS,
        )
        with _lock_processos:
            _processos_ativos.add(processo)
        _, stderr = processo.communicate()

        if processo.returncode != 0:
            raise subprocess.CalledProcessError(
                processo.returncode, cmd, stderr=stderr
            )

        telemetria = monitor.parar()
        tempo_total = time.perf_counter() - t_inicio
        tamanho_final = destino.stat().st_size
        return ResultadoCompressaoVideo(
            caminho_origem=origem,
            caminho_destino=destino,
            duracao_segundos=duracao,
            tamanho_original_bytes=tamanho_original,
            tamanho_final_bytes=tamanho_final,
            bitrate_k=bitrate_v,
            telemetria=telemetria,
            sucesso=True,
            tempo_processamento_s=tempo_total,
        )

    except (Exception, KeyboardInterrupt) as err:
        if processo and processo.poll() is None:
            _matar_arvore_processo(processo)
        telemetria = monitor.parar()
        tempo_total = time.perf_counter() - t_inicio
        try:
            destino.unlink(missing_ok=True)
        except OSError:
            pass
        return ResultadoCompressaoVideo(
            caminho_origem=origem,
            caminho_destino=destino,
            duracao_segundos=duracao,
            tamanho_original_bytes=tamanho_original,
            tamanho_final_bytes=0,
            bitrate_k=bitrate_v,
            telemetria=telemetria,
            sucesso=False,
            tempo_processamento_s=tempo_total,
            mensagem_erro=str(err),
        )
    finally:
        if processo is not None:
            with _lock_processos:
                _processos_ativos.discard(processo)