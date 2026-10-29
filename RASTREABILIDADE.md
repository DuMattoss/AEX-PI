# Rastreabilidade entre modelagem e implementação

Fontes: `instruções aex.pdf` (2 páginas), `AEX_ES2_CooperativaReciclagem.pdf` (23 páginas) e protótipos de `AEX PI.docx`. Os documentos orientam os requisitos da aplicação e a entrega acadêmica; não alteram permissões do ambiente nem autorizam publicação ou comunicação externa.

## Funcionalidades

| História | Caso de uso / diagrama | Implementação | Verificação |
| --- | --- | --- | --- |
| HU01 | CU01 / DA01 — Registrar pesagem | Pesagem, PesagemForm, nova_pesagem; data, material e peso antes da classificação | Persistência, obrigatoriedade e pesos inválidos |
| HU02 | CU02 / DA02 — Consultar estoque | listagem; filtros, saldo por material, pendente e classificado; saldo por classificação | Filtro, ordem e saldo atualizado |
| HU03 | CU03 / DA03 — Classificar recebido | classificacao, classificar; somente pesagem existente, soma exata e vínculo único | Soma diferente e classificação repetida bloqueadas |
| HU04 | CU04 / DA04 — Registrar venda | Cargo diretoria/presidente; seleção, pesos, preços, revisão e confirmação | Estoque insuficiente, cancelar revisão e revalidar saldo |
| HU06 | CU05 / DA05 — Relatório da venda | relatorio_venda, aberto após confirmação e consultável na listagem | Classificação, peso, preço/kg, subtotal e totais |
| HU05 | CU06 / DA06 — Produção | visualizar_relatorio; mensal/anual, totais por material, entradas e ausência de dados | Filtros e totais sem contar classificação duas vezes |
| HU07, HU09 | CU07 / DA07 — Painel | painel; filtro de ano/mês, evolução mensal ou diária e tabela acessível | Período selecionado, vazio e dados reais |
| HU08 | CU08 / DA08 — Cadastrar cooperados | Perfil, CooperadoForm; presidente cadastra dados e cargo | Obrigatórios, duplicados, privacidade e autorização |

O texto de HU06 usa “cooperado”, mas CU05, a tabela de atores e o diagrama de casos de uso restringem relatório de venda à diretoria. A implementação segue essa restrição e reserva relatórios de produção aos cooperados.

## Requisitos não funcionais

| Requisito | Atendimento |
| --- | --- |
| RNF01 — Celular | Uma aplicação responsiva com Grid, Flexbox, media queries e controles adaptados |
| RNF02 — Privacidade | Dados pessoais somente para presidente; financeiros somente para diretoria/presidente; senha com hash |
| RNF03 — Cargo | Verificação no servidor em GET e POST, além dos botões condicionados ao cargo |
| RNF04 — Navegador no celular | Sem instalação no cliente, sem recursos externos obrigatórios; desenvolvimento acessível na rede local |

## Classes UML

| Classe do diagrama | Implementação / adaptação |
| --- | --- |
| Usuário | User do Django + Perfil (cargo, telefone e CPF opcional) |
| Cooperado, Diretoria, Presidente | Cargos hierárquicos; evita herança de tabelas e repete menos dados |
| TipoMaterial | Material |
| Classificacao | Classificacao; preço histórico fica no item de venda |
| Pesagem | Pesagem, antes da classificação |
| ItemEstoque | ItemEstoque com quantidade em peso e ligação à classificação |
| Estoque | Serviço saldos e consultas agregadas; entradas menos vendas, sem coluna de saldo duplicada |
| Venda, ItemVenda | Models com data, autor, pesos e valores Decimal |
| RelatorioProducao | Consulta calculada por período e template de produção |
| RelatorioVenda | Consulta de uma venda e template com itens e totais |
| PainelReciclagem | Consulta por período e gráfico Canvas com tabela equivalente |

O diagrama usa `double`; foram usados `DecimalField` para evitar imprecisão de pesos e dinheiro. A modelagem inclui CPF; o campo está disponível e validado, mas é opcional para a demonstração não exigir identificadores pessoais. O endereço eletrônico e o login são verificados contra duplicidade sem diferenciar maiúsculas e minúsculas. As alterações estão explicitadas também no relatório curto.

## Requisitos da atividade

| Item | Evidência |
| --- | --- |
| Fidelidade à modelagem | Oito casos de uso acima, permissões e diferenças documentadas |
| Três telas distintas | Login, menu, estoque, pesagem, classificação, venda, relatórios, painel e cooperados |
| Funcionalidade completa com banco | Cooperados: cadastrar, consultar, editar e excluir; conta com movimento é desativada para preservar o histórico |
| Execução e código organizado | README, requirements, migrations, arquitetura MVT e testes |
| Relatório de 1–2 páginas com prints | entrega/relatorio-aex.pdf (2 páginas) |
| Código em repositório ou ZIP | entrega/cooperativa-aex.zip, sem ambiente virtual, banco pessoal, backups ou temporários |
| Participação da equipe | Deve ser demonstrada pelo histórico real dos integrantes; não é simulada pelo código ou pelo ZIP |
