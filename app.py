"""Interface Gráfica Desktop Moderna (CustomTkinter)

Design estruturado em cards, grids alinhados e exibição de tempos de
processamento.
"""

from pathlib import Path
import threading
import time
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core.calculadora import ARTE_VASCO, calcular_aceleracao_tempo
from core.imagem import otimizar_imagem, otimizar_lote
from core.video import comprimir_video

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):

  def __init__(self):
    super().__init__()
    self.title("Media Automation Toolkit")
    self.geometry("820x650")
    self.minsize(760, 580)

    self.protocol("WM_DELETE_WINDOW", self._ao_fechar)

    self.tabview = ctk.CTkTabview(self, corner_radius=10)
    self.tabview.pack(fill="both", expand=True, padx=20, pady=15)

    self.tab_video = self.tabview.add("Compressão de Vídeo")
    self.tab_img = self.tabview.add("Otimização de Imagens")
    self.tab_calc = self.tabview.add("Calculadora de Tempo")

    self._setup_video_tab()
    self._setup_img_tab()
    self._setup_calc_tab()

  def _ao_fechar(self):
    modal = ctk.CTkToplevel(self)
    modal.title("CRVG - Finalizando")
    modal.geometry("400x420")
    modal.resizable(False, False)
    modal.attributes("-topmost", True)
    modal.protocol("WM_DELETE_WINDOW", self.destroy)

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

    ctk.CTkButton(
        modal,
        text="Encerrar Aplicação",
        fg_color="#8B0000",
        hover_color="#550000",
        command=self.destroy,
    ).pack(pady=(0, 15))

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
    self.v_format = ctk.CTkComboBox(f_sub, values=[".mp4", ".webm"], width=90)
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

    self.log_v = ctk.CTkTextbox(
        self.tab_video,
        font=ctk.CTkFont(family="Consolas", size=11),
        corner_radius=8,
    )
    self.log_v.pack(fill="both", expand=True, padx=15, pady=10)

  def _v_select(self):
    caminho = filedialog.askopenfilename(
        filetypes=[("Arquivos de Vídeo", "*.mp4 *.webm *.mkv *.mov *.avi")]
    )
    if caminho:
      self.v_file.set(caminho)

  def _v_start(self):

    def worker():
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

      self.btn_v_start.configure(state="disabled", text="Processando Vídeo...")
      self.log_v.insert(
          "end",
          f">>> Processando: {origem.name}\n"
          f">>> Destino: {destino.name} | Formato: {ext}\n",
      )
      self.log_v.see("end")

      t_cronometro_inicio = time.perf_counter()
      res = comprimir_video(
          origem=origem,
          destino=destino,
          tamanho_alvo_mb=tamanho_alvo,
          audio_bitrate_kbps=96,
      )
      tempo_total_cronometrado = time.perf_counter() - t_cronometro_inicio

      # Usa o tempo retornado do core ou o cronômetro da chamada
      tempo_exibicao = getattr(
          res, "tempo_processamento_s", tempo_total_cronometrado
      )
      if tempo_exibicao <= 0:
        tempo_exibicao = tempo_total_cronometrado

      if res.sucesso:
        orig_mb = res.tamanho_original_bytes / (1024 * 1024)
        final_mb = res.tamanho_final_bytes / (1024 * 1024)
        reducao = ((orig_mb - final_mb) / orig_mb) * 100
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
      else:
        self.log_v.insert(
            "end",
            f"\n[FALHA DE PROCESSAMENTO]\nTempo decorrido:"
            f" {tempo_exibicao:.2f} s\nMotivo: {res.mensagem_erro}\n{'-'*55}\n",
        )

      self.log_v.see("end")
      self.btn_v_start.configure(
          state="normal", text="Iniciar Compressão de Vídeo"
      )

    threading.Thread(target=worker, daemon=True).start()

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

    botoes_box = ctk.CTkFrame(card, fg_color="transparent")
    botoes_box.grid(row=0, column=2, padx=8, pady=10)
    ctk.CTkButton(
        botoes_box, text="Arquivo", width=65, command=self._i_select_file
    ).pack(side="left", padx=2)
    ctk.CTkButton(
        botoes_box, text="Pasta", width=65, command=self._i_select_dir
    ).pack(side="left", padx=2)

    f_sub = ctk.CTkFrame(card, fg_color="transparent")
    f_sub.grid(
        row=1, column=0, columnspan=3, padx=12, pady=(0, 10), sticky="w"
    )

    ctk.CTkLabel(f_sub, text="Dimensão Máxima (px):").pack(side="left")
    self.i_max = ctk.CTkEntry(f_sub, width=70)
    self.i_max.insert(0, "1920")
    self.i_max.pack(side="left", padx=(6, 20))

    ctk.CTkLabel(f_sub, text="Qualidade JPEG (1-100):").pack(side="left")
    self.i_qual = ctk.CTkEntry(f_sub, width=60)
    self.i_qual.insert(0, "80")
    self.i_qual.pack(side="left", padx=6)

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

    self.log_i = ctk.CTkTextbox(
        self.tab_img,
        font=ctk.CTkFont(family="Consolas", size=11),
        corner_radius=8,
    )
    self.log_i.pack(fill="both", expand=True, padx=15, pady=10)

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

    def worker():
      caminho_raw = self.i_path.get().strip()
      origem = Path(caminho_raw)
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

      self.btn_i_start.configure(
          state="disabled", text="Processando Imagens..."
      )

      if origem.is_file():
        destino = origem.parent / f"{origem.stem}_otimizada.jpg"
        self.log_i.insert(
            "end", f">>> Otimizando arquivo individual: {origem.name}\n"
        )
        self.log_i.see("end")

        t_i = time.perf_counter()
        res = otimizar_imagem(origem, destino, max_dim, qualidade)
        duracao = getattr(res, "tempo_processamento_s", time.perf_counter() - t_i)

        if res.sucesso:
          orig_kb = res.tamanho_original_bytes / 1024
          final_kb = res.tamanho_final_bytes / 1024
          self.log_i.insert(
              "end",
              f"[OK] {destino.name}\n"
              f"     Tamanho : {orig_kb:.1f} KB -> {final_kb:.1f} KB\n"
              f"     Duração : {duracao:.3f} s\n{'-'*55}\n",
          )
        else:
          self.log_i.insert(
              "end",
              f"[FALHA] {res.mensagem_erro} ({duracao:.3f} s)\n{'-'*55}\n",
          )
        self.log_i.see("end")
        self.btn_i_start.configure(
          state="normal", text="Iniciar Otimização de Imagens"
      )
        return

      destino = origem / "otimizadas"
      self.log_i.insert(
          "end",
          f">>> Processando lote em: {origem}\n>>> Saída: {destino}\n\n",
      )
      self.log_i.see("end")

      total = 0
      sucessos = 0
      bytes_antes = 0
      bytes_depois = 0
      t_lote_inicio = time.perf_counter()

      for res in otimizar_lote(origem, destino, max_dim, qualidade):
        total += 1
        dur = getattr(res, "tempo_processamento_s", 0.0)
        if res.sucesso:
          sucessos += 1
          bytes_antes += res.tamanho_original_bytes
          bytes_depois += res.tamanho_final_bytes
          final_kb = res.tamanho_final_bytes / 1024
          self.log_i.insert(
              "end",
              f" [{sucessos:02d}] {res.caminho_origem.name:<30} ->"
              f" {final_kb:7.1f} KB  ({dur:.3f} s)\n",
          )
        else:
          self.log_i.insert(
              "end",
              f" [ERRO] {res.caminho_origem.name}: {res.mensagem_erro}\n",
          )
        self.log_i.see("end")

      tempo_acumulado = time.perf_counter() - t_lote_inicio
      economia_mb = (bytes_antes - bytes_depois) / (1024 * 1024)
      self.log_i.insert(
          "end",
          f"\n{'='*55}\n"
          f" Concluídas          : {sucessos}/{total} imagens\n"
          f" Tempo Acumulado     : {tempo_acumulado:.2f} s\n"
          f" Espaço Economizado  : {economia_mb:.2f} MB\n"
          f"{'='*55}\n",
      )
      self.log_i.see("end")
      self.btn_i_start.configure(
          state="normal", text="Iniciar Otimização de Imagens"
      )

    threading.Thread(target=worker, daemon=True).start()

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