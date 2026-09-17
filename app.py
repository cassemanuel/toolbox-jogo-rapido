"""Interface Gráfica Desktop Moderna (CustomTkinter)

Design estruturado em cards, grids alinhados e exibição de tempos de
processamento.
"""

import os
from pathlib import Path
import queue
import subprocess
import threading
import time
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core.calculadora import ARTE_VASCO, calcular_aceleracao_tempo
from core.imagem import FORMATOS_SAIDA, otimizar_imagem, otimizar_lote
from core.video import cancelar_processos_ativos, comprimir_video

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
    self._worker_video: threading.Thread | None = None
    self._worker_img: threading.Thread | None = None
    self._cancel_video = threading.Event()
    self._ultimo_destino_video: Path | None = None
    self._ultimo_destino_img: Path | None = None
    self._modal_saida: ctk.CTkToplevel | None = None
    self._restante_saida = 0

    self.tabview = ctk.CTkTabview(self, corner_radius=10)
    self.tabview.pack(fill="both", expand=True, padx=20, pady=15)

    self.tab_video = self.tabview.add("Compressão de Vídeo")
    self.tab_img = self.tabview.add("Otimização de Imagens")
    self.tab_calc = self.tabview.add("Calculadora de Tempo")

    self._setup_video_tab()
    self._setup_img_tab()
    self._setup_calc_tab()

    self.after(75, self._drenar_fila_ui)

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
    for worker in (self._worker_video, self._worker_img):
      if worker and worker.is_alive():
        worker.join(timeout=3.0)

    modal = ctk.CTkToplevel(self)
    modal.title("CRVG - Finalizando")
    modal.geometry("400x460")
    modal.resizable(False, False)
    modal.attributes("-topmost", True)
    modal.protocol("WM_DELETE_WINDOW", self._finalizar)
    self._modal_saida = modal
    self._restante_saida = 4

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

  def _abrir_destino(self, destino):
    if destino is None:
      return
    try:
      if destino.is_dir():
        os.startfile(destino)
      else:
        subprocess.run(
            ["explorer", f'/select,"{destino}"'],
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
      try:
        os.startfile(Path(destino).parent)
      except Exception:
        pass

  # -------------------------------------------------------------
  # ABA: VÍDEO
  # -------------------------------------------------------------
  def _setup_video_tab(self):
    card = ctk.CTkFrame(
        self.tab_video, corner_radius=8, border_width=1, border_color="#3a3a3a"
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
        self.tab_video,
        text="Iniciar Compressão de Vídeo",
        height=36,
        font=ctk.CTkFont(weight="bold"),
        fg_color="#1f6aa5",
        hover_color="#144870",
        command=self._v_start,
    )
    self.btn_v_start.pack(fill="x", padx=15, pady=5)

    self.prog_v = ctk.CTkProgressBar(self.tab_video, corner_radius=8)
    self.prog_v.set(0)
    self.prog_v.pack(fill="x", padx=15, pady=(0, 5))

    self.btn_v_abrir = ctk.CTkButton(
        self.tab_video,
        text="Abrir Pasta de Destino",
        width=160,
        state="disabled",
        command=lambda: self._abrir_destino(self._ultimo_destino_video),
    )
    self.btn_v_abrir.pack(anchor="e", padx=15, pady=(0, 5))

    self.log_v = ctk.CTkTextbox(
        self.tab_video,
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
    destino = origem.parent / f"{origem.stem}_comprimido{ext}"

    self._cancel_video.clear()
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

    self._worker_video = threading.Thread(target=worker, daemon=True)
    self._worker_video.start()

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
      self._ultimo_destino_video = res.caminho_destino
      self.btn_v_abrir.configure(state="normal")
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
    self._v_restaurar_botao()

  def _v_erro(self, erro):
    self.log_v.insert("end", f"\n[FALHA INESPERADA] {erro}\n{'-'*55}\n")
    self.log_v.see("end")
    self.prog_v.set(0)
    self._v_restaurar_botao()

  # -------------------------------------------------------------
  # ABA: IMAGEM
  # -------------------------------------------------------------
  def _setup_img_tab(self):
    card = ctk.CTkFrame(
        self.tab_img, corner_radius=8, border_width=1, border_color="#3a3a3a"
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
    self.i_fmt = ctk.CTkComboBox(
        f_sub, values=list(FORMATOS_SAIDA.keys()), width=90
    )
    self.i_fmt.set("JPEG")
    self.i_fmt.pack(side="left", padx=6)

    card.grid_columnconfigure(1, weight=1)

    self.btn_i_start = ctk.CTkButton(
        self.tab_img,
        text="Iniciar Otimização de Imagens",
        height=36,
        font=ctk.CTkFont(weight="bold"),
        fg_color="#1f6aa5",
        hover_color="#144870",
        command=self._i_start,
    )
    self.btn_i_start.pack(fill="x", padx=15, pady=5)

    self.btn_i_abrir = ctk.CTkButton(
        self.tab_img,
        text="Abrir Pasta de Destino",
        width=160,
        state="disabled",
        command=lambda: self._abrir_destino(self._ultimo_destino_img),
    )
    self.btn_i_abrir.pack(anchor="e", padx=15, pady=(0, 5))

    self.log_i = ctk.CTkTextbox(
        self.tab_img,
        font=ctk.CTkFont(family="Consolas", size=11),
        corner_radius=8,
    )
    self.log_i.pack(fill="both", expand=True, padx=15, pady=10)

  def _i_modo_changed(self, modo):
    self.btn_i_buscar.configure(
        text="Buscar Pasta" if modo == "Lote de Pasta" else "Buscar Arquivo"
    )

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

    if origem.is_file():
      destino = origem.parent / f"{origem.stem}_otimizada{ext_saida}"
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

      self._worker_img = threading.Thread(target=worker_arquivo, daemon=True)
      self._worker_img.start()
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

    self._worker_img = threading.Thread(target=worker_lote, daemon=True)
    self._worker_img.start()

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
      self._ultimo_destino_img = res.caminho_destino
      self.btn_i_abrir.configure(state="normal")
    self.log_i.see("end")
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
      self._ultimo_destino_img = destino
      self.btn_i_abrir.configure(state="normal")
    self.log_i.see("end")
    self.btn_i_start.configure(
        state="normal", text="Iniciar Otimização de Imagens"
    )

  def _i_erro(self, erro):
    self.log_i.insert("end", f"\n[FALHA INESPERADA] {erro}\n{'-'*55}\n")
    self.log_i.see("end")
    self.btn_i_start.configure(
        state="normal", text="Iniciar Otimização de Imagens"
    )

  # -------------------------------------------------------------
  # ABA: CALCULADORA
  # -------------------------------------------------------------
  def _setup_calc_tab(self):
    card = ctk.CTkFrame(
        self.tab_calc, corner_radius=8, border_width=1, border_color="#3a3a3a"
    )
    card.pack(fill="x", padx=15, pady=15)

    ctk.CTkLabel(
        card,
        text="Duração do Vídeo (Minutos):",
        font=ctk.CTkFont(weight="bold"),
    ).grid(row=0, column=0, padx=15, pady=10, sticky="w")
    self.c_min = ctk.CTkEntry(card, width=140)
    self.c_min.grid(row=0, column=1, padx=15, pady=10, sticky="w")

    ctk.CTkLabel(
        card,
        text="Fator de Velocidade (Playback):",
        font=ctk.CTkFont(weight="bold"),
    ).grid(row=1, column=0, padx=15, pady=10, sticky="w")
    self.c_vel = ctk.CTkEntry(card, width=140)
    self.c_vel.insert(0, "1.5")
    self.c_vel.grid(row=1, column=1, padx=15, pady=10, sticky="w")

    self.btn_calc = ctk.CTkButton(
        card,
        text="Calcular Aceleração",
        command=self._c_calc,
        width=160,
        fg_color="#1f6aa5",
        hover_color="#144870",
    )
    self.btn_calc.grid(row=2, column=0, columnspan=2, pady=12)

    card_display = ctk.CTkFrame(
        self.tab_calc, corner_radius=8, fg_color="#1c1c1c"
    )
    card_display.pack(fill="x", padx=15, pady=10)

    ctk.CTkLabel(
        card_display,
        text="TEMPO AJUSTADO (DIGITAL)",
        font=ctk.CTkFont(size=11, weight="bold"),
        text_color="#888888",
    ).pack(pady=(12, 2))

    self.c_res = ctk.CTkLabel(
        card_display,
        text="--:--:--.00",
        font=ctk.CTkFont(family="Consolas", size=28, weight="bold"),
        text_color="#00E5FF",
    )
    self.c_res.pack(pady=(0, 4))

    self.c_res_extenso = ctk.CTkLabel(
        card_display,
        text="0 hora(s), 0 minuto(s) e 0 segundo(s)",
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color="#E0E0E0",
    )
    self.c_res_extenso.pack(pady=(0, 12))

  def _c_calc(self):
    try:
      minutos = float(self.c_min.get().strip())
      vel = float(self.c_vel.get().strip())
      res = calcular_aceleracao_tempo(minutos * 60.0, vel)
      self.c_res.configure(text=f"{res}")
      self.c_res_extenso.configure(
          text=f"Convertendo temos: {res.texto_descritivo}"
      )
    except Exception as e:
      messagebox.showerror("Erro de Entrada", str(e))


if __name__ == "__main__":
  app = App()
  app.mainloop()