"""Homepage: central de automação com atalhos em cards."""

from typing import Callable

import customtkinter as ctk

_CARDS = [
    (
        "videos",
        "🎬 Vídeo & Áudio",
        "Compressão com teto de tamanho\ne conversão direta de formato",
    ),
    (
        "imagens",
        "🖼️ Otimização de Imagens",
        "Lotes, WebP, redimensionamento\ne conversão de fotos",
    ),
    (
        "pdf",
        "📑 Manipulação de PDFs",
        "Unir, dividir, rotacionar,\nmix frente/verso e marcadores",
    ),
    (
        "calc",
        "⏱️ Calculadora Temporal",
        "Aceleração de playback, conversor\nuniversal e algarismos romanos",
    ),
    (
        "energia",
        "⚡ Controle de Energia",
        "Agendamento de hibernação\nsilenciosa com cancelamento",
    ),
]


class TelaHome(ctk.CTkFrame):

  def __init__(self, master, navegar: Callable[[str], None]):
    super().__init__(master, fg_color="transparent")
    self._navegar = navegar

    ctk.CTkLabel(
        self,
        text="Central de Automação e Mídia",
        font=ctk.CTkFont(size=22, weight="bold"),
    ).pack(pady=(35, 4))

    ctk.CTkLabel(
        self,
        text="Selecione uma ferramenta para começar",
        font=ctk.CTkFont(size=12),
        text_color="#8a8a8a",
    ).pack(pady=(0, 25))

    grade = ctk.CTkFrame(self, fg_color="transparent")
    grade.pack()

    for i, (chave, titulo, descricao) in enumerate(_CARDS):
      card = ctk.CTkButton(
          grade,
          text=f"{titulo}\n\n{descricao}",
          width=240,
          height=120,
          corner_radius=12,
          border_width=1,
          border_color="#3a3a3a",
          fg_color="#212121",
          hover_color="#1f6aa5",
          font=ctk.CTkFont(size=13, weight="bold"),
          command=lambda c=chave: self._navegar(c),
      )
      card.grid(row=i // 3, column=i % 3, padx=12, pady=12)
