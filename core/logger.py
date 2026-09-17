"""Rotação de logs de sessão (FIFO, retenção máxima de 10 arquivos)."""

from datetime import datetime
from pathlib import Path

_PASTA_LOGS = Path(__file__).resolve().parent.parent / "logs"
_LIMITE_LOGS = 10


def salvar_log(texto: str, origem: str = "app") -> Path:
  """Persiste o conteúdo do log da UI e aplica rotação FIFO.

  Retorna o caminho do arquivo criado.
  """
  _PASTA_LOGS.mkdir(parents=True, exist_ok=True)
  stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
  destino = _PASTA_LOGS / f"log_{stamp}.txt"
  sufixo = 1
  while destino.exists():
    sufixo += 1
    destino = _PASTA_LOGS / f"log_{stamp}_{sufixo}.txt"
  destino.write_text(f"[{origem}]\n{texto}", encoding="utf-8")
  _rotacionar()
  return destino


def _rotacionar() -> None:
  arquivos = sorted(
      _PASTA_LOGS.glob("log_*.txt"), key=lambda p: p.stat().st_mtime
  )
  while len(arquivos) > _LIMITE_LOGS:
    mais_antigo = arquivos.pop(0)
    try:
      mais_antigo.unlink()
    except OSError:
      break


def ultimo_resumo() -> str:
  """Data/hora e primeira linha útil do log mais recente, ou fallback."""
  arquivos = sorted(
      _PASTA_LOGS.glob("log_*.txt"), key=lambda p: p.stat().st_mtime
  ) if _PASTA_LOGS.is_dir() else []
  if not arquivos:
    return "Nenhum registro prévio"

  mais_recente = arquivos[-1]
  stamp = datetime.fromtimestamp(
      mais_recente.stat().st_mtime
  ).strftime("%d/%m/%Y %H:%M:%S")
  try:
    linhas = [
        linha.strip()
        for linha in mais_recente.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
        if linha.strip() and not linha.startswith("[")
    ]
    resumo = linhas[0][:80] if linhas else mais_recente.name
  except OSError:
    resumo = mais_recente.name
  return f"{stamp} — {resumo}"
