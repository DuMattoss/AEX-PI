# Relatório de implementação da AEX

Sistema de gestão de estoque e produção para cooperativa de reciclagem. UENP, Campus Luiz Meneghel. Programação para Internet em integração com Engenharia de Software II. Versão de 28/10/2026.

Integrantes conforme a modelagem: Anna Laura Balmiza Soares, Eduardo Barbeito Mattos, Sabryna da Silva Moretto e Vitória Eduarda de Souza.

## O que foi implementado

Os oito casos de uso foram implementados: registrar pesagem, consultar estoque, classificar material recebido, registrar venda, emitir relatório individual de venda, gerar relatório mensal/anual de produção, visualizar painel por período e cadastrar cooperados. O cadastro inclui consulta, edição e exclusão. Contas com movimentos são desativadas em vez de apagadas, preservando o histórico.

As permissões seguem a hierarquia dos atores: cooperado registra e classifica materiais, consulta estoque, produção e painel; diretoria também registra vendas e consulta valores financeiros; presidente também gerencia cooperados. Os dados pessoais ficam restritos ao presidente e as rotas verificam o cargo no servidor.

O sistema usa Python, Django MVT, ORM, SQLite, templates HTML, CSS responsivo e JavaScript. A pesagem é persistida antes da classificação. A soma das classificações deve ser igual à pesagem; classificá-la não aumenta a produção uma segunda vez. A venda exige saldo classificado, tem revisão antes da confirmação e revalida o saldo em transação. O relatório é aberto automaticamente após a venda.

## Adaptações em relação à modelagem

Usuário é representado pelo User do Django e um Perfil com cargo, telefone e CPF opcional. Os atores especializados são cargos, evitando tabelas com dados pessoais repetidos. TipoMaterial é Material. Estoque, painel e relatórios são consultas sobre os movimentos, sem tabelas duplicando resultados. RegistroEstoque guarda a distribuição classificada da pesagem. Pesos e dinheiro usam Decimal no lugar do double do UML; o preço/kg fica no item de venda para preservar o histórico de negociação. O catálogo segue os protótipos: três tipos e 27 classificações.

Há uma divergência no documento: HU06 menciona cooperado, enquanto CU05 e o diagrama reservam o relatório de venda à diretoria. Foi adotado o acesso restrito descrito no caso de uso. As telas mantêm a identidade visual do DOCX, com adaptações no desktop e novos formulários necessários aos casos de uso.

## Validação e dificuldades

Foram aprovados 33 testes automatizados de autenticação, CSRF, permissões, cadastro, duplicados, classificação, saldo, vendas e consultas por período. Também foi executado no navegador um fluxo completo de pesagem, classificação, revisão, confirmação e relatório. As novas telas foram verificadas nas larguras de 375, 430, 768, 1366 e 1920 px. As imagens da instrução estavam em um PDF sem texto selecionável e foram lidas a partir da renderização; os diagramas UML também foram inspecionados visualmente.

O principal cuidado foi distinguir peso recebido de saldo classificado, impedindo contagem duplicada e venda antes da classificação. Outro foi separar relatórios de produção dos dados financeiros e pessoais. Houve backup antes da migração; os registros da primeira versão foram preservados e ligados a pesagens equivalentes.

## O que ficou de fora

Não foram implementados pagamento, nota fiscal, pedidos públicos de coleta, integração com balança ou implantação de produção. Não houve teste em celular físico, teste de carga, impressão física ou validação da exportação pelo diálogo de PDF. O código inclui o botão de impressão e CSS A4. O ZIP e o PDF não comprovam participação individual: o grupo deve apresentar seu histórico Git real, sem autoria ou commits inventados.

## Capturas

As capturas usadas no relatório PDF estão em verificacao/aex-menu-mobile.jpg, verificacao/aex-pesagem-mobile.jpg, verificacao/aex-venda-mobile.jpg, verificacao/aex-painel-desktop.jpg e verificacao/aex-cooperados-desktop.jpg. O relatório diagramado de duas páginas está em entrega/relatorio-aex.pdf.
