"""Manipulação pura de PDFs via pypdf: unir, extrair e dividir."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pypdf import PdfReader, PdfWriter

from core.binarios import gerar_destino_unico


@dataclass(frozen=True)
class ResultadoOperacaoPDF:
    sucesso: bool
    caminho_origem: Optional[Path]
    caminho_destino: Optional[Path]
    total_paginas: int
    mensagem_erro: Optional[str] = None


def _falha(
    origem: Optional[Path], destino: Optional[Path], erro: str
) -> ResultadoOperacaoPDF:
    return ResultadoOperacaoPDF(
        sucesso=False,
        caminho_origem=origem,
        caminho_destino=destino,
        total_paginas=0,
        mensagem_erro=erro,
    )


def unir_pdfs(
    arquivos: list[Path], destino: Path
) -> ResultadoOperacaoPDF:
    """Mescla múltiplos PDFs em ordem sequencial."""
    if not arquivos:
        return _falha(None, destino, "Nenhum arquivo informado.")
    faltantes = [str(p) for p in arquivos if not p.is_file()]
    if faltantes:
        return _falha(
            arquivos[0], destino,
            f"Arquivo(s) inexistente(s): {', '.join(faltantes)}",
        )
    try:
        escritor = PdfWriter()
        total = 0
        for arquivo in arquivos:
            leitor = PdfReader(str(arquivo))
            for pagina in leitor.pages:
                escritor.add_page(pagina)
                total += 1
        destino.parent.mkdir(parents=True, exist_ok=True)
        with open(destino, "wb") as f:
            escritor.write(f)
        return ResultadoOperacaoPDF(
            sucesso=True,
            caminho_origem=arquivos[0],
            caminho_destino=destino,
            total_paginas=total,
        )
    except Exception as e:
        destino.unlink(missing_ok=True)
        return _falha(arquivos[0], destino, str(e))


def extrair_paginas(
    origem: Path, paginas: list[int], destino: Path
) -> ResultadoOperacaoPDF:
    """Extrai páginas específicas (índice 1-based) para novo PDF."""
    if not origem.is_file():
        return _falha(origem, destino, "Arquivo de origem não existe.")
    try:
        leitor = PdfReader(str(origem))
        total_origem = len(leitor.pages)
        invalidas = [
            p for p in paginas if p < 1 or p > total_origem
        ]
        if not paginas or invalidas:
            return _falha(
                origem, destino,
                f"Páginas inválidas {invalidas} (documento tem"
                f" {total_origem} página(s)).",
            )
        escritor = PdfWriter()
        for p in paginas:
            escritor.add_page(leitor.pages[p - 1])
        destino.parent.mkdir(parents=True, exist_ok=True)
        with open(destino, "wb") as f:
            escritor.write(f)
        return ResultadoOperacaoPDF(
            sucesso=True,
            caminho_origem=origem,
            caminho_destino=destino,
            total_paginas=len(paginas),
        )
    except Exception as e:
        destino.unlink(missing_ok=True)
        return _falha(origem, destino, str(e))


def dividir_pdf(
    origem: Path, pasta_destino: Path
) -> list[ResultadoOperacaoPDF]:
    """Salva cada página do PDF em um arquivo individual."""
    if not origem.is_file():
        return [
            _falha(origem, pasta_destino, "Arquivo de origem não existe.")
        ]
    try:
        leitor = PdfReader(str(origem))
        pasta_destino.mkdir(parents=True, exist_ok=True)
        reservados: set[Path] = set()
        resultados: list[ResultadoOperacaoPDF] = []
        for i, pagina in enumerate(leitor.pages, 1):
            destino = gerar_destino_unico(
                pasta_destino,
                f"{origem.stem}_pagina_{i:03d}",
                "pdf",
                ".pdf",
                reservados=reservados,
            )
            try:
                escritor = PdfWriter()
                escritor.add_page(pagina)
                with open(destino, "wb") as f:
                    escritor.write(f)
                resultados.append(
                    ResultadoOperacaoPDF(
                        sucesso=True,
                        caminho_origem=origem,
                        caminho_destino=destino,
                        total_paginas=1,
                    )
                )
            except Exception as e:
                resultados.append(_falha(origem, destino, str(e)))
        return resultados
    except Exception as e:
        return [_falha(origem, pasta_destino, str(e))]
