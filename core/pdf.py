"""Manipulação pura de PDFs via pypdf: unir, extrair e dividir."""

from dataclasses import dataclass
import io
from pathlib import Path
import re
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


def rotacionar_pdf(
    origem: Path,
    angulo: int,
    paginas: Optional[list[int]],
    destino: Path,
) -> ResultadoOperacaoPDF:
    """Rotaciona todas ou páginas específicas (1-based) em 90/180/270°."""
    if angulo not in (90, 180, 270):
        return _falha(
            origem, destino, "Ângulo deve ser 90, 180 ou 270."
        )
    if not origem.is_file():
        return _falha(origem, destino, "Arquivo de origem não existe.")
    try:
        leitor = PdfReader(str(origem))
        total = len(leitor.pages)
        alvo = set(paginas) if paginas else set(range(1, total + 1))
        invalidas = sorted(p for p in alvo if p < 1 or p > total)
        if invalidas:
            return _falha(
                origem, destino,
                f"Páginas inválidas {invalidas} (documento tem"
                f" {total} página(s)).",
            )
        escritor = PdfWriter()
        for i in range(1, total + 1):
            pagina = leitor.pages[i - 1]
            if i in alvo:
                pagina.rotate(angulo)
            escritor.add_page(pagina)
        destino.parent.mkdir(parents=True, exist_ok=True)
        with open(destino, "wb") as f:
            escritor.write(f)
        return ResultadoOperacaoPDF(
            sucesso=True,
            caminho_origem=origem,
            caminho_destino=destino,
            total_paginas=total,
        )
    except Exception as e:
        destino.unlink(missing_ok=True)
        return _falha(origem, destino, str(e))


def mix_alternado_pdf(
    arquivo_a: Path,
    arquivo_b: Path,
    inverter_b: bool,
    destino: Path,
) -> ResultadoOperacaoPDF:
    """Intercala A1,B1,A2,B2... (ou B invertido); excedentes ao final."""
    for arq in (arquivo_a, arquivo_b):
        if not arq.is_file():
            return _falha(arq, destino, f"Arquivo inexistente: {arq}")
    try:
        paginas_a = PdfReader(str(arquivo_a)).pages
        paginas_b = PdfReader(str(arquivo_b)).pages
        idx_b = list(range(len(paginas_b)))
        if inverter_b:
            idx_b.reverse()

        escritor = PdfWriter()
        n_comum = min(len(paginas_a), len(paginas_b))
        for i in range(n_comum):
            escritor.add_page(paginas_a[i])
            escritor.add_page(paginas_b[idx_b[i]])
        for i in range(n_comum, len(paginas_a)):
            escritor.add_page(paginas_a[i])
        for i in range(n_comum, len(paginas_b)):
            escritor.add_page(paginas_b[idx_b[i]])

        total = len(paginas_a) + len(paginas_b)
        destino.parent.mkdir(parents=True, exist_ok=True)
        with open(destino, "wb") as f:
            escritor.write(f)
        return ResultadoOperacaoPDF(
            sucesso=True,
            caminho_origem=arquivo_a,
            caminho_destino=destino,
            total_paginas=total,
        )
    except Exception as e:
        destino.unlink(missing_ok=True)
        return _falha(arquivo_a, destino, str(e))


