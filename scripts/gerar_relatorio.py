"""Gera o relatório acadêmico de duas páginas. Dependência opcional: reportlab."""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'entrega'
OUT.mkdir(exist_ok=True)
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TituloAEX', fontName='Helvetica-Bold', fontSize=20, leading=24, spaceAfter=12))
styles.add(ParagraphStyle(name='TextoAEX', fontName='Helvetica', fontSize=10, leading=14, spaceAfter=8))
styles.add(ParagraphStyle(name='SecaoAEX', fontName='Helvetica-Bold', fontSize=12, leading=16, spaceBefore=8, spaceAfter=7))
styles.add(ParagraphStyle(name='LegendaAEX', fontName='Helvetica', fontSize=9, leading=12, alignment=TA_CENTER, spaceAfter=6))


def p(text, style='TextoAEX'):
    return Paragraph(text, styles[style])


def screenshot(name, width):
    img = Image(str(ROOT / 'verificacao' / name))
    img.drawHeight = img.imageHeight * width / img.imageWidth
    img.drawWidth = width
    return img


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#dddddd'))
    canvas.line(42, 34, 553, 34)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#555555'))
    canvas.drawString(42, 22, 'AEX - Programação para Internet / Engenharia de Software II - 28/10/2026')
    canvas.drawRightString(553, 22, str(doc.page))
    canvas.restoreState()


story = [p('Sistema de gestão de estoque e produção para cooperativa de reciclagem', 'TituloAEX'),
    p('<b>UENP - Campus Luiz Meneghel</b><br/>AEX de Programação para Internet integrada a Engenharia de Software II.'),
    p('<b>Integrantes:</b> Anna Laura Balmiza Soares, Eduardo Barbeito Mattos, Sabryna da Silva Moretto e Vitória Eduarda de Souza.'),
    p('Implementação', 'SecaoAEX'),
    p('A aplicação funcional usa Python, Django MVT, ORM, SQLite, HTML, CSS responsivo e JavaScript. Foram implementados os oito casos de uso: pesagem, consulta de estoque, classificação, venda, relatório individual de venda, relatório mensal/anual de produção, painel por período e cadastro de cooperados.'),
    p('O cooperado registra e classifica materiais, consulta estoque e produção. A diretoria também registra vendas e consulta dados financeiros. O presidente também cadastra, consulta, edita e exclui cooperados, definindo cargo e acesso. Dados pessoais são restritos ao presidente. Contas com movimentos são desativadas, preservando o histórico.'),
    p('A pesagem é salva antes da classificação. A distribuição deve somar exatamente o peso recebido, sem duplicar o estoque. Apenas material classificado pode ser vendido. A venda passa por revisão e confirmação; o saldo é revalidado em transação e o relatório é aberto após a gravação.'),
    p('Adaptações da modelagem', 'SecaoAEX'),
    p('Usuário é representado pelo User do Django e um Perfil com cargo, telefone e CPF opcional. A especialização dos atores é feita por cargos hierárquicos. TipoMaterial corresponde a Material; RegistroEstoque organiza a distribuição da pesagem. Estoque, painel e relatórios são consultas calculadas, sem tabelas que dupliquem os resultados.'),
    p('Pesos e dinheiro usam Decimal no lugar de double. O preço/kg é histórico no item de venda. O catálogo segue os protótipos: três materiais e 27 classificações. HU06 menciona cooperado, mas CU05 e o diagrama reservam relatório de venda à diretoria; foi seguida essa restrição. A aparência mantém o DOCX, com adaptação ao desktop e novos formulários necessários aos casos de uso.'),
    p('Validação e dificuldades', 'SecaoAEX'),
    p('Foram aprovados 33 testes automatizados de autenticação, CSRF, cargos, cadastro, duplicidade, classificação, saldos, vendas e períodos. No navegador foi concluído o fluxo de pesagem, classificação, revisão e confirmação de venda, com relatório. Onze telas foram verificadas em cinco larguras (55 combinações), sem rolagem horizontal indevida.'),
    p('Os principais cuidados foram impedir dupla contagem de peso e separar dados de produção, financeiros e pessoais. O PDF de instruções era uma imagem; ele e os diagramas foram lidos visualmente. Antes da migração houve backup, e os registros anteriores foram preservados.'),
    p('Limites da versão', 'SecaoAEX'),
    p('Não inclui pagamento, nota fiscal, coleta pública, integração com balança ou implantação de produção. Não houve teste em celular físico, teste de carga, impressão física ou validação da exportação pelo diálogo de PDF. Há botão de impressão e CSS A4. A equipe deve apresentar seu histórico Git real; não foram simuladas contribuições ou autoria.'),
    PageBreak(), p('Capturas do sistema em funcionamento', 'TituloAEX'),
    p('Dados fictícios da demonstração. As telas móveis mantêm a identidade visual dos protótipos; o desktop amplia o espaço de consulta.'),
]
mobile = Table([[screenshot('aex-menu-mobile.jpg', 115), screenshot('aex-pesagem-mobile.jpg', 115), screenshot('aex-venda-mobile.jpg', 115)],
                [p('Menu do presidente', 'LegendaAEX'), p('Pesagem antes da classificação', 'LegendaAEX'), p('Relatório após confirmar a venda', 'LegendaAEX')]], colWidths=[165, 165, 165])
mobile.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('BOTTOMPADDING', (0, 0), (-1, -1), 7)]))
story += [mobile, Spacer(1, 10), screenshot('aex-cooperados-desktop.jpg', 445), p('Cadastro e consulta de cooperados: acesso exclusivo do presidente.', 'LegendaAEX'),
          p('<b>Execução:</b> seguir o README; executar migrations, popular_demo e python manage.py runserver. As contas demo (presidente), diretoria e cooperado usam a senha fictícia Coopera123!.', 'TextoAEX')]
doc = SimpleDocTemplate(str(OUT / 'relatorio-aex.pdf'), pagesize=(595.28, 841.89), leftMargin=42, rightMargin=42, topMargin=38, bottomMargin=45)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT / 'relatorio-aex.pdf')
