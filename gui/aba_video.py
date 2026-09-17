"""Aba de compressão de vídeo com teto de tamanho alvo."""

from pathlib import Path
import threading
import time
from tkinter import filedialog, messagebox
from typing import Any, Callable

import customtkinter as ctk

from core.binarios import gerar_destino_unico
from core.video import comprimir_video
from gui.comum import (
    abrir_pasta_ou_padrao,
    exibir_historico,
    persistir_log,
)


class AbaVideo(ctk.CTkFrame):

  def __init__(
      self,
      master,
      post_ui: Callable[[Callable, Any], None],
  ):
    super().__init__(master, fg_color="transparent")
    self.pack(fill="both", expand=True)
    self._post_ui = post_ui

    self._worker: threading.Thread | None = None
    self._cancel_video = threading.Event()
    self._ultimo_destino: Path | None = None

    self._montar_layout()
    exibir_historico(self.log_v)

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
        text="Arquivo de Origem:",
        font=ctk.CTkFont(weight="bold"),
    ).grid(row=0, column=0, padx=12, pady=10, sticky="w")

    self.v_file = ctk.StringVar()
    ctk.CTkEntry(
        card,
        textvariable=self.v_file,
        placeholder_text="Caminho do arquivo de vídeo...",
    ).grid(row=0, column=1, padx=8, pady=10, sticky="ew")

    ctk.CTkButton(
        card,
        text="Buscar Vídeo",
        width=110,
        command=self._v_select,
    ).grid(row=0, column=2, padx=12, pady=10)

    f_sub = ctk.CTkFrame(card, fg_color="transparent")
    f_sub.grid(
        row=1, column=0, columnspan=3, padx=12, pady=(0, 10), sticky="w"
    )

    ctk.CTkLabel(f_sub, text="Tamanho Alvo:").pack(side="left")
    self.v_size = ctk.CTkEntry(f_sub, width=70)
    self.v_size.insert(0, "25.0")
    self.v_size.pack(side="left", padx=(6, 2))
    ctk.CTkLabel(f_sub, text="MB").pack(side="left", padx=(0, 20))

    ctk.CTkLabel(f_sub, text="Formato:").pack(side="left")
    self.v_format = ctk.CTkComboBox(
        f_sub,
        values=[".mp4", ".webm", ".mkv", ".mp3"],
        width=90,
        command=self._v_formato_changed,
    )
    self.v_format.set(".mp4")
    self.v_format.pack(side="left", padx=6)

    card.grid_columnconfigure(1, weight=1)

    self.btn_v_start = ctk.CTkButton(
        self,
        text="Iniciar Compressão de Vídeo",
        height=36,
        font=ctk.CTkFont(weight="bold"),
        fg_color="#1f6aa5",
        hover_color="#144870",
        command=self._v_start,
    )
    self.btn_v_start.pack(fill="x", padx=15, pady=5)

    self.prog_v = ctk.CTkProgressBar(self, corner_radius=8)
    self.prog_v.set(0)
    self.prog_v.pack(fill="x", padx=15, pady=(0, 5))

    self.btn_v_abrir = ctk.CTkButton(
        self,
        text="Abrir Pasta de Destino",
        width=160,
        command=lambda: abrir_pasta_ou_padrao(
            self._ultimo_destino, self.v_file.get()
        ),
    )
    self.btn_v_abrir.pack(anchor="e", padx=15, pady=(0, 5))

    self.log_v = ctk.CTkTextbox(
        self,
        font=ctk.CTkFont(family="Consolas", size=11),
        corner_radius=8,
    )
    self.log_v.pack(fill="both", expand=True, padx=15, pady=10)

  def _v_formato_changed(self, formato):
    somente_audio = formato == ".mp3"
    self.v_size.configure(
        state="disabled" if somente_audio else "normal"
    )

  def _v_select(self):
    caminho = filedialog.askopenfilename(
        filetypes=[("Arquivos de Vídeo", "*.mp4 *.webm *.mkv *.mov *.avi")]
    )
    if caminho:
      self.v_file.set(caminho)

  def _v_start(self):
    origem = Path(self.v_file.get().strip())
    if not origem.is_file():
      messagebox.showerror(
          "Erro", "Arquivo de vídeo de origem não encontrado."
      )
      return

    try:
      tamanho_alvo = float(self.v_size.get().strip() or 25.0)
    except ValueError:
      messagebox.showerror("Erro", "Valor do tamanho alvo inválido.")
      return

    ext = self.v_format.get()
    destino = gerar_destino_unico(
        origem.parent, origem.stem, "comprimido", ext
    )

    self._cancel_video.clear()
    self.log_v.delete("1.0", "end")
    self.prog_v.set(0)
    self.btn_v_start.configure(
        text="Cancelar Compressão",
        fg_color="#8B0000",
        hover_color="#550000",
        command=self._v_cancel,
    )
    self.log_v.insert(
        "end",
        f">>> Processando: {origem.name}\n"
        f">>> Destino: {destino.name} | Formato: {ext}\n",
    )
    self.log_v.see("end")

    def worker():
      try:
        t_inicio = time.perf_counter()
        res = comprimir_video(
            origem=origem,
            destino=destino,
            tamanho_alvo_mb=tamanho_alvo,
            audio_bitrate_kbps=96,
            progress_hook=lambda pct: self._post_ui(self._v_progresso, pct),
            cancel_event=self._cancel_video,
        )
        tempo = time.perf_counter() - t_inicio
        self._post_ui(self._v_concluir, res, tempo)
      except Exception as e:
        self._post_ui(self._v_erro, e)

    self._worker = threading.Thread(target=worker, daemon=True)
    self._worker.start()

  def _v_cancel(self):
    self._cancel_video.set()
    self.btn_v_start.configure(state="disabled", text="Cancelando...")

  def _v_progresso(self, pct):
    self.prog_v.set(min(100.0, max(0.0, pct)) / 100.0)

  def _v_restaurar_botao(self):
    self.btn_v_start.configure(
        state="normal",
        text="Iniciar Compressão de Vídeo",
        fg_color="#1f6aa5",
        hover_color="#144870",
        command=self._v_start,
    )

  def _v_concluir(self, res, tempo_cronometrado):
    tempo_exibicao = (
        res.tempo_processamento_s
        if res.tempo_processamento_s > 0
        else tempo_cronometrado
    )

    if res.sucesso:
      orig_mb = res.tamanho_original_bytes / (1024 * 1024)
      final_mb = res.tamanho_final_bytes / (1024 * 1024)
      reducao = ((orig_mb - final_mb) / orig_mb) * 100 if orig_mb else 0.0
      vel_rel = (
          res.duracao_segundos / tempo_exibicao if tempo_exibicao > 0 else 0.0
      )

      relatorio = (
          f"\n{'='*55}\n"
          " STATUS              : SUCESSO\n"
          f" TEMPO CRONOMETRADO  : {tempo_exibicao:.2f} s ({vel_rel:.2f}x"
          " tempo real)\n"
          f" TAMANHO ORIGINAL    : {orig_mb:.2f} MB\n"
          f" TAMANHO FINAL       : {final_mb:.2f} MB ({reducao:.1f}%"
          " reduzido)\n"
          f" TAXA DE BITS VÍDEO  : {res.bitrate_k} kbps\n"
          f" GPU DETECTADA       : {res.telemetria.modelo_gpu}\n"
          f" CARGA CPU (MÉD/PICO): {res.telemetria.cpu_media:.1f}% /"
          f" {res.telemetria.cpu_pico:.1f}%\n"
          f" CARGA GPU (MÉD/PICO): {res.telemetria.gpu_media:.1f}% /"
          f" {res.telemetria.gpu_pico:.1f}%\n"
          f" VRAM DE PICO        : {res.telemetria.vram_pico_mb:.1f} MB\n"
          f"{'='*55}\n"
      )
      self.log_v.insert("end", relatorio)
      self._ultimo_destino = res.caminho_destino
    else:
      self.log_v.insert(
          "end",
          f"\n[FALHA DE PROCESSAMENTO]\nTempo decorrido:"
          f" {tempo_exibicao:.2f} s\nMotivo: {res.mensagem_erro}\n{'-'*55}\n",
      )

    if res.aviso:
      self.log_v.insert("end", f" [AVISO] {res.aviso}\n{'-'*55}\n")

    if not res.sucesso:
      self.prog_v.set(0)
    self.log_v.see("end")
    persistir_log(self.log_v, "video")
    self._v_restaurar_botao()

  def _v_erro(self, erro):
    self.log_v.insert("end", f"\n[FALHA INESPERADA] {erro}\n{'-'*55}\n")
    self.log_v.see("end")
    self.prog_v.set(0)
    persistir_log(self.log_v, "video")
    self._v_restaurar_botao()