def dividir_por_tamanho_pdf(
    origem: Path, teto_mb: float, pasta_destino: Path
) -> list[ResultadoOperacaoPDF]:
    """Fatia o PDF em blocos de até ~teto_mb MB (mín. 1 página/bloco)."""
    if not origem.is_file():
        return [
            _falha(origem, pasta_destino, "Arquivo de origem não existe.")
        ]
    if teto_mb <= 0:
        return [_falha(origem, pasta_destino, "Teto deve ser > 0 MB.")]
    try:
        leitor = PdfReader(str(origem))
        pasta_destino.mkdir(parents=True, exist_ok=True)
        teto_bytes = teto_mb * 1024 * 1024
        reservados: set[Path] = set()
        resultados: list[ResultadoOperacaoPDF] = []
        escritor = PdfWriter()
        paginas_bloco = 0

        def fechar_bloco() -> None:
            nonlocal escritor, paginas_bloco
            destino = gerar_destino_unico(
                pasta_destino,
                f"{origem.stem}_bloco_{len(resultados) + 1:03d}",
                "pdf",
                ".pdf",
                reservados=reservados,
            )
            try:
                with open(destino, "wb") as f:
                    escritor.write(f)
                resultados.append(
                    ResultadoOperacaoPDF(
                        sucesso=True,
                        caminho_origem=origem,
                        caminho_destino=destino,
                        total_paginas=paginas_bloco,
                    )
                )
            except Exception as e:
                resultados.append(_falha(origem, destino, str(e)))
            escritor = PdfWriter()
            paginas_bloco = 0

        for pagina in leitor.pages:
            escritor.add_page(pagina)
            paginas_bloco += 1
            buffer = io.BytesIO()
            escritor.write(buffer)
            if buffer.tell() >= teto_bytes:
                fechar_bloco()
        if paginas_bloco > 0:
            fechar_bloco()
        return resultados
    except Exception as e:
        return [_falha(origem, pasta_destino, str(e))]


def _sanitizar_rotulo(texto: str) -> str:
    limpo = re.sub(r"[^\w\- ]+", "", texto).strip().replace(" ", "_")
    return limpo[:60] or "secao"


def dividir_por_marcadores_pdf(
    origem: Path, nivel: int, pasta_destino: Path
) -> list[ResultadoOperacaoPDF]:
    """Fatia o PDF nos pontos de quebra dos marcadores (outline)."""
    if not origem.is_file():
        return [
            _falha(origem, pasta_destino, "Arquivo de origem não existe.")
        ]
    if nivel < 1:
        return [_falha(origem, pasta_destino, "Nível deve ser >= 1.")]
    try:
        leitor = PdfReader(str(origem))
        try:
            outline = leitor.outline
        except Exception:
            outline = []
        if not outline:
            return [
                _falha(
                    origem, pasta_destino,
                    "Documento não contém marcadores/índice interno",
                )
            ]

        pontos: list[tuple[int, str]] = []

        def caminhar(itens, profundidade: int) -> None:
            for item in itens:
                if isinstance(item, list):
                    caminhar(item, profundidade + 1)
                elif profundidade == nivel:
                    try:
                        pagina = leitor.get_destination_page_number(item)
                    except Exception:
                        continue
                    if pagina is not None and pagina >= 0:
                        titulo = getattr(item, "title", "") or ""
                        pontos.append((pagina, titulo))

        caminhar(outline, 1)
        total = len(leitor.pages)
        titulos = {p: t for p, t in pontos}
        quebras = sorted({p for p, _ in pontos if 0 < p < total})
        limites = [0] + quebras + [total]

        pasta_destino.mkdir(parents=True, exist_ok=True)
        reservados: set[Path] = set()
        resultados: list[ResultadoOperacaoPDF] = []
        for i in range(len(limites) - 1):
            ini, fim = limites[i], limites[i + 1]
            rotulo = _sanitizar_rotulo(titulos.get(ini, ""))
            destino = gerar_destino_unico(
                pasta_destino,
                f"{origem.stem}_{rotulo}",
                "pdf",
                ".pdf",
                reservados=reservados,
            )
            try:
                escritor = PdfWriter()
                for p in range(ini, fim):
                    escritor.add_page(leitor.pages[p])
                with open(destino, "wb") as f:
                    escritor.write(f)
                resultados.append(
                    ResultadoOperacaoPDF(
                        sucesso=True,
                        caminho_origem=origem,
                        caminho_destino=destino,
                        total_paginas=fim - ini,
                    )
                )
            except Exception as e:
                resultados.append(_falha(origem, destino, str(e)))
        return resultados
    except Exception as e:
        return [_falha(origem, pasta_destino, str(e))]
