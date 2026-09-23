"""Aba da calculadora de tempo: aceleração e conversão universal."""

from tkinter import messagebox
from typing import Any, Callable

import customtkinter as ctk

from core.calculadora import (
    calcular_aceleracao_tempo,
    converter_unidade_tempo,
)

_UNIDADES = {
    "Segundos": "segundos",
    "Minutos": "minutos",
    "Horas": "horas",
    "Dias": "dias",
    "Semanas": "semanas",
    "Anos": "anos",
}


def _fmt_num(v: float) -> str:
  if v == int(v):
    return f"{int(v):,}"
  return f"{v:,.4f}".rstrip("0").rstrip(".")


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
    self.modo_calc = ctk.CTkSegmentedButton(
        self,
        values=["Aceleração de Playback", "Conversão de Tempo"],
        command=self._modo_changed,
    )
    self.modo_calc.set("Aceleração de Playback")
    self.modo_calc.pack(fill="x", padx=15, pady=(15, 5))

    self.f_acel = ctk.CTkFrame(self, fg_color="transparent")
    self.f_conv = ctk.CTkFrame(self, fg_color="transparent")
    self._montar_aceleracao(self.f_acel)
    self._montar_conversao(self.f_conv)
    self.f_acel.pack(fill="both", expand=True)

  def _modo_changed(self, modo):
    if modo == "Aceleração de Playback":
      self.f_conv.pack_forget()
      self.f_acel.pack(fill="both", expand=True)
    else:
      self.f_acel.pack_forget()
      self.f_conv.pack(fill="both", expand=True)

  # ---------------- Aceleração de Playback ----------------

  def _montar_aceleracao(self, raiz):
    card = ctk.CTkFrame(
        raiz, corner_radius=8, border_width=1, border_color="#3a3a3a"
    )
    card.pack(fill="x", padx=15, pady=10)

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
        raiz, corner_radius=8, fg_color="#1c1c1c"
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

  # ---------------- Conversão de Tempo ----------------

  def _montar_conversao(self, raiz):
    card = ctk.CTkFrame(
        raiz, corner_radius=8, border_width=1, border_color="#3a3a3a"
    )
    card.pack(fill="x", padx=15, pady=10)

    ctk.CTkLabel(
        card, text="Valor:", font=ctk.CTkFont(weight="bold")
    ).grid(row=0, column=0, padx=15, pady=10, sticky="w")
    self.conv_valor = ctk.CTkEntry(card, width=140)
    self.conv_valor.grid(row=0, column=1, padx=15, pady=10, sticky="w")

    ctk.CTkLabel(
        card, text="Unidade de Origem:", font=ctk.CTkFont(weight="bold")
    ).grid(row=1, column=0, padx=15, pady=10, sticky="w")
    self.conv_unidade = ctk.CTkComboBox(
        card,
        values=list(_UNIDADES.keys()),
        width=140,
        state="readonly",
    )
    self.conv_unidade.set("Horas")
    self.conv_unidade.grid(row=1, column=1, padx=15, pady=10, sticky="w")

    ctk.CTkButton(
        card,
        text="Converter Tempo",
        command=self._c_converter,
        width=160,
        fg_color="#1f6aa5",
        hover_color="#144870",
    ).grid(row=2, column=0, columnspan=2, pady=12)

    painel = ctk.CTkFrame(raiz, corner_radius=8, fg_color="#1c1c1c")
    painel.pack(fill="x", padx=15, pady=10)

    ctk.CTkLabel(
        painel,
        text="DECOMPOSIÇÃO UNIVERSAL",
        font=ctk.CTkFont(size=11, weight="bold"),
        text_color="#888888",
    ).pack(pady=(12, 6))

    self.res_labels: dict[str, ctk.CTkLabel] = {}
    for nome, sufixo in (
        ("Segundos", "s"),
        ("Minutos", "min"),
        ("Horas", "h"),
        ("Dias", "dias"),
        ("Semanas", "semanas"),
        ("Anos", "anos (~365d)"),
    ):
      linha = ctk.CTkFrame(painel, fg_color="transparent")
      linha.pack(fill="x", padx=20)
      ctk.CTkLabel(
          linha, text=f"{nome}:", width=90, anchor="w"
      ).pack(side="left")
      lbl = ctk.CTkLabel(
          linha,
          text=f"— {sufixo}",
          font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
          text_color="#00E5FF",
          anchor="w",
      )
      lbl.pack(side="left", padx=10)
      self.res_labels[nome] = lbl

    self.lbl_romanos = ctk.CTkLabel(
        painel,
        text="",
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color="#D4AF37",
    )
    self.lbl_romanos.pack(pady=(8, 12))

  def _c_converter(self):
    try:
      valor = float(self.conv_valor.get().strip())
      unidade = _UNIDADES[self.conv_unidade.get()]
      res = converter_unidade_tempo(valor, unidade)
    except Exception as e:
      messagebox.showerror("Erro de Entrada", str(e))
      return

    self.res_labels["Segundos"].configure(
        text=f"{_fmt_num(res.em_segundos)} s"
    )
    self.res_labels["Minutos"].configure(
        text=f"{_fmt_num(res.em_minutos)} min"
    )
    self.res_labels["Horas"].configure(
        text=f"{_fmt_num(res.em_horas)} h"
    )
    self.res_labels["Dias"].configure(
        text=f"{_fmt_num(res.em_dias)} dias"
    )
    self.res_labels["Semanas"].configure(
        text=f"{_fmt_num(res.em_semanas)} semanas"
    )
    self.res_labels["Anos"].configure(
        text=f"{_fmt_num(res.em_anos)} anos (~365d)"
    )
    if res.romanos_dias:
      self.lbl_romanos.configure(
          text=f"🏛️ Dias Inteiros em Algarismos Romanos:"
          f" [ {res.romanos_dias} ]"
      )
    else:
      self.lbl_romanos.configure(text="")
