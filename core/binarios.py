"""Resolução de executáveis externos (ffmpeg/ffprobe).

Ordem de busca: bundle do PyInstaller (sys._MEIPASS/bin), pasta local
bin/ na raiz do projeto e, por fim, o PATH do sistema.
"""

from pathlib import Path
import shutil
import sys


def resolver_executavel(nome: str) -> str:
    if getattr(sys, "frozen", False):
        candidato = Path(sys._MEIPASS) / "bin" / f"{nome}.exe"
        if candidato.is_file():
            return str(candidato)

    raiz_projeto = Path(__file__).resolve().parent.parent
    candidato_local = raiz_projeto / "bin" / f"{nome}.exe"
    if candidato_local.is_file():
        return str(candidato_local)

    return shutil.which(nome) or nome
