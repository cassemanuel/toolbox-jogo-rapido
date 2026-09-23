# Referência da Linha de Comando (CLI)

Uso geral: `python cli.py <comando> [flags]`. Todos os destinos omitidos
recebem timestamp automático (`{stem}_{operacao}_{AAAAMMDD_HHMMSS}`) —
nunca sobrescrevem arquivos existentes.

## video — compressão com teto de tamanho

```
python cli.py video --origem entrada.mp4 --destino saida.mp4 --tamanho 25 --audio-bitrate 96
python cli.py video --origem entrada.mov --destino saida.mkv  --tamanho 25
python cli.py video --origem entrada.mp4 --destino audio.mp3  --audio-bitrate 192   # extrai só o áudio
```

Formatos de saída: `.mp4`, `.webm`, `.mkv` (H.264/VP9 com teto de tamanho) e
`.mp3` (extração de áudio via libmp3lame — `--tamanho` não se aplica).
Bitrate fora da faixa executável gera aviso e clamp automático
(piso 150 kbps / teto 50 Mbps).

## imagem — otimização (arquivo único ou lote)

```
python cli.py imagem --origem foto.png --destino foto_otimizada.jpg --qualidade 85
python cli.py imagem --origem foto.jpg --destino saida.webp --formato WEBP --qualidade 90
```

`--formato` aceita `JPEG` (fundo branco sobre transparência), `PNG`
(preserva alfa) e `WEBP` (preserva alfa).

Quando `--origem` é um diretório, o modo lote é ativado automaticamente
(processamento paralelo):

```
python cli.py imagem --origem pasta/fotos/ --destino pasta/otimizadas/ --max-dimensao 1920 --qualidade 80 --formato WEBP
```

## converter — conversão direta de formato (sem teto de tamanho)

```
python cli.py converter --origem video.avi --formato mkv
python cli.py converter --origem video.mp4 --formato mp3 --audio-bitrate 192
python cli.py converter --origem foto.png  --formato webp
python cli.py converter --origem video.mov --destino saida.mp4
```

- **Vídeo→Vídeo** (`.mp4 .mkv .avi .mov .webm`): transcodificação CRF, sem
  compressão por teto de MB.
- **Vídeo→Áudio** (`.mp3 .wav .aac`): extração com `-vn`
  (libmp3lame/pcm_s16le/aac).
- **Imagem→Imagem** (`.png .jpg .webp .ico .bmp`): conversão 1:1 via Pillow
  sem redimensionamento; alfa preservado quando suportado.

## pdf — manipulação de documentos

```
python cli.py pdf unir --arquivos doc1.pdf doc2.pdf [--destino unificado.pdf]
python cli.py pdf extrair --origem doc.pdf --paginas 1,3,5 [--destino extraido.pdf]
python cli.py pdf dividir --origem doc.pdf [--destino pasta/]
python cli.py pdf rotacionar --origem doc.pdf --angulo 90 [--paginas 1,3] [--destino saida.pdf]
python cli.py pdf mix --arquivo-a frentes.pdf --arquivo-b versos.pdf [--inverter-b] [--destino mix.pdf]
python cli.py pdf dividir-tamanho --origem doc.pdf --teto-mb 10 [--destino pasta/]
python cli.py pdf dividir-marcadores --origem doc.pdf [--nivel 1] [--destino pasta/]
```

- **unir**: mescla os PDFs na ordem informada.
- **extrair**: páginas em índice 1-based, validadas contra o total do documento.
- **dividir**: salva cada página em arquivo próprio (default: pasta `paginas/`).
- **rotacionar**: gira todas ou só as páginas listadas em 90/180/270°.
- **mix**: intercala A1,B1,A2,B2…; `--inverter-b` usa B na ordem reversa
  (versos escaneados ao contrário). Excedentes são anexados ao final.
- **dividir-tamanho**: fatia em blocos de até `--teto-mb` MB (default:
  `blocos/`); página que sozinha excede o teto vira bloco próprio.
- **dividir-marcadores**: fatia nos pontos do sumário/outline no `--nivel`
  indicado (default: `secoes/`); falha com mensagem clara sem marcadores.

## calc — calculadora de tempo

```
python cli.py calc --minutos 90 --velocidade 1.5     # 90 min a 1.5x -> 01:00:00.00
python cli.py calc --segundos 5025                   # conversão para HH:MM:SS
python cli.py calc --minutos-totais 90
python cli.py calc --horas 2
python cli.py calc --converter 120 --de horas        # decomposição universal + romanos
```

O conversor universal aceita `segundos|minutos|horas|dias|semanas|anos`
(ano = 365 dias) e projeta o valor em todas as unidades; totais de 1–3999
dias inteiros exibem também o equivalente em algarismos romanos.

## hibernar / vasco

```
python cli.py hibernar --segundos 700    # agenda shutdown /h (Ctrl+C aborta)
python cli.py vasco                      # ASCII art legada
```

## Arquitetura e Segurança de Execução

- **Isolamento de threads (Tkinter)**: workers nunca tocam widgets —
  despacham resultados via `queue.Queue` drenada no mainloop (`after`).
- **Barreira contra processos órfãos**: handles `Popen` registrados em set
  global; no fechamento (`WM_DELETE_WINDOW`) a árvore é terminada via
  `taskkill /F /T` e arquivos parciais são expurgados.
- **Subprocessos silenciosos**: `CREATE_NO_WINDOW` em todas as chamadas.
- **DTOs imutáveis**: `ResultadoCompressao`, `ResultadoCompressaoVideo` e
  `EstatisticasHardware` são `@dataclass(frozen=True)` — contratos entre
  core, CLI e GUI.
- **Paralelismo de imagens**: `ThreadPoolExecutor` (Pillow libera a GIL nas
  rotinas C) com `as_completed` — resultados progressivos, falhas isoladas.
