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
from core.binarios import gerar_destino_unico
from core.pdf import dividir_pdf, extrair_paginas, unir_pdfs
from core.imagem import (
    FORMATOS_CONVERSAO,
    FORMATOS_SAIDA,
    converter_imagem,
    otimizar_imagem,
    otimizar_lote,
)
from core.video import comprimir_video, converter_midia


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
    ext_saida = FORMATOS_SAIDA[args.formato]
    destino_arquivo = (
        destino
        if destino.suffix
        else gerar_destino_unico(
            destino, origem.stem, "otimizada", ext_saida
        )
    )
    res = otimizar_imagem(
        origem,
        destino_arquivo,
        args.max_dimensao,
        args.qualidade,
        formato_saida=args.formato,
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

  for res in otimizar_lote(
      origem, destino, args.max_dimensao, args.qualidade, args.formato
  ):
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

  if destino.suffix.lower() not in (".mp4", ".webm", ".mkv", ".mp3"):
    print("Erro: A saída deve ser .mp4, .webm, .mkv ou .mp3.")
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
  if res.bitrate_k > 0:
    print(f"Bitrate de Vídeo    : {res.bitrate_k} kbps")
  print(f"GPU Detectada       : {res.telemetria.modelo_gpu}")
  print(f"Uso CPU (Média/Pico): {res.telemetria.cpu_media:.1f}% / {res.telemetria.cpu_pico:.1f}%")
  print(f"Uso GPU (Média/Pico): {res.telemetria.gpu_media:.1f}% / {res.telemetria.gpu_pico:.1f}%")
  print(f"VRAM de Pico        : {res.telemetria.vram_pico_mb:.1f} MB")
  print("=" * 50)
  if res.aviso:
    print(f"[AVISO] {res.aviso}")


def tratar_converter(args: argparse.Namespace) -> None:
  origem = Path(args.origem)
  if not origem.is_file():
    print(f"Erro: Arquivo de origem '{origem}' não existe.")
    sys.exit(1)

  if args.destino:
    destino = Path(args.destino)
  elif args.formato:
    ext = args.formato if args.formato.startswith(".") else f".{args.formato}"
    destino = gerar_destino_unico(
        origem.parent, origem.stem, "convertido", ext
    )
  else:
    print("Erro: especifique --destino ou --formato.")
    sys.exit(1)

  ext_destino = destino.suffix.lower()
  if ext_destino in FORMATOS_CONVERSAO:
    res = converter_imagem(origem, destino)
  else:
    res = converter_midia(origem, destino, args.audio_bitrate)

  if not res.sucesso:
    print(f"[FALHA] {res.mensagem_erro}")
    sys.exit(1)

  final_kb = res.tamanho_final_bytes / 1024
  print(
      f"[OK] {res.caminho_destino} ({final_kb:.1f} KB,"
      f" {res.tempo_processamento_s:.2f}s)"
  )


def tratar_pdf_unir(args: argparse.Namespace) -> None:
  arquivos = [Path(p) for p in args.arquivos]
  if args.destino:
    destino = Path(args.destino)
  else:
    destino = gerar_destino_unico(
        arquivos[0].parent, "unificado", "pdf", ".pdf"
    )
  res = unir_pdfs(arquivos, destino)
  if not res.sucesso:
    print(f"[FALHA] {res.mensagem_erro}")
    sys.exit(1)
  print(f"[OK] {res.caminho_destino} ({res.total_paginas} páginas)")


def tratar_pdf_extrair(args: argparse.Namespace) -> None:
  origem = Path(args.origem)
  try:
    paginas = [int(p.strip()) for p in args.paginas.split(",") if p.strip()]
  except ValueError:
    print("Erro: --paginas deve ser uma lista numérica (ex: 1,3,5).")
    sys.exit(1)
  if args.destino:
    destino = Path(args.destino)
  else:
    destino = gerar_destino_unico(
        origem.parent, origem.stem, "extraido", ".pdf"
    )
  res = extrair_paginas(origem, paginas, destino)
  if not res.sucesso:
    print(f"[FALHA] {res.mensagem_erro}")
    sys.exit(1)
  print(f"[OK] {res.caminho_destino} ({res.total_paginas} página(s))")


def tratar_pdf_dividir(args: argparse.Namespace) -> None:
  origem = Path(args.origem)
  pasta = Path(args.destino) if args.destino else origem.parent / "paginas"
  resultados = dividir_pdf(origem, pasta)
  sucessos = sum(1 for r in resultados if r.sucesso)
  for r in resultados:
    if r.sucesso:
      print(f"  [OK] {r.caminho_destino.name}")
    else:
      print(f"  [ERRO] {r.mensagem_erro}")
  if sucessos == 0:
    sys.exit(1)
  print(f"[OK] {sucessos}/{len(resultados)} página(s) em {pasta}")


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
      "--qualidade", type=int, default=80, help="Qualidade JPEG/WEBP (1-100)"
  )
  p_img.add_argument(
      "--formato",
      choices=list(FORMATOS_SAIDA.keys()),
      default="JPEG",
      help="Formato de saída",
  )
  p_img.set_defaults(func=tratar_imagem)

  # Subcomando video
  p_vid = subparsers.add_parser("video", help="Compressão de vídeo")
  p_vid.add_argument(
      "--origem", type=str, required=True, help="Vídeo de entrada"
  )
  p_vid.add_argument(
      "--destino",
      type=str,
      required=True,
      help="Saída (.mp4/.webm/.mkv/.mp3)"
  )
  p_vid.add_argument(
      "--tamanho", type=float, default=25.0, help="Tamanho alvo em MB"
  )
  p_vid.add_argument(
      "--audio-bitrate", type=int, default=96, help="Bitrate do áudio em kbps"
  )
  p_vid.set_defaults(func=tratar_video)

  # Subcomando converter
  p_conv = subparsers.add_parser(
      "converter", help="Conversão direta de formato (sem teto de tamanho)"
  )
  p_conv.add_argument(
      "--origem", type=str, required=True, help="Arquivo de entrada"
  )
  p_conv.add_argument(
      "--destino", type=str, help="Caminho de destino completo"
  )
  p_conv.add_argument(
      "--formato",
      type=str,
      help="Extensão de destino (ex: mp4, mp3, webp) quando --destino "
      "não for informado",
  )
  p_conv.add_argument(
      "--audio-bitrate",
      type=int,
      default=192,
      help="Bitrate de áudio em kbps (vídeo/áudio)",
  )
  p_conv.set_defaults(func=tratar_converter)

  # Subcomando pdf (unir / extrair / dividir)
  p_pdf = subparsers.add_parser("pdf", help="Manipulação de PDFs")
  pdf_sub = p_pdf.add_subparsers(
      dest="acao_pdf", required=True, help="Ação de PDF"
  )

  p_unir = pdf_sub.add_parser("unir", help="Mescla PDFs em ordem")
  p_unir.add_argument(
      "--arquivos", nargs="+", required=True, help="PDFs de entrada"
  )
  p_unir.add_argument("--destino", type=str, help="PDF de saída")
  p_unir.set_defaults(func=tratar_pdf_unir)

  p_ext = pdf_sub.add_parser(
      "extrair", help="Extrai páginas específicas (1-based)"
  )
  p_ext.add_argument("--origem", type=str, required=True)
  p_ext.add_argument(
      "--paginas", type=str, required=True, help="Ex: 1,3,5"
  )
  p_ext.add_argument("--destino", type=str, help="PDF de saída")
  p_ext.set_defaults(func=tratar_pdf_extrair)

  p_div = pdf_sub.add_parser(
      "dividir", help="Salva cada página em arquivo próprio"
  )
  p_div.add_argument("--origem", type=str, required=True)
  p_div.add_argument("--destino", type=str, help="Pasta de saída")
  p_div.set_defaults(func=tratar_pdf_dividir)

  # Subcomando vasco
  p_vasco = subparsers.add_parser("vasco", help="Exibe a Cruz de Malta legada")
  p_vasco.set_defaults(func=lambda _: print(ARTE_VASCO))

  args = parser.parse_args()
  args.func(args)


if __name__ == "__main__":
  main()