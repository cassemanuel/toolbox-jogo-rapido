"""Interface Gráfica Desktop Moderna (CustomTkinter)

Container principal: janela, sidebar de navegação, área de conteúdo
com telas empilhadas (tkraise), fila de eventos thread-safe e
protocolo de encerramento. As regras de cada tela vivem no pacote gui/.
"""

import queue
import random
import customtkinter as ctk

from core.calculadora import ARTE_VASCO
from core.video import cancelar_processos_ativos
from gui.aba_calculadora import AbaCalculadora
from gui.aba_energia import AbaEnergia
from gui.aba_pdf import AbaPdf
from gui.tela_home import TelaHome
from gui.tela_imagem import TelaImagem
from gui.tela_video import TelaVideo

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

_NAV = [
    ("home", "🏠  Início"),
    ("videos", "🎬  Vídeos"),
    ("imagens", "🖼️  Imagens"),
    ("pdf", "📑  Documentos PDF"),
    ("calc", "⏱️  Calculadora"),
    ("energia", "⚡  Energia / Timer"),
]


class App(ctk.CTk):

  def __init__(self):
    super().__init__()
    self.title("Media Automation Toolkit")
    self.geometry("1040x680")
    self.minsize(960, 600)

    self.protocol("WM_DELETE_WINDOW", self._ao_fechar)

    self._fila_ui: queue.Queue = queue.Queue()
    self._modal_saida: ctk.CTkToplevel | None = None
    self._restante_saida = 0
    self._nav_btns: dict[str, ctk.CTkButton] = {}

    self.grid_columnconfigure(1, weight=1)
    self.grid_rowconfigure(0, weight=1)

    self._montar_sidebar()
    self._montar_conteudo()
    self._navegar("home")

    self.after(75, self._drenar_fila_ui)

  # ---------------- Estrutura visual ----------------

  def _montar_sidebar(self):
    sidebar = ctk.CTkFrame(
        self, width=200, corner_radius=0, fg_color="#161616"
    )
    sidebar.grid(row=0, column=0, sticky="nsew")
    sidebar.grid_propagate(False)

    ctk.CTkLabel(
        sidebar,
        text="Media Toolkit",
        font=ctk.CTkFont(size=16, weight="bold"),
    ).pack(pady=(20, 2))
    ctk.CTkLabel(
        sidebar,
        text="v2.0",
        font=ctk.CTkFont(size=11, weight="bold"),
        text_color="#4a9eff",
    ).pack(pady=(0, 18))

    for chave, rotulo in _NAV:
      btn = ctk.CTkButton(
          sidebar,
          text=rotulo,
          anchor="w",
          height=38,
          corner_radius=8,
          fg_color="transparent",
          hover_color="#2b2b2b",
          text_color="#d4d4d4",
          command=lambda c=chave: self._navegar(c),
      )
      btn.pack(fill="x", padx=10, pady=3)
      self._nav_btns[chave] = btn

    ctk.CTkButton(
        sidebar,
        text="[ Sobre / História ]",
        height=24,
        font=ctk.CTkFont(size=11),
        fg_color="transparent",
        hover_color="#2b2b2b",
        text_color="#4a9eff",
        command=self._abrir_sobre,
    ).pack(side="bottom", pady=12)

  def _montar_conteudo(self):
    self.conteudo = ctk.CTkFrame(self, fg_color="transparent")
    self.conteudo.grid(row=0, column=1, sticky="nsew")

    self.telas = {
        "home": TelaHome(self.conteudo, self._navegar),
        "videos": TelaVideo(self.conteudo, self._post_ui),
        "imagens": TelaImagem(self.conteudo, self._post_ui),
        "pdf": AbaPdf(self.conteudo, self._post_ui),
        "calc": AbaCalculadora(self.conteudo, self._post_ui),
        "energia": AbaEnergia(self.conteudo, self._post_ui),
    }

  def _navegar(self, chave: str):
    for tela in self.telas.values():
      tela.pack_forget()
    self.telas[chave].pack(fill="both", expand=True)
    for k, btn in self._nav_btns.items():
      btn.configure(
          fg_color="#1f6aa5" if k == chave else "transparent",
          text_color="#ffffff" if k == chave else "#d4d4d4",
      )

  # ---------------- Infraestrutura ----------------

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
    for tela in self.telas.values():
      cancel_event = getattr(tela, "cancel_event", None)
      if cancel_event is not None:
        cancel_event.set()
      workers = getattr(
          tela, "workers", [getattr(tela, "worker", None)]
      )
      for worker in workers:
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
