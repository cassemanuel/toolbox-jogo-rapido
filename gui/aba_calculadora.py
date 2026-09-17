"""Aba da calculadora de tempo com fator de aceleração."""

from tkinter import messagebox
from typing import Any, Callable

import customtkinter as ctk

from core.calculadora import calcular_aceleracao_tempo


class AbaCalculadora(ctk.CTkFrame):

  def __init__(
      self,
      master,
      post_ui: Callable[[Callable, Any], None],
  ):
    super().__init__(master, fg_color="transparent")
    self.pack(fill="both", expand=True)
    self._post_ui = post_ui

    self._montar_layout()

  def _montar_layout(self):
    card = ctk.CTkFrame(
        self, corner_radius=8, border_width=1, border_color="#3a3a3a"
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
        self, corner_radius=8, fg_color="#1c1c1c"
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
