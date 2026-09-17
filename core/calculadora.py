"""Módulo de cálculos aritméticos de tempo e alocação de bitrate."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DuracaoFormatada:
  horas: int
  minutos: int
  segundos: int
  milisegundos: float = 0.0

  def __str__(self) -> str:
    """Formato digital HH:MM:SS.ms"""
    return (f"{self.horas:02d}:{self.minutos:02d}:{self.segundos:02d}.{int(self.milisegundos * 100):02d}")

  @property
  def texto_descritivo(self) -> str:
    """Formato por extenso idêntico ao programa.c original"""
    return f"{self.horas} hora(s), {self.minutos} minuto(s) e {self.segundos} segundo(s)"


def decompor_segundos(total_segundos: float) -> DuracaoFormatada:
  if total_segundos < 0:
    raise ValueError("A duração não pode ser negativa.")

  total_inteiro = int(total_segundos)
  milisegundos = round(total_segundos - total_inteiro, 2)

  horas = total_inteiro // 3600
  resto = total_inteiro % 3600
  minutos = resto // 60
  segundos = resto % 60

  return DuracaoFormatada(horas, minutos, segundos, milisegundos)


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

  return max(bitrate_video_kbps, 150)


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