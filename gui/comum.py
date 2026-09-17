"""Utilitários compartilhados entre as abas da interface gráfica."""

import os
from pathlib import Path
import subprocess

import customtkinter as ctk

from core.binarios import obter_diretorio_input_output
from core.logger import salvar_log, ultimo_log


def abrir_pasta_ou_padrao(ultimo_destino, texto_entrada):
  """Abre a pasta de destino no Explorer. Ordem de resolução:
  1) último resultado gerado com sucesso; 2) caminho no campo de
  entrada; 3) pasta 'input-output' ao lado do app (fallback sempre
  disponível).
  """
  try:
    if ultimo_destino is not None:
      if ultimo_destino.is_file():
        subprocess.run(
            ["explorer", f'/select,"{ultimo_destino}"'],
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return
      if ultimo_destino.is_dir():
        os.startfile(ultimo_destino)
        return

    texto = (texto_entrada or "").strip()
    if texto:
      caminho = Path(texto)
      if caminho.is_file():
        os.startfile(caminho.parent)
        return
      if caminho.is_dir():
        os.startfile(caminho)
        return

    os.startfile(obter_diretorio_input_output())
  except Exception:
    try:
      os.startfile(obter_diretorio_input_output())
    except Exception:
      pass


def exibir_historico(caixa: ctk.CTkTextbox):
  """Renderiza no topo da caixa o conteúdo da última sessão salva."""
  registro = ultimo_log()
  if registro is None:
    caixa.insert(
        "end", ">>> Última execução: Nenhum registro prévio\n"
        f"{'-'*55}\n"
    )
    return
  stamp, conteudo = registro
  caixa.insert(
      "end",
      f"{'='*16} HISTÓRICO DA ÚLTIMA EXECUÇÃO {'='*16}\n"
      f"[Data/Hora: {stamp}]\n"
      f"{conteudo}\n"
      f"{'='*64}\n"
      "Pronto para nova operação.\n",
  )


def persistir_log(caixa: ctk.CTkTextbox, origem: str):
  try:
    salvar_log(caixa.get("1.0", "end").strip(), origem=origem)
  except OSError:
    pass
