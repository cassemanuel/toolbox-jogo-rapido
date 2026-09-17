"""
Módulo de otimização de imagens individuais e em lote via Pillow.
Substitui a implementação monolítica de 'comprimir.py'.
"""

from pathlib import Path
import time
from typing import Generator, NamedTuple
from PIL import Image, ImageOps


class ResultadoCompressao(NamedTuple):
    caminho_origem: Path
    caminho_destino: Path
    tamanho_original_bytes: int
    tamanho_final_bytes: int
    sucesso: bool
    tempo_processamento_s: float = 0.0
    mensagem_erro: str = ""


def otimizar_imagem(
    origem: Path,
    destino: Path,
    max_dimensao: int = 1920,
    qualidade: int = 80,
) -> ResultadoCompressao:
    t_inicio = time.perf_counter()
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
    diretorio_destino.mkdir(parents=True, exist_ok=True)

    for arquivo in diretorio_origem.iterdir():
        if arquivo.is_file() and arquivo.suffix.lower() in extensoes_validas:
            destino_arquivo = (
                diretorio_destino / f"{arquivo.stem}_otimizada.jpg"
            )
            yield otimizar_imagem(
                arquivo, destino_arquivo, max_dimensao, qualidade
            )