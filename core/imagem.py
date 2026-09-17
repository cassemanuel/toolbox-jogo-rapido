"""
Módulo de otimização de imagens individuais e em lote via Pillow.
Substitui a implementação monolítica de 'comprimir.py'.
"""

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Generator
from PIL import Image, ImageOps


@dataclass(frozen=True)
class ResultadoCompressao:
    caminho_origem: Path
    caminho_destino: Path
    tamanho_original_bytes: int
    tamanho_final_bytes: int
    sucesso: bool
    tempo_processamento_s: float = 0.0
    mensagem_erro: str = ""


def _validar_parametros(max_dimensao: int, qualidade: int) -> str:
    if not 1 <= qualidade <= 100:
        return "Qualidade JPEG deve estar no intervalo [1, 100]."
    if max_dimensao <= 0:
        return "Dimensão máxima deve ser maior que zero."
    return ""


def otimizar_imagem(
    origem: Path,
    destino: Path,
    max_dimensao: int = 1920,
    qualidade: int = 80,
) -> ResultadoCompressao:
    t_inicio = time.perf_counter()
    if erro := _validar_parametros(max_dimensao, qualidade):
        return ResultadoCompressao(
            caminho_origem=origem,
            caminho_destino=destino,
            tamanho_original_bytes=0,
            tamanho_final_bytes=0,
            sucesso=False,
            mensagem_erro=erro,
        )
    try:
        with Image.open(origem) as img:
            img = ImageOps.exif_transpose(img)

            if img.mode in ("RGBA", "LA") or (
                img.mode == "P" and "transparency" in img.info
            ):
                fundo = Image.new("RGB", img.size, (255, 255, 255))
                img_rgba = img.convert("RGBA")
                fundo.paste(img_rgba, mask=img_rgba.split()[3])
                img = fundo
            elif img.mode != "RGB":
                img = img.convert("RGB")

            if img.width > max_dimensao or img.height > max_dimensao:
                img.thumbnail(
                    (max_dimensao, max_dimensao), Image.Resampling.LANCZOS
                )

            destino.parent.mkdir(parents=True, exist_ok=True)
            img.save(destino, "JPEG", optimize=True, quality=qualidade)

            tamanho_original_bytes = origem.stat().st_size
            tamanho_final_bytes = destino.stat().st_size
            tempo_total = time.perf_counter() - t_inicio

            return ResultadoCompressao(
                caminho_origem=origem,
                caminho_destino=destino,
                tamanho_original_bytes=tamanho_original_bytes,
                tamanho_final_bytes=tamanho_final_bytes,
                sucesso=True,
                tempo_processamento_s=tempo_total,
            )
    except Exception as e:
        tempo_total = time.perf_counter() - t_inicio
        return ResultadoCompressao(
            caminho_origem=origem,
            caminho_destino=destino,
            tamanho_original_bytes=0,
            tamanho_final_bytes=0,
            sucesso=False,
            tempo_processamento_s=tempo_total,
            mensagem_erro=str(e),
        )


def otimizar_lote(
    diretorio_origem: Path,
    diretorio_destino: Path,
    max_dimensao: int = 1920,
    qualidade: int = 80,
) -> Generator[ResultadoCompressao, None, None]:
    extensoes_validas = {".jpg", ".jpeg", ".png", ".webp"}
    if erro := _validar_parametros(max_dimensao, qualidade):
        yield ResultadoCompressao(
            caminho_origem=diretorio_origem,
            caminho_destino=diretorio_destino,
            tamanho_original_bytes=0,
            tamanho_final_bytes=0,
            sucesso=False,
            mensagem_erro=erro,
        )
        return
    try:
        diretorio_destino.mkdir(parents=True, exist_ok=True)
        arquivos = sorted(diretorio_origem.iterdir())
    except OSError as e:
        yield ResultadoCompressao(
            caminho_origem=diretorio_origem,
            caminho_destino=diretorio_destino,
            tamanho_original_bytes=0,
            tamanho_final_bytes=0,
            sucesso=False,
            mensagem_erro=f"Falha de I/O no diretório: {e}",
        )
        return

    for arquivo in arquivos:
        if arquivo.is_file() and arquivo.suffix.lower() in extensoes_validas:
            destino_arquivo = (
                diretorio_destino / f"{arquivo.stem}_otimizada.jpg"
            )
            yield otimizar_imagem(
                arquivo, destino_arquivo, max_dimensao, qualidade
            )