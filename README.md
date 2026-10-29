# Sistema de gestão da cooperativa de reciclagem

Projeto acadêmico da AEX de Programação para Internet, desenvolvido com Python e Django. O sistema organiza pesagens, classificações de materiais, estoque, vendas e cadastros de cooperados.

## Tecnologias

- Python 3.10 ou superior.
- Django 5.2.18, com arquitetura MVT e Django ORM.
- SQLite.
- Django Templates, HTML, CSS e JavaScript.

## Instalação

Abra um terminal na pasta `versao_inicial`:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py popular_demo
```

## Iniciar o sistema

```powershell
.venv\Scripts\python.exe manage.py runserver
```

Acesse `http://127.0.0.1:8000/`.

Com o ambiente virtual ativado, o comando é `python manage.py runserver`. O arquivo `iniciar-cooperativa.cmd` também inicia o servidor após a instalação.

No Linux ou macOS, use `.venv/bin/python` no lugar de `.venv\Scripts\python.exe`.

## Contas de demonstração

O comando `popular_demo` cria contas e dados fictícios para apresentação. Pode ser executado novamente sem duplicar os movimentos.

| Login | Cargo |
| --- | --- |
| demo | Presidente |
| diretoria | Diretoria |
| cooperado | Cooperado |

Senha inicial das três contas: `Coopera123!`.

Para administrar o Django, crie uma conta com `python manage.py createsuperuser`.

## Estrutura

```text
versao_inicial/
├── manage.py
├── requirements.txt
├── README.md
├── iniciar-cooperativa.cmd
├── config/                 # Configurações, URLs principais e WSGI
├── core/                   # Models, forms, views, serviços e testes
│   ├── migrations/
│   └── management/commands/
├── templates/              # Páginas HTML e base compartilhada
├── static/                 # CSS e JavaScript
├── scripts/                # Utilitários do projeto
├── referencias/            # Imagens dos protótipos
└── db.sqlite3              # Banco criado pelas migrations
```

Os models representam os materiais, as classificações, os perfis, as pesagens e os movimentos. As views recebem os formulários, consultam o banco e preparam os dados das páginas. Os templates apresentam a interface, com layout adaptado para computador e celular.

## Dados

O banco fica em `db.sqlite3`, na mesma pasta de `manage.py`. Fechar o servidor não apaga os registros.

As pesagens registram material, data e peso recebido. A classificação distribui esse peso entre os itens do catálogo. O estoque físico inclui os itens pendentes de classificação; somente os classificados ficam disponíveis para venda. Os cálculos de peso e valor usam Decimal, e a gravação da venda é feita em transação.

Os cargos controlam o acesso às páginas: cooperado, diretoria e presidente. O presidente administra os cadastros; a diretoria e o presidente têm acesso às vendas e aos dados financeiros.

## Verificações

```powershell
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py test
```

## Acesso pela rede local

No computador que executa o sistema, identifique o IPv4 com `ipconfig` e substitua o endereço do exemplo:

```powershell
$env:DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost,192.168.1.20"
.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

No celular conectado à mesma rede, abra `http://192.168.1.20:8000/`. Utilize o servidor de desenvolvimento somente em uma rede confiável.
