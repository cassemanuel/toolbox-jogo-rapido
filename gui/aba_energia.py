"""Aba de energia: agendamento de hibernação com presets e cancelamento."""

from datetime import datetime, timedelta
import subprocess
import threading
import time
from tkinter import messagebox
from typing import Any, Callable

import customtkinter as ctk

from gui.comum import exibir_historico, persistir_log

_PRESETS = {"10 min": 600, "30 min": 1800, "60 min": 3600}

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class AbaEnergia(ctk.CTkFrame):

  def __init__(
      self,
      master,
      post_ui: Callable[[Callable, Any], None],
  ):
    super().__init__(master, fg_color="transparent")
    self.pack(fill="both", expand=True)
    self._post_ui = post_ui

    self._worker: threading.Thread | None = None
    self.cancel_event = threading.Event()

    self._montar_layout()
    exibir_historico(self.log_e)

  @property
  def worker(self) -> threading.Thread | None:
    return self._worker

  def _montar_layout(self):
    card = ctk.CTkFrame(
        self, corner_radius=8, border_width=1, border_color="#3a3a3a"
    )
    card.pack(fill="x", padx=15, pady=10)

    ctk.CTkLabel(
        card, text="Preset:", font=ctk.CTkFont(weight="bold")
    ).grid(row=0, column=0, padx=12, pady=10, sticky="w")

    self.preset = ctk.CTkSegmentedButton(
        card,
        values=list(_PRESETS.keys()) + ["A Definir"],
        command=self._preset_changed,
    )
    self.preset.set("10 min")
    self.preset.grid(
        row=0, column=1, columnspan=2, padx=8, pady=10, sticky="w"
    )

    self.f_custom = ctk.CTkFrame(card, fg_color="transparent")
    ctk.CTkLabel(
        self.f_custom, text="Tempo em segundos:"
    ).pack(side="left")
    self.e_segundos = ctk.CTkEntry(self.f_custom, width=120)
    self.e_segundos.pack(side="left", padx=8)
    self.e_segundos.bind(
        "<KeyRelease>", lambda _e: self._atualizar_previsao()
    )

    self.lbl_previsao = ctk.CTkLabel(
        card,
        text="",
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color="#00E5FF",
    )
    self.lbl_previsao.grid(
        row=2, column=0, columnspan=3, padx=12, pady=(4, 10),
        sticky="w",
    )

    card.grid_columnconfigure(1, weight=1)

    self.btn_agendar = ctk.CTkButton(
        self,
        text="Agendar Hibernação",
        height=36,
        font=ctk.CTkFont(weight="bold"),
        fg_color="#1f6aa5",
        hover_color="#144870",
        command=self._agendar,
    )
    self.btn_agendar.pack(fill="x", padx=15, pady=5)

    self.btn_cancelar = ctk.CTkButton(
        self,
        text="Cancelar Agendamento",
        height=32,
        fg_color="#8B0000",
        hover_color="#550000",
        state="disabled",
        command=self._cancelar,
    )
    self.btn_cancelar.pack(fill="x", padx=15, pady=(0, 5))

    self.prog_e = ctk.CTkProgressBar(self, corner_radius=8)
    self.prog_e.set(0)
    self.prog_e.pack(fill="x", padx=15, pady=(0, 2))

    self.lbl_restante = ctk.CTkLabel(
        self,
        text="Tempo restante: --:--:--",
        font=ctk.CTkFont(family="Consolas", size=12),
        text_color="#8a8a8a",
    )
    self.lbl_restante.pack(anchor="w", padx=15, pady=(0, 5))

    self.log_e = ctk.CTkTextbox(
        self,
        font=ctk.CTkFont(family="Consolas", size=11),
        corner_radius=8,
    )
    self.log_e.pack(fill="both", expand=True, padx=15, pady=10)

    self._atualizar_previsao()

  def _segundos_selecionados(self) -> int | None:
    preset = self.preset.get()
    if preset in _PRESETS:
      return _PRESETS[preset]
    try:
      valor = int(self.e_segundos.get().strip())
      return valor if valor > 0 else None
    except ValueError:
      return None

  def _preset_changed(self, _valor):
    if self.preset.get() == "A Definir":
      self.f_custom.grid(
          row=1, column=0, columnspan=3, padx=12, pady=(0, 4),
          sticky="w",
      )
    else:
      self.f_custom.grid_remove()
    self._atualizar_previsao()

  def _atualizar_previsao(self):
    total = self._segundos_selecionados()
    if total is None:
      self.lbl_previsao.configure(
          text="Previsão: informe um tempo válido em segundos"
      )
      return
    minutos, segundos = divmod(total, 60)
    alvo = datetime.now() + timedelta(seconds=total)
    self.lbl_previsao.configure(
        text=f"Previsão: Hibernará em {minutos} minuto(s) e"
        f" {segundos} segundo(s) (às {alvo:%H:%M:%S})"
    )

  def _agendar(self):
    total = self._segundos_selecionados()
    if total is None:
      messagebox.showerror(
          "Erro", "Informe um tempo válido em segundos (> 0)."
      )
      return

    self.cancel_event.clear()
    self.btn_agendar.configure(
        state="disabled", text="Agendado..."
    )
    self.btn_cancelar.configure(state="normal")
    self.prog_e.set(0)

    alvo = datetime.now() + timedelta(seconds=total)
    self.log_e.insert(
        "end", "\n================ NOVA EXECUÇÃO ================\n"
    )
    self.log_e.insert(
        "end",
        f">>> Hibernação agendada para {alvo:%H:%M:%S}"
        f" ({total} s)\n",
    )
    self.log_e.see("end")

    def worker():
      restante = total
      while restante > 0:
        if self.cancel_event.is_set():
          self._post_ui(self._e_cancelado)
          return
        self._post_ui(self._e_tick, restante, total)
        time.sleep(1)
        restante -= 1
      if self.cancel_event.is_set():
        self._post_ui(self._e_cancelado)
        return
      self._post_ui(self._e_tick, 0, total)
      try:
        subprocess.run(
            ["shutdown", "/h"], creationflags=_CREATE_NO_WINDOW
        )
        self._post_ui(self._e_disparado)
      except Exception as e:
        self._post_ui(self._e_erro, e)

    self._worker = threading.Thread(target=worker, daemon=True)
    self._worker.start()

  def _cancelar(self):
    self.cancel_event.set()

  def _e_tick(self, restante, total):
    h, rem = divmod(restante, 3600)
    m, s = divmod(rem, 60)
    self.lbl_restante.configure(
        text=f"Tempo restante: {h:02d}:{m:02d}:{s:02d}"
    )
    self.prog_e.set(1.0 - (restante / total if total else 0.0))

  def _restaurar(self):
    self.btn_agendar.configure(
        state="normal", text="Agendar Hibernação"
    )
    self.btn_cancelar.configure(state="disabled")
    self.lbl_restante.configure(text="Tempo restante: --:--:--")

  def _e_cancelado(self):
    self.log_e.insert(
        "end", "[CANCELADO] Agendamento cancelado pelo usuário.\n"
    )
    self.log_e.see("end")
    persistir_log(self.log_e, "energia")
    self._restaurar()

  def _e_disparado(self):
    self.prog_e.set(1.0)
    self.log_e.insert(
        "end", "[OK] Comando de hibernação disparado.\n"
    )
    self.log_e.see("end")
    persistir_log(self.log_e, "energia")
    self._restaurar()

  def _e_erro(self, erro):
    self.log_e.insert(
        "end", f"[FALHA] {erro}\n"
    )
    self.log_e.see("end")
    persistir_log(self.log_e, "energia")
    self._restaurar()
