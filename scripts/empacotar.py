"""Empacota somente os arquivos portáveis da aplicação, sem banco ou ambiente local."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'entrega' / 'cooperativa-aex.zip'
OUT.parent.mkdir(exist_ok=True)
IGNORAR = {'.venv', '__pycache__', 'backups', 'tmp', '.git'}
with ZipFile(OUT, 'w', ZIP_DEFLATED) as arquivo:
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(part in IGNORAR for part in relative.parts):
            continue
        if path.suffix in {'.sqlite3', '.zip', '.pyc'} or path.name.startswith('.env'):
            continue
        arquivo.write(path, Path('cooperativa') / relative)
print(OUT)
