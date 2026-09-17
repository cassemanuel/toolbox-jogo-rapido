"""Ponto de entrada unificado via linha de comando para o toolkit multimídia."""

import argparse
from pathlib import Path
import sys

from core.calculadora import (
    ARTE_VASCO,
    calcular_aceleracao_tempo,
    converter_horas,
    converter_minutos,
    converter_segundos,
)
from core.imagem import otimizar_imagem, otimizar_lote
from core.video import comprimir_video


def tratar_calc(args: argparse.Namespace) -> None:
  if args.minutos is not None and args.velocidade is not None:
    duracao_original = args.minutos * 60.0
    resultado = calcular_aceleracao_tempo(duracao_original, args.velocidade)
    print(f"Tempo Original : {args.minutos:.2f} min")
    print(f"Velocidade     : {args.velocidade:.2f}x")
    print(f"Tempo Ajustado : {resultado}")
  elif args.segundos is not None:
    print(f"Resultado: {converter_segundos(int(args.segundos))}")
  elif args.minutos_totais is not None:
    print(f"Resultado: {converter_minutos(int(args.minutos_totais))}")
  elif args.horas is not None:
    print(f"Resultado: {converter_horas(int(args.horas))}")
  else:
    print(
        "Erro: Especifique (--minutos e --velocidade) ou uma flag de conversão."
    )
    sys.exit(1)


def tratar_imagem(args: argparse.Namespace) -> None:
  origem = Path(args.origem)
  destino = Path(args.destino)

  if not origem.exists():
    print(f"Erro: O caminho de origem '{origem}' não existe.")
    sys.exit(1)

  if origem.is_file():
    destino_arquivo = (
        destino if destino.suffix else destino / f"{origem.stem}_otimizada.jpg"
    )
    res = otimizar_imagem(
        origem, destino_arquivo, args.max_dimensao, args.qualidade
    )
    if res.sucesso:
      print(
          f"[OK] {res.caminho_origem.name} ->"
          f" {res.tamanho_final_bytes / 1024:.1f} KB"
      )
    else:
      print(f"[FALHA] {res.caminho_origem.name}: {res.mensagem_erro}")
      sys.exit(1)
    return

  print(f"Processando lote em: {origem}")
  total = 0
  sucessos = 0
  bytes_antes = 0
  bytes_depois = 0

  for res in otimizar_lote(origem, destino, args.max_dimensao, args.qualidade):
    total += 1
    if res.sucesso:
      sucessos += 1
      bytes_antes += res.tamanho_original_bytes
      bytes_depois += res.tamanho_final_bytes
      print(
          f"  [{sucessos}] {res.caminho_origem.name} ->"
          f" {res.tamanho_final_bytes / 1024:.1f} KB"
      )
    else:
      print(f"  [ERRO] {res.caminho_origem.name}: {res.mensagem_erro}")

  if total == 0:
    print("Nenhuma imagem válida encontrada.")
    return

  economia_mb = (bytes_antes - bytes_depois) / (1024 * 1024)
  print("\n--- Resumo de Compressão ---")
  print(f"Imagens processadas : {sucessos}/{total}")
  print(f"Espaço economizado  : {economia_mb:.2f} MB")


def tratar_video(args: argparse.Namespace) -> None:
  origem = Path(args.origem)
  destino = Path(args.destino)

  if not origem.is_file():
    print(f"Erro: Arquivo de vídeo '{origem}' não existe.")
    sys.exit(1)

  if destino.suffix.lower() not in (".mp4", ".webm"):
    print("Erro: A extensão do arquivo de saída deve ser .mp4 ou .webm.")
    sys.exit(1)

  print(f"Iniciando codificação de '{origem.name}' para '{destino.name}'...")
  res = comprimir_video(origem, destino, args.tamanho, args.audio_bitrate)

  if not res.sucesso:
    print(f"[FALHA] Erro na codificação: {res.mensagem_erro}")
    sys.exit(1)

  tamanho_final_mb = res.tamanho_final_bytes / (1024 * 1024)
  print("\n" + "=" * 50)
  print("STATUS              : SUCESSO")
  print(f"Arquivo Final       : {res.caminho_destino} ({tamanho_final_mb:.2f} MB)")
  print(f"Bitrate de Vídeo    : {res.bitrate_k} kbps")
  print(f"GPU Detectada       : {res.telemetria.modelo_gpu}")
  print(f"Uso CPU (Média/Pico): {res.telemetria.cpu_media:.1f}% / {res.telemetria.cpu_pico:.1f}%")
  print(f"Uso GPU (Média/Pico): {res.telemetria.gpu_media:.1f}% / {res.telemetria.gpu_pico:.1f}%")
  print(f"VRAM de Pico        : {res.telemetria.vram_pico_mb:.1f} MB")
  print("=" * 50)
  if res.aviso:
    print(f"[AVISO] {res.aviso}")


def main() -> None:
  parser = argparse.ArgumentParser(
      description="Toolkit Unificado de Automação de Mídia e Cálculos"
  )
  subparsers = parser.add_subparsers(
      dest="comando", required=True, help="Subcomandos disponíveis"
  )

  # Subcomando calc
  p_calc = subparsers.add_parser("calc", help="Cálculos de tempo e aceleração")
  p_calc.add_argument("--minutos", type=float, help="Duração base em minutos")
  p_calc.add_argument(
      "--velocidade", type=float, help="Multiplicador de velocidade"
  )
  p_calc.add_argument(
      "--segundos", type=int, help="Converte segundos para HH:MM:SS"
  )
  p_calc.add_argument(
      "--minutos-totais", type=int, help="Converte minutos para HH:MM:SS"
  )
  p_calc.add_argument("--horas", type=int, help="Converte horas para HH:MM:SS")
  p_calc.set_defaults(func=tratar_calc)

  # Subcomando imagem
  p_img = subparsers.add_parser("imagem", help="Otimização de imagens")
  p_img.add_argument(
      "--origem", type=str, required=True, help="Caminho de entrada"
  )
  p_img.add_argument(
      "--destino", type=str, required=True, help="Caminho de saída"
  )
  p_img.add_argument(
      "--max-dimensao", type=int, default=1920, help="Limite em pixels"
  )
  p_img.add_argument(
      "--qualidade", type=int, default=80, help="Qualidade JPEG (1-100)"
  )
  p_img.set_defaults(func=tratar_imagem)

  # Subcomando video
  p_vid = subparsers.add_parser("video", help="Compressão de vídeo")
  p_vid.add_argument(
      "--origem", type=str, required=True, help="Vídeo de entrada"
  )
  p_vid.add_argument(
      "--destino", type=str, required=True, help="Saída (.mp4/.webm)"
  )
  p_vid.add_argument(
      "--tamanho", type=float, default=25.0, help="Tamanho alvo em MB"
  )
  p_vid.add_argument(
      "--audio-bitrate", type=int, default=96, help="Bitrate do áudio em kbps"
  )
  p_vid.set_defaults(func=tratar_video)

  # Subcomando vasco
  p_vasco = subparsers.add_parser("vasco", help="Exibe a Cruz de Malta legada")
  p_vasco.set_defaults(func=lambda _: print(ARTE_VASCO))

  args = parser.parse_args()
  args.func(args)


if __name__ == "__main__":
  main()