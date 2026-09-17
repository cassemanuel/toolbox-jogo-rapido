"""Aba de manipulação de PDFs: unir, extrair páginas e dividir."""

from pathlib import Path
import threading
from tkinter import filedialog, messagebox
from typing import Any, Callable

import customtkinter as ctk

from pypdf import PdfReader

from core.binarios import gerar_destino_unico
from core.pdf import (
    dividir_pdf,
    dividir_por_marcadores_pdf,
    dividir_por_tamanho_pdf,
    extrair_paginas,
    mix_alternado_pdf,
    rotacionar_pdf,
    unir_pdfs,
)
from gui.comum import (
    abrir_pasta_ou_padrao,
    exibir_historico,
    persistir_log,
)

_ACOES = [
    "Unir",
    "Extrair",
    "Dividir",
    "Rotacionar",
    "Mix Alternado",
    "Por Tamanho",
    "Por Marcador",
]

_ROTULOS = {
    "Unir": "Unir Documentos",
    "Extrair": "Extrair",
    "Dividir": "Dividir em Páginas",
    "Rotacionar": "Rotacionar PDF",
    "Mix Alternado": "Intercalar PDFs",
    "Por Tamanho": "Dividir por Tamanho",
    "Por Marcador": "Dividir por Marcadores",
}

_ANGULOS = {
    "90° Horário": 90,
    "180° Invertido": 180,
    "270° (90° Anti-horário)": 270,
}


def _parse_paginas(texto: str) -> list[int]:
  """Expande '1, 3-5, 8' em [1, 3, 4, 5, 8] (índice 1-based)."""
  paginas: list[int] = []
  for trecho in texto.split(","):
    trecho = trecho.strip()
    if not trecho:
      continue
    if "-" in trecho:
      inicio, fim = (int(t.strip()) for t in trecho.split("-", 1))
      paginas.extend(range(inicio, fim + 1))
    else:
      paginas.append(int(trecho))
  return paginas


