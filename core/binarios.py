"""Resolução de executáveis externos (ffmpeg/ffprobe).

Ordem de busca: bundle do PyInstaller (sys._MEIPASS/bin), pasta local
bin/ na raiz do projeto e, por fim, o PATH do sistema.
"""

from datetime import datetime
from pathlib import Path
import shutil
import sys


def obter_diretorio_base() -> Path:
    """Diretório raiz visível ao usuário: pasta do .exe quando congelado
    pelo PyInstaller, ou raiz do projeto em desenvolvimento."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def obter_diretorio_input_output() -> Path:
    """Pasta padrão de entrada/saída, criada sob demanda."""
    pasta = obter_diretorio_base() / "input-output"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def resolver_executavel(nome: str) -> str:
    if getattr(sys, "frozen", False):
        candidato = Path(sys._MEIPASS) / "bin" / f"{nome}.exe"
        if candidato.is_file():
            return str(candidato)

    candidato_local = obter_diretorio_base() / "bin" / f"{nome}.exe"
    if candidato_local.is_file():
        return str(candidato_local)

    return shutil.which(nome) or nome


def gerar_destino_unico(
    pasta: Path,
    stem: str,
    operacao: str,
    extensao: str,
    reservados: set[Path] | None = None,
) -> Path:
    """Gera '{stem}_{operacao}_{AAAAMMDD_HHMMSS}{ext}' sem colisão:
    incrementa sufixo numérico se o arquivo já existir em disco ou já
    tiver sido reservado no lote atual."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidato = pasta / f"{stem}_{operacao}_{stamp}{extensao}"
    contador = 1
    while candidato.exists() or (reservados and candidato in reservados):
        contador += 1
        candidato = pasta / f"{stem}_{operacao}_{stamp}_{contador}{extensao}"
    if reservados is not None:
        reservados.add(candidato)
    return candidato
