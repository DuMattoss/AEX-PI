"""Prepara o ambiente local e inicia o servidor de desenvolvimento."""
import argparse
import hashlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser


ROOT = Path(__file__).resolve().parent.parent


def executar(comando):
    subprocess.run(comando, cwd=ROOT, check=True)


def preparar():
    if sys.version_info < (3, 10):
        raise RuntimeError('Instale Python 3.10 ou superior e tente novamente.')
    if not (ROOT / 'manage.py').is_file() or not (ROOT / 'requirements.txt').is_file():
        raise RuntimeError('Mantenha o iniciador dentro da pasta completa do projeto.')
    ambiente = ROOT / '.venv'
    python = ambiente / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.is_file():
        print('Criando o ambiente do projeto...', flush=True)
        executar([sys.executable, '-m', 'venv', str(ambiente)])
    requisitos = hashlib.sha256((ROOT / 'requirements.txt').read_bytes()).hexdigest()
    marcador = ambiente / 'cooperativa-requisitos.sha256'
    instalado = marcador.read_text().strip() if marcador.is_file() else ''
    verificacao = subprocess.run([str(python), '-c', 'import django'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if instalado != requisitos or verificacao.returncode != 0:
        print('Instalando as dependencias. Na primeira vez, aguarde...', flush=True)
        executar([str(python), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', 'requirements.txt'])
        marcador.write_text(requisitos, encoding='ascii')
    banco = ROOT / 'db.sqlite3'
    novo = not banco.exists() or banco.stat().st_size == 0
    print('Conferindo o banco de dados...', flush=True)
    executar([str(python), 'manage.py', 'migrate', '--noinput'])
    if novo:
        print('Criando as contas e os dados de demonstracao...', flush=True)
        executar([str(python), 'manage.py', 'popular_demo'])
    return python


def porta_livre():
    for porta in range(8000, 8021):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as teste:
            try:
                teste.bind(('127.0.0.1', porta))
            except OSError:
                continue
            return porta
    raise RuntimeError('As portas de 8000 a 8020 estao em uso. Feche um servidor e tente novamente.')


def encerrar(processo):
    if processo.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(processo.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        processo.terminate()
    try:
        processo.wait(timeout=5)
    except subprocess.TimeoutExpired:
        processo.kill()


def iniciar(python, abrir_navegador=True):
    porta = porta_livre()
    endereco = f'http://127.0.0.1:{porta}/'
    processo = subprocess.Popen([str(python), 'manage.py', 'runserver', f'127.0.0.1:{porta}', '--noreload'], cwd=ROOT)
    try:
        limite = time.monotonic() + 30
        while time.monotonic() < limite:
            if processo.poll() is not None:
                raise RuntimeError('O servidor encerrou durante a inicializacao. Confira a mensagem acima.')
            try:
                with urlopen(endereco, timeout=1) as resposta:
                    if resposta.status == 200:
                        break
            except (URLError, TimeoutError, OSError):
                time.sleep(0.25)
        else:
            raise RuntimeError('O servidor nao respondeu em 30 segundos. Tente iniciar novamente.')
        print(f'\nEndereco: {endereco}', flush=True)
        print('Login de demonstracao: demo | Senha inicial: Coopera123!', flush=True)
        print('Deixe esta janela aberta enquanto usa o sistema. Para encerrar, pressione Ctrl+C.\n', flush=True)
        if abrir_navegador:
            try:
                if not webbrowser.open(endereco):
                    print('Abra o endereco acima no navegador.', flush=True)
            except webbrowser.Error:
                print('Abra o endereco acima no navegador.', flush=True)
        return processo.wait()
    finally:
        encerrar(processo)


def main():
    parser = argparse.ArgumentParser(description='Preparar e iniciar a cooperativa.')
    parser.add_argument('--sem-navegador', action='store_true', help='Iniciar sem abrir o navegador automaticamente.')
    args = parser.parse_args()
    try:
        return iniciar(preparar(), abrir_navegador=not args.sem_navegador)
    except KeyboardInterrupt:
        print('\nServidor encerrado. Os dados continuam salvos no banco.', flush=True)
        return 0
    except (RuntimeError, OSError, subprocess.CalledProcessError) as erro:
        print(f'\nNao foi possivel iniciar: {erro}', file=sys.stderr, flush=True)
        print('Confira se o Python esta instalado e se ha internet para instalar as dependencias na primeira execucao.', file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
