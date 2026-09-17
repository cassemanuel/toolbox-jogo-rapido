"""Rotação de logs de sessão (FIFO, retenção máxima de 10 arquivos)."""

from datetime import datetime
from pathlib import Path

from core.binarios import obter_diretorio_base

_PASTA_LOGS = obter_diretorio_base() / "logs"
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
  destino.write_text(
      f"[{origem}]\n{_expurgar_historico(texto)}", encoding="utf-8"
  )
  _rotacionar()
  return destino


_MARCADOR_HISTORICO = "================ HISTÓRICO DA ÚLTIMA EXECUÇÃO"
_FIM_HISTORICO = "Pronto para nova operação."


def _expurgar_historico(texto: str) -> str:
  """Remove o bloco de histórico renderizado na UI e o cabeçalho
  legado '>>> Última execução:', preservando o conteúdo real."""
  corpo_linhas = []
  pulando_bloco = False
  pular_separador = False
  for linha in texto.splitlines():
    if linha.startswith(_MARCADOR_HISTORICO):
      pulando_bloco = True
      continue
    if pulando_bloco:
      if linha.strip() == _FIM_HISTORICO:
        pulando_bloco = False
        continue
      if linha.startswith(">>>"):
        pulando_bloco = False
      else:
        continue
    if linha.startswith(">>> Última execução:"):
      pular_separador = True
      continue
    if (
        pular_separador
        and linha.strip()
        and set(linha.strip()) == {"-"}
    ):
      pular_separador = False
      continue
    pular_separador = False
    corpo_linhas.append(linha)
  return "\n".join(corpo_linhas).strip()


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


def ultimo_log() -> tuple[str, str] | None:
  """Retorna (data/hora formatada, conteúdo) do log mais recente, ou
  None quando não há registro prévio."""
  arquivos = sorted(
      _PASTA_LOGS.glob("log_*.txt"), key=lambda p: p.stat().st_mtime
  ) if _PASTA_LOGS.is_dir() else []
  if not arquivos:
    return None

  mais_recente = arquivos[-1]
  stamp = datetime.fromtimestamp(
      mais_recente.stat().st_mtime
  ).strftime("%d/%m/%Y %H:%M:%S")
  try:
    conteudo = mais_recente.read_text(
        encoding="utf-8", errors="replace"
    ).strip()
  except OSError:
    conteudo = mais_recente.name
  return stamp, conteudo


def ultimo_resumo() -> str:
  """Data/hora e primeira linha útil do log mais recente, ou fallback."""
  registro = ultimo_log()
  if registro is None:
    return "Nenhum registro prévio"
  stamp, conteudo = registro
  linhas = [
      linha.strip()
      for linha in conteudo.splitlines()
      if linha.strip() and not linha.startswith("[")
  ]
  resumo = linhas[0][:80] if linhas else stamp
  return f"{stamp} — {resumo}"
