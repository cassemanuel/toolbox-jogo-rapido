# Media Automation Toolkit

**Versão 2.5** (23/09/2026) — Toolkit multimídia desktop para Windows que automatiza:

- Compressão de vídeo com teto de tamanho (FFmpeg) e conversão direta de formato
- Otimização e conversão de imagens em lote (Pillow, paralelo)
- Manipulação de PDFs: unir, extrair, dividir, rotacionar, mix frente/verso, fatia por tamanho ou marcadores
- Calculadora de tempo (aceleração de playback e decomposição universal)
- Agendamento de hibernação com presets e contagem regressiva cancelável

## Requisitos

- Windows 10/11, Python 3.12+
- `pip install -r requirements.txt`
- FFmpeg + FFprobe em `bin/` ou no PATH

## Como Executar

**Desktop (GUI):**

```
dist\MediaToolkit.exe
# ou
python app.py
```

**Linha de comando (CLI):**

```
python cli.py <comando> --help
```

Subcomandos: `video`, `imagem`, `converter`, `pdf`, `calc`, `hibernar`, `vasco`.
Referência completa de flags e exemplos em [docs/CLI.md](docs/CLI.md).

## Build

```
python -m PyInstaller MediaToolkit.spec --noconfirm
```

Gera `dist\MediaToolkit.exe` (onefile). Para bundle 100% portátil, posicione
`ffmpeg.exe` e `ffprobe.exe` em `bin/` antes do build — o `.spec` os inclui
automaticamente.

## Documentação interna

- [docs/CLI.md](docs/CLI.md) — referência completa da linha de comando
- Botão **[ Tutorial & Changelog ]** na interface — guia rápido de uso e histórico de versões
