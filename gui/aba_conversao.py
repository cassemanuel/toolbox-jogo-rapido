"""Aba de conversão direta de formato, sem teto de tamanho."""

from pathlib import Path
import threading
from tkinter import filedialog, messagebox
from typing import Any, Callable

import customtkinter as ctk

from core.binarios import gerar_destino_unico
from core.imagem import FORMATOS_CONVERSAO, converter_imagem
from core.video import converter_midia
from gui.comum import (
    abrir_pasta_ou_padrao,
    exibir_historico,
    persistir_log,
)

_FORMATOS_VIDEO_AUDIO = [
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".mp3", ".wav", ".aac",
]
_FORMATOS_IMAGEM_CONVERSAO = list(FORMATOS_CONVERSAO.keys())
_EXT_MIDIA_ENTRADA = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm",
    ".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a",
}
_EXT_IMAGEM_ENTRADA = set(FORMATOS_CONVERSAO.keys())


class AbaConversao(ctk.CTkFrame):

  def __init__(
      self,
      master,
      post_ui: Callable[[Callable, Any], None],
  ):
    super().__init__(master, fg_color="transparent")
    self.pack(fill="both", expand=True)
    self._post_ui = post_ui

    self._worker: threading.Thread | None = None
    self._ultimo_destino: Path | None = None

    self._montar_layout()
    exibir_historico(self.log_conv)

  @property
  def worker(self) -> threading.Thread | None:
    return self._worker

  def _montar_layout(self):
    card = ctk.CTkFrame(
        self, corner_radius=8, border_width=1, border_color="#3a3a3a"
    )
    card.pack(fill="x", padx=15, pady=10)

    ctk.CTkLabel(
        card,
        text="Tipo de Conversão:",
        font=ctk.CTkFont(weight="bold"),
    ).grid(row=0, column=0, padx=12, pady=10, sticky="w")

    self.conv_tipo = ctk.CTkSegmentedButton(
        card,
        values=["Vídeo / Áudio", "Imagem"],
        command=self._conv_tipo_changed,
    )
    self.conv_tipo.set("Vídeo / Áudio")
    self.conv_tipo.grid(row=0, column=1, padx=8, pady=10, sticky="w")

    ctk.CTkLabel(
        card,
        text="Escopo:",
        font=ctk.CTkFont(weight="bold"),
    ).grid(row=0, column=2, padx=(12, 4), pady=10, sticky="w")

    self.conv_modo = ctk.CTkSegmentedButton(
        card,
        values=["Arquivo Único", "Pasta em Lote"],
        command=self._conv_modo_changed,
    )
    self.conv_modo.set("Arquivo Único")
    self.conv_modo.grid(row=0, column=3, padx=8, pady=10, sticky="w")

    ctk.CTkLabel(
        card,
        text="Origem:",
        font=ctk.CTkFont(weight="bold"),
    ).grid(row=1, column=0, padx=12, pady=10, sticky="w")

    self.conv_file = ctk.StringVar()
    ctk.CTkEntry(
        card,
        textvariable=self.conv_file,
        placeholder_text="Selecione o arquivo a converter...",
    ).grid(row=1, column=1, columnspan=2, padx=8, pady=10, sticky="ew")

    self.btn_conv_busca = ctk.CTkButton(
        card, text="Buscar Arquivo", width=110, command=self._conv_select
    )
    self.btn_conv_busca.grid(row=1, column=3, padx=12, pady=10)

    f_sub = ctk.CTkFrame(card, fg_color="transparent")
    f_sub.grid(
        row=2, column=0, columnspan=4, padx=12, pady=(0, 10), sticky="w"
    )

    ctk.CTkLabel(f_sub, text="Formato de Destino:").pack(side="left")
    self.conv_formato = ctk.CTkComboBox(
        f_sub, values=_FORMATOS_VIDEO_AUDIO, width=100
    )
    self.conv_formato.set(_FORMATOS_VIDEO_AUDIO[0])
    self.conv_formato.pack(side="left", padx=6)

    card.grid_columnconfigure(1, weight=1)

    self.btn_conv_start = ctk.CTkButton(
        self,
        text="Iniciar Conversão",
        height=36,
        font=ctk.CTkFont(weight="bold"),
        fg_color="#1f6aa5",
        hover_color="#144870",
        command=self._conv_start,
    )
    self.btn_conv_start.pack(fill="x", padx=15, pady=5)

    self.prog_conv = ctk.CTkProgressBar(self, corner_radius=8)
    self.prog_conv.set(0)
    self.prog_conv.pack(fill="x", padx=15, pady=(0, 5))

    self.btn_conv_abrir = ctk.CTkButton(
        self,
        text="Abrir Pasta de Destino",
        width=160,
        command=lambda: abrir_pasta_ou_padrao(
            self._ultimo_destino, self.conv_file.get()
        ),
    )
    self.btn_conv_abrir.pack(anchor="e", padx=15, pady=(0, 5))

    self.log_conv = ctk.CTkTextbox(
        self,
        font=ctk.CTkFont(family="Consolas", size=11),
        corner_radius=8,
    )
    self.log_conv.pack(fill="both", expand=True, padx=15, pady=10)

  def _conv_tipo_changed(self, tipo):
    valores = (
        _FORMATOS_IMAGEM_CONVERSAO
        if tipo == "Imagem"
        else _FORMATOS_VIDEO_AUDIO
    )
    self.conv_formato.configure(values=valores)
    self.conv_formato.set(valores[0])

  def _conv_modo_changed(self, modo):
    em_lote = modo == "Pasta em Lote"
    self.btn_conv_busca.configure(
        text="Buscar Pasta" if em_lote else "Buscar Arquivo"
    )
    self.conv_file.set("")

  def _conv_select(self):
    if self.conv_modo.get() == "Pasta em Lote":
      caminho = filedialog.askdirectory()
    elif self.conv_tipo.get() == "Imagem":
      caminho = filedialog.askopenfilename(
          filetypes=[
              ("Imagens", "*.jpg *.jpeg *.png *.webp *.bmp *.ico")
          ]
      )
    else:
      caminho = filedialog.askopenfilename(
          filetypes=[
              (
                  "Mídia",
                  "*.mp4 *.webm *.mkv *.mov *.avi *.mp3 *.wav *.aac"
                  " *.flac *.ogg",
              )
          ]
      )
    if caminho:
      self.conv_file.set(caminho)

  def _conv_start(self):
    origem = Path(self.conv_file.get().strip())
    em_lote = self.conv_modo.get() == "Pasta em Lote"
    ext_destino = self.conv_formato.get()
    tipo = self.conv_tipo.get()

    self.prog_conv.set(0)
    self.btn_conv_start.configure(state="disabled", text="Convertendo...")
    self.log_conv.delete("1.0", "end")

    if em_lote:
      if not origem.is_dir():
        messagebox.showerror("Erro", "Pasta de origem não encontrada.")
        self.btn_conv_start.configure(
            state="normal", text="Iniciar Conversão"
        )
        return
      extensoes = (
          _EXT_IMAGEM_ENTRADA if tipo == "Imagem" else _EXT_MIDIA_ENTRADA
      )
      arquivos = sorted(
          p for p in origem.iterdir()
          if p.is_file() and p.suffix.lower() in extensoes
          and p.suffix.lower() != ext_destino.lower()
      )
      if not arquivos:
        messagebox.showerror(
            "Erro", "Nenhum arquivo compatível encontrado na pasta."
        )
        self.btn_conv_start.configure(
            state="normal", text="Iniciar Conversão"
        )
        return
      pasta_saida = origem / "convertidos"
      pasta_saida.mkdir(parents=True, exist_ok=True)
      self.log_conv.insert(
          "end",
          f">>> Lote: {len(arquivos)} arquivo(s) -> {pasta_saida}\n",
      )
      self.log_conv.see("end")

      def worker_lote():
        try:
          sucessos = 0
          for i, arq in enumerate(arquivos, 1):
            destino = gerar_destino_unico(
                pasta_saida, arq.stem, "convertido", ext_destino
            )
            self._post_ui(
                self._conv_log_lote, i, len(arquivos), arq.name
            )
            if tipo == "Imagem":
              res = converter_imagem(arq, destino)
            else:
              res = converter_midia(
                  arq, destino, audio_bitrate_kbps=192
              )
            self._post_ui(self._conv_item_lote, res)
            if res.sucesso:
              sucessos += 1
            self._post_ui(
                self._conv_progresso, i / len(arquivos) * 100.0
            )
          self._post_ui(
              self._conv_fim_lote, len(arquivos), sucessos, pasta_saida
          )
        except Exception as e:
          self._post_ui(self._conv_erro, e)

      self._worker = threading.Thread(
          target=worker_lote, daemon=True
      )
      self._worker.start()
      return

    if not origem.is_file():
      messagebox.showerror("Erro", "Arquivo de origem não encontrado.")
      self.btn_conv_start.configure(
          state="normal", text="Iniciar Conversão"
      )
      return

    destino = gerar_destino_unico(
        origem.parent, origem.stem, "convertido", ext_destino
    )
    self.log_conv.insert(
        "end", f">>> Convertendo: {origem.name} -> {destino.name}\n"
    )
    self.log_conv.see("end")

    def worker():
      try:
        if tipo == "Imagem":
          res = converter_imagem(origem, destino)
          self._post_ui(self._conv_progresso, 100.0)
        else:
          res = converter_midia(
              origem,
              destino,
              audio_bitrate_kbps=192,
              progress_hook=lambda pct: self._post_ui(
                  self._conv_progresso, pct
              ),
          )
        self._post_ui(self._conv_concluir, res)
      except Exception as e:
        self._post_ui(self._conv_erro, e)

    self._worker = threading.Thread(target=worker, daemon=True)
    self._worker.start()

  def _conv_log_lote(self, indice, total, nome):
    self.log_conv.insert(
        "end", f"Processando {indice}/{total}: {nome}...\n"
    )
    self.log_conv.see("end")

  def _conv_item_lote(self, res):
    if res.sucesso:
      final_kb = res.tamanho_final_bytes / 1024
      self.log_conv.insert(
          "end",
          f"   [OK] {res.caminho_destino.name} ({final_kb:.1f} KB)\n",
      )
    else:
      self.log_conv.insert(
          "end",
          f"   [ERRO] {res.caminho_origem.name}: {res.mensagem_erro}\n",
      )
    self.log_conv.see("end")

  def _conv_fim_lote(self, total, sucessos, pasta_saida):
    self.log_conv.insert(
        "end",
        f"\n{'='*55}\n Lote concluído: {sucessos}/{total} convertidos\n"
        f"{'='*55}\n",
    )
    if sucessos > 0:
      self._ultimo_destino = pasta_saida
    self.log_conv.see("end")
    persistir_log(self.log_conv, "conversao")
    self.btn_conv_start.configure(state="normal", text="Iniciar Conversão")

  def _conv_progresso(self, pct):
    self.prog_conv.set(min(100.0, max(0.0, pct)) / 100.0)

  def _conv_concluir(self, res):
    if res.sucesso:
      orig_kb = res.tamanho_original_bytes / 1024
      final_kb = res.tamanho_final_bytes / 1024
      self.log_conv.insert(
          "end",
          f"[OK] {res.caminho_destino.name}\n"
          f"     Tamanho : {orig_kb:.1f} KB -> {final_kb:.1f} KB\n"
          f"     Duração : {res.tempo_processamento_s:.3f} s\n{'-'*55}\n",
      )
      self._ultimo_destino = res.caminho_destino
    else:
      self.prog_conv.set(0)
      self.log_conv.insert(
          "end", f"[FALHA] {res.mensagem_erro}\n{'-'*55}\n"
      )
    self.log_conv.see("end")
    persistir_log(self.log_conv, "conversao")
    self.btn_conv_start.configure(state="normal", text="Iniciar Conversão")

  def _conv_erro(self, erro):
    self.prog_conv.set(0)
    self.log_conv.insert(
        "end", f"\n[FALHA INESPERADA] {erro}\n{'-'*55}\n"
    )
    self.log_conv.see("end")
    persistir_log(self.log_conv, "conversao")
    self.btn_conv_start.configure(state="normal", text="Iniciar Conversão")
