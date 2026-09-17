# Media Automation Toolkit

Toolkit multimídia desktop para Windows que automatiza três domínios:

- **Compressão de Vídeo com teto de tamanho** — recodifica via FFmpeg (H.264/MP4 ou VP9/WebM) calculando o bitrate alvo a partir da duração, para caber em ~25 MB. Telemetria de hardware (CPU/RAM/GPU/VRAM), progresso contínuo via `-progress pipe:1` e cancelamento gracioso.
- **Otimização de Imagens em lote** — redimensionamento e recompressão JPEG via Pillow com processamento paralelo, correção de orientação EXIF e preservação do perfil de cor ICC.
- **Calculadora de Tempo** — port do utilitário legado em C (`programa.c`): conversões HH:MM:SS e tempo ajustado por fator de playback.

## Requisitos

- Windows 10/11, Python 3.12+
- Dependências Python: `pip install -r requirements.txt`
- **FFmpeg + FFprobe** disponíveis via `bin/` local ou no PATH (ver seção de build)

## Como Executar — Modo Desktop (GUI)

**Executável autônomo:**

```
dist\MediaToolkit.exe
```

**Via código-fonte:**

```
python app.py
```

A interface (`customtkinter`) oferece quatro abas: Compressão de Vídeo (teto de MB com barra de progresso e cancelamento), Otimização de Imagens (arquivo único ou pasta em lote), Conversão de Mídia (troca de formato direta, sem teto) e Calculadora de Tempo. Todas as abas de mídia incluem botão "Abrir Pasta de Destino" sempre ativo.

## Como Executar — Linha de Comando (CLI)

### Compressão de vídeo e conversão de formato

```
python cli.py video --origem entrada.mp4 --destino saida.mp4 --tamanho 25 --audio-bitrate 96
python cli.py video --origem entrada.mov --destino saida.mkv  --tamanho 25
python cli.py video --origem entrada.mp4 --destino audio.mp3  --audio-bitrate 192   # extrai só o áudio
```

Formatos de saída: `.mp4`, `.webm`, `.mkv` (H.264/VP9 com teto de tamanho) e `.mp3` (extração de áudio via libmp3lame — `--tamanho` não se aplica). Valores de bitrate fora da faixa executável geram aviso e clamp automático (piso 150 kbps / teto 50 Mbps).

### Otimização de imagem — arquivo único

```
python cli.py imagem --origem foto.png --destino foto_otimizada.jpg --qualidade 85
python cli.py imagem --origem foto.jpg --destino saida.webp --formato WEBP --qualidade 90
```

`--formato` aceita `JPEG` (fundo branco sobre transparência), `PNG` (preserva alfa) e `WEBP` (preserva alfa).

### Otimização de imagem — pasta em lote

Quando `--origem` é um diretório, o modo lote é ativado automaticamente (processamento paralelo):

```
python cli.py imagem --origem pasta/fotos/ --destino pasta/otimizadas/ --max-dimensao 1920 --qualidade 80 --formato WEBP
```

### Conversão direta de formato (sem teto de tamanho)

```
python cli.py converter --origem video.avi --formato mkv
python cli.py converter --origem video.mp4 --formato mp3 --audio-bitrate 192
python cli.py converter --origem foto.png  --formato webp
python cli.py converter --origem video.mov --destino saida.mp4
```

- **Vídeo→Vídeo** (`.mp4 .mkv .avi .mov .webm`): transcodificação com preservação de qualidade (CRF), sem compressão por teto de MB.
- **Vídeo→Áudio** (`.mp3 .wav .aac`): extração com `-vn` (libmp3lame/pcm_s16le/aac).
- **Imagem→Imagem** (`.png .jpg .webp .ico .bmp`): conversão 1:1 via Pillow sem redimensionamento; alfa preservado quando suportado.

### Calculadora de tempo

```
python cli.py calc --minutos 90 --velocidade 1.5     # 90 min a 1.5x -> 01:00:00.00
python cli.py calc --segundos 5025                    # conversão para HH:MM:SS
python cli.py calc --minutos-totais 90
python cli.py calc --horas 2
python cli.py vasco                                   # ASCII art legada
```

## Build com PyInstaller

```
pyinstaller MediaToolkit.spec --noconfirm
```

Gera `dist\MediaToolkit.exe` (onefile, `console=False`, UPX desabilitado).

### Distribuição 100% portável

Para eliminar a dependência de FFmpeg instalado no PATH, posicione os binários estáticos antes do build:

```
bin/
  ffmpeg.exe
  ffprobe.exe
```

O `.spec` inclui `bin/` automaticamente no bundle. Em runtime, `core/binarios.py` resolve na ordem: `sys._MEIPASS/bin/` (congelado) → `bin/` local (dev) → `PATH`.

## Arquitetura e Segurança de Execução

- **Isolamento de threads (Tkinter)**: workers nunca tocam widgets — despacham resultados via `queue.Queue` drenada no mainloop (`after`), eliminando `RuntimeError: main thread is not in main loop`.
- **Barreira contra processos órfãos**: handles `Popen` registrados em set global; no fechamento da janela (`WM_DELETE_WINDOW`) a árvore é terminada via `taskkill /F /T` e arquivos parciais são expurgados.
- **Subprocessos silenciosos**: `CREATE_NO_WINDOW` em todas as chamadas — zero flicker de console no modo gráfico.
- **DTOs imutáveis**: `ResultadoCompressao`, `ResultadoCompressaoVideo` e `EstatisticasHardware` são `@dataclass(frozen=True)` — contratos estritos entre core, CLI e GUI.
- **Resiliência de I/O**: criação de diretórios e iteração sob `try/except OSError`; falhas retornam DTOs de erro em vez de exceções.
- **Paralelismo de imagens**: `ThreadPoolExecutor` (Pillow libera a GIL nas rotinas C de resize/save) com `as_completed` — resultados fluem progressivamente e falhas são isoladas por arquivo.

## Engenharia e Ferramental

Desenvolvido com assistência do agente **Devin AI** (Cognition): auditoria arquitetural, saneamento do repositório, correções de runtime P0/P1, telemetria contínua e empacotamento PyInstaller — evolução registrada em commits atômicos no histórico do Git.
