"""Aba de otimização de imagens (arquivo único ou lote em pasta)."""

from pathlib import Path
import threading
import time
from tkinter import filedialog, messagebox
from typing import Any, Callable

import customtkinter as ctk
from PIL import Image

from core.binarios import gerar_destino_unico
from core.imagem import FORMATOS_SAIDA, otimizar_imagem, otimizar_lote
from gui.comum import (
    abrir_pasta_ou_padrao,
    exibir_historico,
    persistir_log,
)


class AbaImagem(ctk.CTkFrame):

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
    exibir_historico(self.log_i)

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
        text="Entrada (Arquivo/Pasta):",
        font=ctk.CTkFont(weight="bold"),
    ).grid(row=0, column=0, padx=12, pady=10, sticky="w")

    self.i_path = ctk.StringVar()
    ctk.CTkEntry(
        card,
        textvariable=self.i_path,
        placeholder_text="Selecione um arquivo de imagem ou diretório...",
    ).grid(row=0, column=1, padx=8, pady=10, sticky="ew")

    self.i_modo = ctk.CTkSegmentedButton(
        card,
        values=["Arquivo Único", "Lote de Pasta"],
        command=self._i_modo_changed,
    )
    self.i_modo.set("Arquivo Único")
    self.i_modo.grid(row=0, column=2, padx=8, pady=10)

    self.btn_i_buscar = ctk.CTkButton(
        card, text="Buscar Arquivo", width=110, command=self._i_buscar
    )
    self.btn_i_buscar.grid(row=0, column=3, padx=8, pady=10)

    f_sub = ctk.CTkFrame(card, fg_color="transparent")
    f_sub.grid(
        row=1, column=0, columnspan=4, padx=12, pady=(0, 10), sticky="w"
    )

    ctk.CTkLabel(f_sub, text="Dimensão Máxima (px):").pack(side="left")
    self.i_max = ctk.CTkEntry(f_sub, width=70)
    self.i_max.insert(0, "1920")
    self.i_max.pack(side="left", padx=(6, 20))

    ctk.CTkLabel(f_sub, text="Qualidade (1-100):").pack(side="left")
    self.i_qual = ctk.CTkEntry(f_sub, width=60)
    self.i_qual.insert(0, "80")
    self.i_qual.pack(side="left", padx=(6, 20))

    ctk.CTkLabel(f_sub, text="Formato:").pack(side="left")
    self.i_fmt = ctk.CTkSegmentedButton(
        f_sub, values=list(FORMATOS_SAIDA.keys())
    )
    self.i_fmt.set("JPEG")
    self.i_fmt.pack(side="left", padx=6)

    self.lbl_estimativa = ctk.CTkLabel(
        card,
        text="Tamanho estimado: —",
        font=ctk.CTkFont(size=11),
        text_color="#8a8a8a",
    )
    self.lbl_estimativa.grid(
        row=2, column=0, columnspan=4, padx=12, pady=(0, 8),
        sticky="w",
    )

    self.i_path.trace_add("write", lambda *_: self._atualizar_estimativa())
    self.i_max.bind("<KeyRelease>", lambda _e: self._atualizar_estimativa())
    self.i_qual.bind("<KeyRelease>", lambda _e: self._atualizar_estimativa())

    card.grid_columnconfigure(1, weight=1)

    self.btn_i_start = ctk.CTkButton(
        self,
        text="Iniciar Otimização de Imagens",
        height=36,
        font=ctk.CTkFont(weight="bold"),
        fg_color="#1f6aa5",
        hover_color="#144870",
        command=self._i_start,
    )
    self.btn_i_start.pack(fill="x", padx=15, pady=5)

    self.btn_i_abrir = ctk.CTkButton(
        self,
        text="Abrir Pasta de Destino",
        width=160,
        command=lambda: abrir_pasta_ou_padrao(
            self._ultimo_destino, self.i_path.get()
        ),
    )
    self.btn_i_abrir.pack(anchor="e", padx=15, pady=(0, 5))

    self.log_i = ctk.CTkTextbox(
        self,
        font=ctk.CTkFont(family="Consolas", size=11),
        corner_radius=8,
    )
    self.log_i.pack(fill="both", expand=True, padx=15, pady=10)

  def _atualizar_estimativa(self):
    neutro = "Tamanho estimado: —"
    caminho = Path(self.i_path.get().strip())
    if self.i_modo.get() != "Arquivo Único" or not caminho.is_file():
      self.lbl_estimativa.configure(text=neutro)
      return
    try:
      max_dim = int(self.i_max.get().strip() or 1920)
      qualidade = int(self.i_qual.get().strip() or 80)
      if max_dim <= 0 or not 1 <= qualidade <= 100:
        raise ValueError
    except ValueError:
      self.lbl_estimativa.configure(text=neutro)
      return
    try:
      with Image.open(caminho) as img:
        w, h = img.size
    except Exception:
      self.lbl_estimativa.configure(text=neutro)
      return

    if max(w, h) > max_dim:
      escala = max_dim / max(w, h)
      w_f, h_f = int(w * escala), int(h * escala)
    else:
      w_f, h_f = w, h

    bpp = 0.5 + (qualidade / 100.0) * 1.5
    bytes_est = (w_f * h_f * bpp) / 8
    orig_kb = caminho.stat().st_size / 1024
    self.lbl_estimativa.configure(
        text=f"Tamanho estimado: ~{bytes_est / 1024:.0f} KB"
        f" ({w_f}x{h_f}px | original: {orig_kb:.0f} KB)"
    )

  def _i_modo_changed(self, modo):
    self.btn_i_buscar.configure(
        text="Buscar Pasta" if modo == "Lote de Pasta" else "Buscar Arquivo"
    )
    self._atualizar_estimativa()

  def _i_buscar(self):
    if self.i_modo.get() == "Lote de Pasta":
      self._i_select_dir()
    else:
      self._i_select_file()

  def _i_select_file(self):
    caminho = filedialog.askopenfilename(
        filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp")]
    )
    if caminho:
      self.i_path.set(caminho)

  def _i_select_dir(self):
    caminho = filedialog.askdirectory()
    if caminho:
      self.i_path.set(caminho)

  def _i_start(self):
    origem = Path(self.i_path.get().strip())
    if not origem.exists():
      messagebox.showerror(
          "Erro", "Caminho de imagem ou diretório inexistente."
      )
      return

    try:
      max_dim = int(self.i_max.get().strip() or 1920)
      qualidade = int(self.i_qual.get().strip() or 80)
    except ValueError:
      messagebox.showerror(
          "Erro", "Dimensão ou qualidade deve ser um número inteiro."
      )
      return

    if not 1 <= qualidade <= 100 or max_dim <= 0:
      messagebox.showerror(
          "Erro", "Qualidade deve estar entre 1-100 e a dimensão > 0."
      )
      return

    formato = self.i_fmt.get()
    ext_saida = FORMATOS_SAIDA[formato]

    self.btn_i_start.configure(
        state="disabled", text="Processando Imagens..."
    )

    self.log_i.insert(
        "end", "\n================ NOVA EXECUÇÃO ================\n"
    )

    if origem.is_file():
      destino = gerar_destino_unico(
          origem.parent, origem.stem, "otimizada", ext_saida
      )
      self.log_i.insert(
          "end",
          f">>> Otimizando arquivo individual: {origem.name}"
          f" | Formato: {formato}\n",
      )
      self.log_i.see("end")

      def worker_arquivo():
        try:
          res = otimizar_imagem(
              origem, destino, max_dim, qualidade, formato_saida=formato
          )
          self._post_ui(self._i_concluir_arquivo, res)
        except Exception as e:
          self._post_ui(self._i_erro, e)

      self._worker = threading.Thread(target=worker_arquivo, daemon=True)
      self._worker.start()
      return

    destino = origem / "otimizadas"
    self.log_i.insert(
        "end",
        f">>> Processando lote em: {origem}\n>>> Saída: {destino}\n\n",
    )
    self.log_i.see("end")

    def worker_lote():
      total = 0
      sucessos = 0
      bytes_antes = 0
      bytes_depois = 0
      t_inicio = time.perf_counter()
      try:
        for res in otimizar_lote(
            origem, destino, max_dim, qualidade, formato_saida=formato
        ):
          total += 1
          if res.sucesso:
            sucessos += 1
            bytes_antes += res.tamanho_original_bytes
            bytes_depois += res.tamanho_final_bytes
          self._post_ui(self._i_log_item, res, sucessos)
        tempo = time.perf_counter() - t_inicio
        self._post_ui(
            self._i_concluir_lote,
            total,
            sucessos,
            bytes_antes,
            bytes_depois,
            tempo,
            destino,
        )
      except Exception as e:
        self._post_ui(self._i_erro, e)

    self._worker = threading.Thread(target=worker_lote, daemon=True)
    self._worker.start()

  def _i_concluir_arquivo(self, res):
    dur = res.tempo_processamento_s
    if res.sucesso:
      orig_kb = res.tamanho_original_bytes / 1024
      final_kb = res.tamanho_final_bytes / 1024
      self.log_i.insert(
          "end",
          f"[OK] {res.caminho_destino.name}\n"
          f"     Tamanho : {orig_kb:.1f} KB -> {final_kb:.1f} KB\n"
          f"     Duração : {dur:.3f} s\n{'-'*55}\n",
      )
    else:
      self.log_i.insert(
          "end",
          f"[FALHA] {res.mensagem_erro} ({dur:.3f} s)\n{'-'*55}\n",
      )
    if res.sucesso:
      self._ultimo_destino = res.caminho_destino
    self.log_i.see("end")
    persistir_log(self.log_i, "imagem")
    self.btn_i_start.configure(
        state="normal", text="Iniciar Otimização de Imagens"
    )

  def _i_log_item(self, res, sucessos):
    if res.sucesso:
      final_kb = res.tamanho_final_bytes / 1024
      self.log_i.insert(
          "end",
          f" [{sucessos:02d}] {res.caminho_origem.name:<30} ->"
          f" {final_kb:7.1f} KB  ({res.tempo_processamento_s:.3f} s)\n",
      )
    else:
      self.log_i.insert(
          "end",
          f" [ERRO] {res.caminho_origem.name}: {res.mensagem_erro}\n",
      )
    self.log_i.see("end")

  def _i_concluir_lote(
      self, total, sucessos, bytes_antes, bytes_depois, tempo, destino
  ):
    economia_mb = (bytes_antes - bytes_depois) / (1024 * 1024)
    self.log_i.insert(
        "end",
        f"\n{'='*55}\n"
        f" Concluídas          : {sucessos}/{total} imagens\n"
        f" Tempo Acumulado     : {tempo:.2f} s\n"
        f" Espaço Economizado  : {economia_mb:.2f} MB\n"
        f"{'='*55}\n",
    )
    if sucessos > 0:
      self._ultimo_destino = destino
    self.log_i.see("end")
    persistir_log(self.log_i, "imagem")
    self.btn_i_start.configure(
        state="normal", text="Iniciar Otimização de Imagens"
    )

  def _i_erro(self, erro):
    self.log_i.insert("end", f"\n[FALHA INESPERADA] {erro}\n{'-'*55}\n")
    self.log_i.see("end")
    persistir_log(self.log_i, "imagem")
    self.btn_i_start.configure(
        state="normal", text="Iniciar Otimização de Imagens"
    )
