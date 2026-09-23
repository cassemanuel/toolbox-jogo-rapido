"""Módulo de cálculos aritméticos de tempo e alocação de bitrate."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DuracaoFormatada:
  horas: int
  minutos: int
  segundos: int
  centesimos: int = 0

  def __str__(self) -> str:
    """Formato digital HH:MM:SS.cs"""
    return (f"{self.horas:02d}:{self.minutos:02d}:{self.segundos:02d}.{self.centesimos:02d}")

  @property
  def texto_descritivo(self) -> str:
    """Formato por extenso idêntico ao programa.c original"""
    return f"{self.horas} hora(s), {self.minutos} minuto(s) e {self.segundos} segundo(s)"


def decompor_segundos(total_segundos: float) -> DuracaoFormatada:
  if total_segundos < 0:
    raise ValueError("A duração não pode ser negativa.")

  total_centesimos = int(round(total_segundos * 100))
  total_inteiro, centesimos = divmod(total_centesimos, 100)

  horas = total_inteiro // 3600
  resto = total_inteiro % 3600
  minutos = resto // 60
  segundos = resto % 60

  return DuracaoFormatada(horas, minutos, segundos, centesimos)


def calcular_aceleracao_tempo(
    duracao_segundos: float, velocidade: float
) -> DuracaoFormatada:
  if velocidade <= 0:
    raise ValueError("A velocidade de reprodução deve ser maior que zero.")
  return decompor_segundos(duracao_segundos / velocidade)


def converter_segundos(segundos: int) -> DuracaoFormatada:
  return decompor_segundos(float(segundos))


def converter_minutos(minutos: int) -> DuracaoFormatada:
  return decompor_segundos(float(minutos * 60))


def converter_horas(horas: int) -> DuracaoFormatada:
  return decompor_segundos(float(horas * 3600))


@dataclass(frozen=True)
class DecomposicaoTempoUniversal:
  segundos_totais: float
  em_segundos: float
  em_minutos: float
  em_horas: float
  em_dias: float
  em_semanas: float
  em_anos: float  # Base: 365 dias
  dias_inteiros: int
  anos_inteiros: int = 0
  romanos_dias: Optional[str] = None
  romanos_anos: Optional[str] = None


_FATORES_SEGUNDOS = {
    "segundos": 1.0,
    "minutos": 60.0,
    "horas": 3600.0,
    "dias": 86400.0,
    "semanas": 604800.0,
    "anos": 31_536_000.0,  # 365 dias
}

_TABELA_ROMANA = (
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
)


def converter_para_romanos(numero: int) -> Optional[str]:
  """Converte inteiro de 1 a 3999 para algarismos romanos."""
  if not isinstance(numero, int) or not 1 <= numero <= 3999:
    return None
  resultado = ""
  restante = numero
  for valor, simbolo in _TABELA_ROMANA:
    while restante >= valor:
      resultado += simbolo
      restante -= valor
  return resultado


def converter_unidade_tempo(
    valor: float, unidade_origem: str
) -> DecomposicaoTempoUniversal:
  """Normaliza 'valor' em segundos e projeta em todas as unidades."""
  unidade = unidade_origem.strip().lower()
  if unidade not in _FATORES_SEGUNDOS:
    raise ValueError(
        f"Unidade inválida: '{unidade_origem}'. "
        f"Use: {', '.join(_FATORES_SEGUNDOS)}."
    )
  if valor < 0:
    raise ValueError("O valor não pode ser negativo.")

  segundos_totais = valor * _FATORES_SEGUNDOS[unidade]
  dias_inteiros = int(segundos_totais // 86400)
  anos_inteiros = int(segundos_totais // 31_536_000)
  return DecomposicaoTempoUniversal(
      segundos_totais=segundos_totais,
      em_segundos=segundos_totais,
      em_minutos=segundos_totais / 60,
      em_horas=segundos_totais / 3600,
      em_dias=segundos_totais / 86400,
      em_semanas=segundos_totais / 604800,
      em_anos=segundos_totais / 31_536_000,
      dias_inteiros=dias_inteiros,
      anos_inteiros=anos_inteiros,
      romanos_dias=converter_para_romanos(dias_inteiros),
      romanos_anos=converter_para_romanos(anos_inteiros),
  )


BITRATE_MIN_KBPS = 150
BITRATE_MAX_KBPS = 50_000


def calcular_bitrate_alvo_kbps(
    duracao_segundos: float,
    tamanho_alvo_mb: float = 25.0,
    audio_bitrate_kbps: int = 96,
) -> int:
  if duracao_segundos <= 0:
    raise ValueError("Duração do vídeo deve ser superior a zero.")

  tamanho_total_kbits = tamanho_alvo_mb * 8192
  bitrate_total_kbps = tamanho_total_kbits / duracao_segundos
  bitrate_video_kbps = int(bitrate_total_kbps - audio_bitrate_kbps)

  return min(max(bitrate_video_kbps, BITRATE_MIN_KBPS), BITRATE_MAX_KBPS)


# Arte ASCII da Cruz de Malta (legado do programa.c)
ARTE_VASCO = """
VASCO
=  ========================  =
==  ======================  ==
===   ==================   ===
=====   ==============   =====
======    ==========   =======
========   ========   ========
==============================
==============================
========   ========   ========
======    ==========   =======
=====   ==============   =====
===   ==================   ===
==  ======================  ==
=  ========================  =
"""