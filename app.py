"""Interface Gráfica Desktop Moderna (CustomTkinter)

Container principal: janela, Tabview, fila de eventos thread-safe e
protocolo de encerramento. As regras de cada aba vivem no pacote gui/.
"""

import queue
import random
import customtkinter as ctk

from core.calculadora import ARTE_VASCO
from core.video import cancelar_processos_ativos
from gui.aba_calculadora import AbaCalculadora
from gui.aba_conversao import AbaConversao
from gui.aba_imagem import AbaImagem
from gui.aba_pdf import AbaPdf
from gui.aba_video import AbaVideo

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):

  def __init__(self):
    super().__init__()
    self.title("Media Automation Toolkit")
    self.geometry("820x650")
    self.minsize(760, 580)

    self.protocol("WM_DELETE_WINDOW", self._ao_fechar)

    self._fila_ui: queue.Queue = queue.Queue()
    self._modal_saida: ctk.CTkToplevel | None = None
    self._restante_saida = 0

    rodape = ctk.CTkFrame(self, fg_color="transparent", height=28)
    rodape.pack(fill="x", side="bottom", padx=20, pady=(0, 8))

    ctk.CTkLabel(
        rodape,
        text="Media Automation Toolkit v2.0 • 2021–2026 • Cássio Silva",
        font=ctk.CTkFont(size=11),
        text_color="#6e6e6e",
    ).pack(side="left")

    ctk.CTkButton(
        rodape,
        text="[ Sobre / História ]",
        width=120,
        height=22,
        font=ctk.CTkFont(size=11),
        fg_color="transparent",
        hover_color="#2b2b2b",
        text_color="#4a9eff",
        command=self._abrir_sobre,
    ).pack(side="right")

    self.tabview = ctk.CTkTabview(self, corner_radius=10)
    self.tabview.pack(fill="both", expand=True, padx=20, pady=15)

    self.abas = [
        AbaVideo(
            self.tabview.add("Compressão de Vídeo"), self._post_ui
        ),
        AbaImagem(
            self.tabview.add("Otimização de Imagens"), self._post_ui
        ),
        AbaConversao(
            self.tabview.add("Conversão de Mídia"), self._post_ui
        ),
        AbaPdf(
            self.tabview.add("Manipulação de PDFs"), self._post_ui
        ),
        AbaCalculadora(
            self.tabview.add("Calculadora de Tempo"), self._post_ui
        ),
    ]

    self.after(75, self._drenar_fila_ui)

  def _abrir_sobre(self):
    modal = ctk.CTkToplevel(self)
    modal.title("Sobre — Media Automation Toolkit")
    modal.geometry("480x320")
    modal.resizable(False, False)
    modal.attributes("-topmost", True)

    ctk.CTkLabel(
        modal,
        text="Media Automation Toolkit v2.0",
        font=ctk.CTkFont(size=14, weight="bold"),
    ).pack(pady=(15, 5))

    texto = (
        "Projeto pessoal concebido em 2021 durante a pandemia como um "
        "utilitário simples em C (programa.c) para cálculos de aceleração "
        "e tempo de vídeo. Evoluiu ao longo dos anos para suprir gargalos "
        "de compressão com teto estrito, otimização de imagens em lote, "
        "manipulação de documentos PDF e conversão multimídia multiformato."
        "\n\nÚltima atualização: Versão 2.0 (17/09/2026)."
    )
    box = ctk.CTkTextbox(
        modal, wrap="word", font=ctk.CTkFont(size=12), height=180
    )
    box.pack(fill="both", expand=True, padx=15, pady=10)
    box.insert("1.0", texto)
    box.configure(state="disabled")

    ctk.CTkButton(
        modal, text="Fechar", width=100, command=modal.destroy
    ).pack(pady=(0, 12))

  def _post_ui(self, fn, *args):
    self._fila_ui.put((fn, args))

  def _drenar_fila_ui(self):
    try:
      while True:
        fn, args = self._fila_ui.get_nowait()
        try:
          fn(*args)
        except Exception:
          pass
    except queue.Empty:
      pass
    self.after(75, self._drenar_fila_ui)

  def _ao_fechar(self):
    cancelar_processos_ativos()
    for aba in self.abas:
      worker = getattr(aba, "worker", None)
      if worker and worker.is_alive():
        worker.join(timeout=3.0)

    if random.random() >= 0.5:
      self.destroy()
      return

    modal = ctk.CTkToplevel(self)
    modal.title("CRVG - Finalizando")
    modal.geometry("400x460")
    modal.resizable(False, False)
    modal.attributes("-topmost", True)
    modal.protocol("WM_DELETE_WINDOW", self._finalizar)
    self._modal_saida = modal
    self._restante_saida = 2

    ctk.CTkLabel(
        modal,
        text="VASCO DA GAMA",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color="#DC143C",
    ).pack(pady=(12, 0))

    textbox = ctk.CTkTextbox(
        modal,
        font=ctk.CTkFont(family="Courier New", size=10, weight="bold"),
    )
    textbox.pack(expand=True, fill="both", padx=15, pady=10)
    textbox.insert("1.0", ARTE_VASCO)
    textbox.configure(state="disabled")

    self._lbl_timer = ctk.CTkLabel(
        modal,
        text=f"Encerrando em {self._restante_saida}s...",
        font=ctk.CTkFont(size=11),
        text_color="#888888",
    )
    self._lbl_timer.pack(pady=(0, 4))

    ctk.CTkButton(
        modal,
        text="Encerrar Aplicação",
        fg_color="#8B0000",
        hover_color="#550000",
        command=self._finalizar,
    ).pack(pady=(0, 15))

    modal.after(1000, self._tick_saida)

  def _tick_saida(self):
    if self._modal_saida is None:
      return
    self._restante_saida -= 1
    if self._restante_saida <= 0:
      self._finalizar()
      return
    try:
      self._lbl_timer.configure(
          text=f"Encerrando em {self._restante_saida}s..."
      )
      self._modal_saida.after(1000, self._tick_saida)
    except Exception:
      pass

  def _finalizar(self):
    self._modal_saida = None
    self.destroy()


if __name__ == "__main__":
  app = App()
  app.mainloop()