class AbaPdf(ctk.CTkFrame):

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
    self._arquivos_unir: list[Path] = []

    self._montar_layout()
    self._acao_changed(_ACOES[0])
    exibir_historico(self.log_pdf)

  @property
  def worker(self) -> threading.Thread | None:
    return self._worker

  def _montar_layout(self):
    card = ctk.CTkFrame(
        self, corner_radius=8, border_width=1, border_color="#3a3a3a"
    )
    card.pack(fill="x", padx=15, pady=10)

    ctk.CTkLabel(
        card, text="Ação:", font=ctk.CTkFont(weight="bold")
    ).grid(row=0, column=0, padx=12, pady=10, sticky="w")

    self.acao = ctk.CTkSegmentedButton(
        card, values=_ACOES, command=self._acao_changed
    )
    self.acao.set(_ACOES[0])
    self.acao.grid(
        row=0, column=1, columnspan=3, padx=8, pady=10, sticky="w"
    )

    # --- Seleção de arquivo único (Extrair / Dividir) ---
    self.f_unico = ctk.CTkFrame(card, fg_color="transparent")
    self.f_unico.grid(
        row=1, column=0, columnspan=4, padx=12, sticky="ew"
    )
    ctk.CTkLabel(self.f_unico, text="Arquivo PDF:").pack(side="left")
    self.pdf_path = ctk.StringVar()
    self.pdf_path.trace_add("write", lambda *_: self._atualizar_info_pdf())
    ctk.CTkEntry(
        self.f_unico,
        textvariable=self.pdf_path,
        placeholder_text="Selecione o documento PDF...",
        width=380,
    ).pack(side="left", padx=8)
    ctk.CTkButton(
        self.f_unico,
        text="Buscar Arquivo",
        width=110,
        command=self._pdf_select,
    ).pack(side="left", padx=4)
    self.lbl_info_pdf = ctk.CTkLabel(
        self.f_unico,
        text="",
        font=ctk.CTkFont(size=11),
        text_color="#8a8a8a",
    )
    self.lbl_info_pdf.pack(side="left", padx=8)

    # --- Lista de arquivos (Unir) ---
    self.f_multi = ctk.CTkFrame(card, fg_color="transparent")
    f_btns = ctk.CTkFrame(self.f_multi, fg_color="transparent")
    f_btns.pack(fill="x")
    ctk.CTkButton(
        f_btns,
        text="Adicionar PDFs",
        width=110,
        command=self._pdf_add,
    ).pack(side="left", padx=(0, 6))
    ctk.CTkButton(
        f_btns,
        text="Limpar Lista",
        width=110,
        fg_color="#6b6b6b",
        hover_color="#4a4a4a",
        command=self._pdf_limpar,
    ).pack(side="left")

    self.lista_pdf = ctk.CTkTextbox(
        self.f_multi,
        height=64,
        font=ctk.CTkFont(family="Consolas", size=10),
    )
    self.lista_pdf.pack(fill="x", pady=(6, 0))
    self.lista_pdf.configure(state="disabled")

    # --- Campo de páginas (Extrair) ---
    self.f_paginas = ctk.CTkFrame(card, fg_color="transparent")
    self.lbl_paginas = ctk.CTkLabel(
        self.f_paginas,
        text="Páginas físicas (folhas 1 a N, ex: 1, 3-5, 8):",
    )
    self.lbl_paginas.pack(side="left")
    self.pdf_paginas = ctk.CTkEntry(self.f_paginas, width=180)
    self.pdf_paginas.pack(side="left", padx=8)

    # --- Campos (Rotacionar) ---
    self.f_rot = ctk.CTkFrame(card, fg_color="transparent")
    ctk.CTkLabel(self.f_rot, text="Ângulo:").pack(side="left")
    self.rot_angulo = ctk.CTkComboBox(
        self.f_rot,
        values=list(_ANGULOS.keys()),
        width=190,
        state="readonly",
    )
    self.rot_angulo.set("90° Horário")
    self.rot_angulo.pack(side="left", padx=8)
    ctk.CTkLabel(
        self.f_rot, text="Páginas (vazio = todas):"
    ).pack(side="left", padx=(14, 4))
    self.rot_paginas = ctk.CTkEntry(self.f_rot, width=140)
    self.rot_paginas.pack(side="left", padx=4)

    # --- Campos (Mix Alternado) ---
    self.f_mix = ctk.CTkFrame(card, fg_color="transparent")
    self.mix_a = ctk.StringVar()
    self.mix_b = ctk.StringVar()
    self.mix_inv = ctk.BooleanVar(value=False)

    linha_a = ctk.CTkFrame(self.f_mix, fg_color="transparent")
    linha_a.pack(fill="x")
    ctk.CTkLabel(linha_a, text="Arquivo A (Frentes):").pack(side="left")
    ctk.CTkEntry(
        linha_a,
        textvariable=self.mix_a,
        placeholder_text="PDF das frentes...",
        width=320,
    ).pack(side="left", padx=8)
    ctk.CTkButton(
        linha_a,
        text="Buscar",
        width=80,
        command=lambda: self._mix_select(self.mix_a),
    ).pack(side="left")

    linha_b = ctk.CTkFrame(self.f_mix, fg_color="transparent")
    linha_b.pack(fill="x", pady=(6, 0))
    ctk.CTkLabel(linha_b, text="Arquivo B (Versos):").pack(side="left")
    ctk.CTkEntry(
        linha_b,
        textvariable=self.mix_b,
        placeholder_text="PDF dos versos...",
        width=320,
    ).pack(side="left", padx=8)
    ctk.CTkButton(
        linha_b,
        text="Buscar",
        width=80,
        command=lambda: self._mix_select(self.mix_b),
    ).pack(side="left")
    ctk.CTkCheckBox(
        linha_b,
        text="Inverter ordem do Arquivo B (versos na ordem inversa)",
        variable=self.mix_inv,
    ).pack(side="left", padx=(14, 0))

    # --- Campos (Por Tamanho) ---
    self.f_tam = ctk.CTkFrame(card, fg_color="transparent")
    ctk.CTkLabel(
        self.f_tam, text="Tamanho Máximo por Parte (MB):"
    ).pack(side="left")
    self.tam_mb = ctk.CTkEntry(self.f_tam, width=80)
    self.tam_mb.insert(0, "10")
    self.tam_mb.pack(side="left", padx=8)

    # --- Campos (Por Marcador) ---
    self.f_marc = ctk.CTkFrame(card, fg_color="transparent")
    ctk.CTkLabel(self.f_marc, text="Nível de Marcador:").pack(
        side="left"
    )
    self.marc_nivel = ctk.CTkEntry(self.f_marc, width=60)
    self.marc_nivel.insert(0, "1")
    self.marc_nivel.pack(side="left", padx=8)

    card.grid_columnconfigure(1, weight=1)

    self.btn_pdf_start = ctk.CTkButton(
        self,
        text="Unir Documentos",
        height=36,
        font=ctk.CTkFont(weight="bold"),
        fg_color="#1f6aa5",
        hover_color="#144870",
        command=self._pdf_start,
    )
    self.btn_pdf_start.pack(fill="x", padx=15, pady=5)

    self.prog_pdf = ctk.CTkProgressBar(self, corner_radius=8)
    self.prog_pdf.set(0)
    self.prog_pdf.pack(fill="x", padx=15, pady=(0, 5))

    self.btn_pdf_abrir = ctk.CTkButton(
        self,
        text="Abrir Pasta de Destino",
        width=160,
        command=lambda: abrir_pasta_ou_padrao(
            self._ultimo_destino, ""
        ),
    )
    self.btn_pdf_abrir.pack(anchor="e", padx=15, pady=(0, 5))

    self.log_pdf = ctk.CTkTextbox(
        self,
        font=ctk.CTkFont(family="Consolas", size=11),
        corner_radius=8,
    )
    self.log_pdf.pack(fill="both", expand=True, padx=15, pady=10)

  def _acao_changed(self, acao):
    for f in (
        self.f_unico,
        self.f_multi,
        self.f_paginas,
        self.f_rot,
        self.f_mix,
        self.f_tam,
        self.f_marc,
    ):
      f.grid_remove()

    self.btn_pdf_start.configure(text=_ROTULOS[acao])
    if acao == "Unir":
      self.f_multi.grid(
          row=1, column=0, columnspan=4, padx=12, sticky="ew"
      )
    elif acao == "Mix Alternado":
      self.f_mix.grid(
          row=1, column=0, columnspan=4, padx=12, sticky="ew"
      )
    else:
      self.f_unico.grid(
          row=1, column=0, columnspan=4, padx=12, sticky="ew"
      )
      extra = {
          "Extrair": self.f_paginas,
          "Rotacionar": self.f_rot,
          "Por Tamanho": self.f_tam,
          "Por Marcador": self.f_marc,
      }.get(acao)
      if extra is not None:
        extra.grid(
            row=2, column=0, columnspan=4, padx=12, pady=(0, 8),
            sticky="w",
        )
    self._atualizar_info_pdf()

  def _atualizar_info_pdf(self):
    caminho = Path(self.pdf_path.get().strip())
    self.lbl_paginas.configure(
        text="Páginas físicas (folhas 1 a N, ex: 1, 3-5, 8):"
    )
    self.lbl_info_pdf.configure(text="")
    if not caminho.is_file():
      return
    try:
      reader = PdfReader(str(caminho))
      total = len(reader.pages)
    except Exception:
      return
    texto = f"Total: {total} folhas físicas detectadas"
    if self.acao.get() == "Por Marcador":
      try:
        tem_marcadores = bool(reader.outline)
      except Exception:
        tem_marcadores = False
      if not tem_marcadores:
        texto += "  —  SEM marcadores/índice interno"
    self.lbl_info_pdf.configure(text=texto)
    self.lbl_paginas.configure(
        text=f"Páginas físicas (folhas 1 a {total}, ex: 1, 3-5, 8):"
    )

  def _pdf_select(self):
    caminho = filedialog.askopenfilename(
        filetypes=[("Documentos PDF", "*.pdf")]
    )
    if caminho:
      self.pdf_path.set(caminho)

  def _pdf_add(self):
    caminhos = filedialog.askopenfilenames(
        filetypes=[("Documentos PDF", "*.pdf")]
    )
    if not caminhos:
      return
    self._arquivos_unir.extend(Path(c) for c in caminhos)
    self._render_lista()

  def _pdf_limpar(self):
    self._arquivos_unir.clear()
    self._render_lista()

  def _mix_select(self, var):
    caminho = filedialog.askopenfilename(
        filetypes=[("Documentos PDF", "*.pdf")]
    )
    if caminho:
      var.set(caminho)

  def _rotulo(self):
    return _ROTULOS[self.acao.get()]

  def _render_lista(self):
    self.lista_pdf.configure(state="normal")
    self.lista_pdf.delete("1.0", "end")
    for i, arq in enumerate(self._arquivos_unir, 1):
      self.lista_pdf.insert("end", f" {i:02d}. {arq.name}\n")
    self.lista_pdf.configure(state="disabled")

  def _restaurar_botao(self, texto):
    self.btn_pdf_start.configure(state="normal", text=texto)

  def _pdf_start(self):
    acao = self.acao.get()
    self.prog_pdf.set(0)
    self.btn_pdf_start.configure(state="disabled", text="Processando...")
    self.log_pdf.insert(
        "end", "\n================ NOVA EXECUÇÃO ================\n"
    )
    self.log_pdf.see("end")

    if acao == "Unir":
      self._start_unir()
    elif acao == "Extrair":
      self._start_extrair()
    elif acao == "Dividir":
      self._start_dividir()
    elif acao == "Rotacionar":
      self._start_rotacionar()
    elif acao == "Mix Alternado":
      self._start_mix()
    elif acao == "Por Tamanho":
      self._start_tamanho()
    else:
      self._start_marcador()

  def _start_unir(self):
    if len(self._arquivos_unir) < 2:
      messagebox.showerror(
          "Erro", "Selecione ao menos 2 PDFs para unir."
      )
      self._restaurar_botao("Unir Documentos")
      return
    arquivos = list(self._arquivos_unir)
    destino = gerar_destino_unico(
        arquivos[0].parent, "unificado", "pdf", ".pdf"
    )
    self.log_pdf.insert(
        "end",
        f">>> Unindo {len(arquivos)} documentos -> {destino.name}\n",
    )
    self.log_pdf.see("end")

    def worker():
      try:
        res = unir_pdfs(arquivos, destino)
        self._post_ui(self._pdf_concluir, res)
      except Exception as e:
        self._post_ui(self._pdf_erro, e, "Unir Documentos")

    self._worker = threading.Thread(target=worker, daemon=True)
    self._worker.start()

  def _start_extrair(self):
    origem = Path(self.pdf_path.get().strip())
    if not origem.is_file():
      messagebox.showerror("Erro", "Arquivo PDF não encontrado.")
      self._restaurar_botao("Extrair")
      return
    try:
      paginas = _parse_paginas(self.pdf_paginas.get())
    except ValueError:
      messagebox.showerror(
          "Erro", "Formato de páginas inválido. Use ex: 1, 3-5, 8"
      )
      self._restaurar_botao("Extrair")
      return
    if not paginas:
      messagebox.showerror("Erro", "Informe ao menos uma página.")
      self._restaurar_botao("Extrair")
      return
    destino = gerar_destino_unico(
        origem.parent, origem.stem, "extraido", ".pdf"
    )
    try:
      total_folhas = len(PdfReader(str(origem)).pages)
      self.log_pdf.insert(
          "end",
          f">>> Documento possui {total_folhas} folhas físicas"
          " no total.\n",
      )
    except Exception:
      pass
    self.log_pdf.insert(
        "end",
        f">>> Extraindo páginas {paginas} de {origem.name}\n",
    )
    self.log_pdf.see("end")

    def worker():
      try:
        res = extrair_paginas(origem, paginas, destino)
        self._post_ui(self._pdf_concluir, res)
      except Exception as e:
        self._post_ui(self._pdf_erro, e, "Extrair")

    self._worker = threading.Thread(target=worker, daemon=True)
    self._worker.start()

  def _worker_blocos(self, fn, origem, pasta, rotulo):
    def worker():
      try:
        resultados = fn(origem, pasta)
        for i, res in enumerate(resultados, 1):
          self._post_ui(self._pdf_item_divisao, res)
          self._post_ui(
              self._pdf_progresso,
              i / len(resultados) * 100.0 if resultados else 0.0,
          )
        self._post_ui(self._pdf_fim_divisao, resultados, pasta)
      except Exception as e:
        self._post_ui(self._pdf_erro, e, rotulo)

    self._worker = threading.Thread(target=worker, daemon=True)
    self._worker.start()

  def _start_dividir(self):
    origem = Path(self.pdf_path.get().strip())
    if not origem.is_file():
      messagebox.showerror("Erro", "Arquivo PDF não encontrado.")
      self._restaurar_botao(self._rotulo())
      return
    pasta = origem.parent / "paginas_pdf"
    self.log_pdf.insert(
        "end", f">>> Dividindo {origem.name} -> {pasta}\n"
    )
    self.log_pdf.see("end")
    self._worker_blocos(dividir_pdf, origem, pasta, self._rotulo())

  def _start_rotacionar(self):
    origem = Path(self.pdf_path.get().strip())
    if not origem.is_file():
      messagebox.showerror("Erro", "Arquivo PDF não encontrado.")
      self._restaurar_botao(self._rotulo())
      return
    angulo = _ANGULOS[self.rot_angulo.get()]
    texto = self.rot_paginas.get().strip()
    try:
      paginas = _parse_paginas(texto) if texto else None
    except ValueError:
      messagebox.showerror(
          "Erro", "Formato de páginas inválido. Use ex: 1, 3-5"
      )
      self._restaurar_botao(self._rotulo())
      return
    destino = gerar_destino_unico(
        origem.parent, origem.stem, "rotacionado", ".pdf"
    )
    alvo = (
        f"páginas {paginas}" if paginas else "todas as páginas"
    )
    self.log_pdf.insert(
        "end", f">>> Rotacionando {origem.name} em {angulo}° ({alvo})\n"
    )
    self.log_pdf.see("end")
    rotulo = self._rotulo()

    def worker():
      try:
        res = rotacionar_pdf(origem, angulo, paginas, destino)
        self._post_ui(self._pdf_concluir, res)
      except Exception as e:
        self._post_ui(self._pdf_erro, e, rotulo)

    self._worker = threading.Thread(target=worker, daemon=True)
    self._worker.start()

  def _start_mix(self):
    arq_a = Path(self.mix_a.get().strip())
    arq_b = Path(self.mix_b.get().strip())
    if not arq_a.is_file() or not arq_b.is_file():
      messagebox.showerror(
          "Erro", "Selecione os arquivos A e B válidos."
      )
      self._restaurar_botao(self._rotulo())
      return
    inverter = bool(self.mix_inv.get())
    destino = gerar_destino_unico(arq_a.parent, "mix", "pdf", ".pdf")
    modo = "B invertido" if inverter else "ordem direta"
    self.log_pdf.insert(
        "end",
        f">>> Intercalando {arq_a.name} + {arq_b.name} ({modo})\n",
    )
    self.log_pdf.see("end")
    rotulo = self._rotulo()

    def worker():
      try:
        res = mix_alternado_pdf(arq_a, arq_b, inverter, destino)
        self._post_ui(self._pdf_concluir, res)
      except Exception as e:
        self._post_ui(self._pdf_erro, e, rotulo)

    self._worker = threading.Thread(target=worker, daemon=True)
    self._worker.start()

  def _start_tamanho(self):
    origem = Path(self.pdf_path.get().strip())
    if not origem.is_file():
      messagebox.showerror("Erro", "Arquivo PDF não encontrado.")
      self._restaurar_botao(self._rotulo())
      return
    try:
      teto = float(self.tam_mb.get().strip() or "10")
      if teto <= 0:
        raise ValueError
    except ValueError:
      messagebox.showerror(
          "Erro", "Tamanho máximo deve ser um número > 0."
      )
      self._restaurar_botao(self._rotulo())
      return
    pasta = origem.parent / "blocos_pdf"
    self.log_pdf.insert(
        "end",
        f">>> Fatiando {origem.name} em blocos de até"
        f" {teto:g} MB -> {pasta}\n",
    )
    self.log_pdf.see("end")
    self._worker_blocos(
        lambda o, p: dividir_por_tamanho_pdf(o, teto, p),
        origem,
        pasta,
        self._rotulo(),
    )

  def _start_marcador(self):
    origem = Path(self.pdf_path.get().strip())
    if not origem.is_file():
      messagebox.showerror("Erro", "Arquivo PDF não encontrado.")
      self._restaurar_botao(self._rotulo())
      return
    try:
      nivel = int(self.marc_nivel.get().strip() or "1")
      if nivel < 1:
        raise ValueError
    except ValueError:
      messagebox.showerror(
          "Erro", "Nível de marcador deve ser inteiro >= 1."
      )
      self._restaurar_botao(self._rotulo())
      return
    pasta = origem.parent / "secoes_pdf"
    self.log_pdf.insert(
        "end",
        f">>> Fatiando {origem.name} pelos marcadores"
        f" (nível {nivel}) -> {pasta}\n",
    )
    self.log_pdf.see("end")
    self._worker_blocos(
        lambda o, p: dividir_por_marcadores_pdf(o, nivel, p),
        origem,
        pasta,
        self._rotulo(),
    )

  def _pdf_progresso(self, pct):
    self.prog_pdf.set(min(100.0, max(0.0, pct)) / 100.0)

  def _pdf_item_divisao(self, res):
    if res.sucesso:
      self.log_pdf.insert(
          "end", f"   [OK] {res.caminho_destino.name}\n"
      )
    else:
      self.log_pdf.insert("end", f"   [ERRO] {res.mensagem_erro}\n")
    self.log_pdf.see("end")

  def _pdf_fim_divisao(self, resultados, pasta):
    sucessos = sum(1 for r in resultados if r.sucesso)
    self.log_pdf.insert(
        "end",
        f"\n{'='*55}\n Divisão concluída:"
        f" {sucessos}/{len(resultados)} página(s)\n{'='*55}\n",
    )
    if sucessos > 0:
      self._ultimo_destino = pasta
    self.log_pdf.see("end")
    persistir_log(self.log_pdf, "pdf")
    self._restaurar_botao(self._rotulo())

  def _pdf_concluir(self, res):
    if res.sucesso:
      self.log_pdf.insert(
          "end",
          f"[OK] {res.caminho_destino.name}\n"
          f"     Páginas: {res.total_paginas}\n{'-'*55}\n",
      )
      self._ultimo_destino = res.caminho_destino
      self.prog_pdf.set(1.0)
    else:
      self.prog_pdf.set(0)
      self.log_pdf.insert(
          "end", f"[FALHA] {res.mensagem_erro}\n{'-'*55}\n"
      )
    self.log_pdf.see("end")
    persistir_log(self.log_pdf, "pdf")
    self._restaurar_botao(self._rotulo())

  def _pdf_erro(self, erro, rotulo):
    self.prog_pdf.set(0)
    self.log_pdf.insert(
        "end", f"\n[FALHA INESPERADA] {erro}\n{'-'*55}\n"
    )
    self.log_pdf.see("end")
    persistir_log(self.log_pdf, "pdf")
    self._restaurar_botao(rotulo)
