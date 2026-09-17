"""
Módulo de otimização de imagens individuais e em lote via Pillow.
Substitui a implementação monolítica de 'comprimir.py'.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import os
from pathlib import Path
import time
from typing import Generator
from PIL import Image, ImageOps

from core.binarios import gerar_destino_unico


@dataclass(frozen=True)
class ResultadoCompressao:
    caminho_origem: Path
    caminho_destino: Path
    tamanho_original_bytes: int
    tamanho_final_bytes: int
    sucesso: bool
    tempo_processamento_s: float = 0.0
    mensagem_erro: str = ""


FORMATOS_SAIDA = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def _validar_parametros(
    max_dimensao: int, qualidade: int, formato_saida: str = "JPEG"
) -> str:
    if not 1 <= qualidade <= 100:
        return "Qualidade deve estar no intervalo [1, 100]."
    if max_dimensao <= 0:
        return "Dimensão máxima deve ser maior que zero."
    if formato_saida not in FORMATOS_SAIDA:
        return "Formato inválido. Use JPEG, PNG ou WEBP."
    return ""


def otimizar_imagem(
    origem: Path,
    destino: Path,
    max_dimensao: int = 1920,
    qualidade: int = 80,
    formato_saida: str = "JPEG",
) -> ResultadoCompressao:
    t_inicio = time.perf_counter()
    if erro := _validar_parametros(max_dimensao, qualidade, formato_saida):
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
            perfil_icc = img.info.get("icc_profile")
            img = ImageOps.exif_transpose(img)

            tem_alfa = img.mode in ("RGBA", "LA") or (
                img.mode == "P" and "transparency" in img.info
            )
            if formato_saida == "JPEG":
                if tem_alfa:
                    fundo = Image.new("RGB", img.size, (255, 255, 255))
                    img_rgba = img.convert("RGBA")
                    fundo.paste(img_rgba, mask=img_rgba.split()[3])
                    img = fundo
                elif img.mode != "RGB":
                    img = img.convert("RGB")
            elif tem_alfa:
                img = img.convert("RGBA")
            elif img.mode == "P":
                img = img.convert("RGB")

            if img.width > max_dimensao or img.height > max_dimensao:
                img.thumbnail(
                    (max_dimensao, max_dimensao), Image.Resampling.LANCZOS
                )

            destino.parent.mkdir(parents=True, exist_ok=True)
            opcoes_save = {"optimize": True}
            if formato_saida != "PNG":
                opcoes_save["quality"] = qualidade
            if perfil_icc:
                opcoes_save["icc_profile"] = perfil_icc
            img.save(destino, formato_saida, **opcoes_save)

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
    formato_saida: str = "JPEG",
) -> Generator[ResultadoCompressao, None, None]:
    extensoes_validas = {".jpg", ".jpeg", ".png", ".webp"}
    if erro := _validar_parametros(max_dimensao, qualidade, formato_saida):
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

    alvos = [
        arquivo
        for arquivo in arquivos
        if arquivo.is_file() and arquivo.suffix.lower() in extensoes_validas
    ]

    ext_saida = FORMATOS_SAIDA[formato_saida]
    reservados: set[Path] = set()
    destinos = {
        arquivo: gerar_destino_unico(
            diretorio_destino, arquivo.stem, "otimizada", ext_saida,
            reservados=reservados,
        )
        for arquivo in alvos
    }
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        futuros = {
            executor.submit(
                otimizar_imagem,
                arquivo,
                destinos[arquivo],
                max_dimensao,
                qualidade,
                formato_saida,
            ): arquivo
            for arquivo in alvos
        }
        for futuro in as_completed(futuros):
            arquivo = futuros[futuro]
            try:
                yield futuro.result()
            except Exception as e:
                yield ResultadoCompressao(
                    caminho_origem=arquivo,
                    caminho_destino=destinos[arquivo],
                    tamanho_original_bytes=0,
                    tamanho_final_bytes=0,
                    sucesso=False,
                    mensagem_erro=str(e),
                )


FORMATOS_CONVERSAO = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".webp": "WEBP",
    ".ico": "ICO",
    ".bmp": "BMP",
}
_FORMATOS_COM_ALFA = {"PNG", "WEBP", "ICO"}


def converter_imagem(origem: Path, destino: Path) -> ResultadoCompressao:
    """Conversão 1:1 de formato via Pillow, sem redimensionamento forçado.

    Preserva transparência quando o formato de destino suporta (PNG,
    WEBP, ICO); aplica fundo branco quando não suporta (JPEG, BMP).
    """
    t_inicio = time.perf_counter()
    formato = FORMATOS_CONVERSAO.get(destino.suffix.lower())
    if formato is None:
        return ResultadoCompressao(
            caminho_origem=origem,
            caminho_destino=destino,
            tamanho_original_bytes=0,
            tamanho_final_bytes=0,
            sucesso=False,
            mensagem_erro=(
                f"Formato de destino não suportado: {destino.suffix}"
            ),
        )
    try:
        with Image.open(origem) as img:
            perfil_icc = img.info.get("icc_profile")
            img = ImageOps.exif_transpose(img)

            tem_alfa = img.mode in ("RGBA", "LA") or (
                img.mode == "P" and "transparency" in img.info
            )
            if formato in _FORMATOS_COM_ALFA:
                if tem_alfa:
                    img = img.convert("RGBA")
                elif img.mode == "P":
                    img = img.convert("RGB")
            elif tem_alfa:
                fundo = Image.new("RGB", img.size, (255, 255, 255))
                img_rgba = img.convert("RGBA")
                fundo.paste(img_rgba, mask=img_rgba.split()[3])
                img = fundo
            elif img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            destino.parent.mkdir(parents=True, exist_ok=True)
            opcoes_save = {}
            if formato == "JPEG":
                opcoes_save = {"optimize": True, "quality": 92}
            if perfil_icc and formato != "ICO":
                opcoes_save["icc_profile"] = perfil_icc
            img.save(destino, formato, **opcoes_save)

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