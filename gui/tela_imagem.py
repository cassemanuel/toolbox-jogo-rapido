"""Tela de Imagens: otimização e conversão de fotos agrupadas."""

import threading
from typing import Any, Callable

import customtkinter as ctk

from gui.aba_conversao import AbaConversao
from gui.aba_imagem import AbaImagem

_MODOS = ["Otimização", "Conversão"]


class TelaImagem(ctk.CTkFrame):

  def __init__(
      self,
      master,
      post_ui: Callable[[Callable, Any], None],
  ):
    super().__init__(master, fg_color="transparent")
    self._post_ui = post_ui

    self.modo = ctk.CTkSegmentedButton(
        self, values=_MODOS, command=self._modo_changed
    )
    self.modo.set(_MODOS[0])
    self.modo.pack(fill="x", padx=15, pady=(12, 0))

    self.container = ctk.CTkFrame(self, fg_color="transparent")
    self.container.pack(fill="both", expand=True)

    self.aba_otimizacao = AbaImagem(self.container, post_ui)
    self.aba_conversao = AbaConversao(
        self.container, post_ui, tipo_fixo="Imagem"
    )
    self.aba_conversao.pack_forget()

  @property
  def worker(self) -> threading.Thread | None:
    for aba in (self.aba_otimizacao, self.aba_conversao):
      if aba.worker and aba.worker.is_alive():
        return aba.worker
    return None

  @property
  def workers(self):
    return [self.aba_otimizacao.worker, self.aba_conversao.worker]

  def _modo_changed(self, modo):
    if modo == _MODOS[0]:
      self.aba_conversao.pack_forget()
      self.aba_otimizacao.pack(fill="both", expand=True)
    else:
      self.aba_otimizacao.pack_forget()
      self.aba_conversao.pack(fill="both", expand=True)
