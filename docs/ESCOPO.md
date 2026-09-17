# Escopo entregue

| Área | Implementado |
|---|---|
| Acesso | Login, cinco perfis, senha individual, CSRF, sessão por inatividade, limitação de tentativas e auditoria |
| Pacientes | Cadastro, busca, status ativo, consentimento de lembrete, histórico e anexos |
| Clínica | Anamnese, evolução, diagnóstico, prescrições e declarações em texto livre, impressão, retificação, odontograma FDI permanente e decíduo |
| Agenda | Calendário diário/semanal/mensal, arrastar e redimensionar, disponibilidade, bloqueios, conflito por paciente/dentista/sala, encaixe justificado, recorrência semanal |
| Tratamentos | Procedimentos, preços, profissionais habilitados, materiais por sessão, orçamento, aceite, sessões concluídas |
| Estoque | Cadastro, lotes, validade, custos, FEFO, mínimos/máximos, movimentos, perdas, ajustes, consumo automático |
| Compras | Fornecedor, pedido, itens, recebimento atômico, entrada de lotes e título a pagar |
| Financeiro | Receitas/despesas, parcelas, descontos, pagamentos parciais, estornos, comissões, inadimplência, fluxo de caixa e lucro gerencial |
| Relatórios | 15 relatórios com exportação PDF, XLSX e CSV |
| Operação | Dados fictícios, migrations, Docker/PostgreSQL, instalação local Windows/Linux, backup e restauração criptografados |

## Limites e decisões explícitas

- Entrega é um MVP funcional para validação, não software homologado para uso clínico imediato. Os testes desta entrega foram executados em SQLite. PostgreSQL, Docker, Windows, SMTP real e aparência em navegador precisam ser validados no ambiente de implantação.
- Estoque é um almoxarifado compartilhado, com localização textual por produto; não possui saldo por unidade nem transferências entre filiais. Filtros de unidade e profissional não restringem relatórios de estoque. Não há liberação de estoque negativo.
- Recorrência é semanal, até 26 consultas, com validação integral antes de salvar. Não há edição coletiva de série; cada ocorrência é editada individualmente.
- WhatsApp abre um rascunho no serviço externo: o usuário confere e envia. E-mail é manual, com SMTP configurável; o padrão registra no console para demonstração. Não há envio automático agendado, API oficial de WhatsApp ou confirmação por resposta do paciente.
- Odontograma usa botões por dente e histórico de condição/face textual; não é editor anatômico por superfície. Não há integração de exames de imagem, assinatura ICP-Brasil, prescrição eletrônica certificada ou emissão fiscal.
- Orçamento do plano calcula itens e desconto, mas não gera cobrança automaticamente. Concluir consulta gera cobrança pelo valor da consulta. O operador deve distribuir descontos e preços acordados entre as sessões. Evite gerar títulos manuais para a mesma receita já gerada por consulta. Parcelamento existe em lançamentos manuais; parcelas e forma do plano são informação comercial.
- Pagamentos e estornos são registros internos. Não processam cartões, PIX ou integração bancária. Comprovantes estão associados ao paciente, não a um título exclusivo.
- Lucro gerencial combina dinheiro recebido no período com materiais, custos diretos e comissões das consultas concluídas no período, além de despesas pagas. Não é DRE por competência. Compra paga reduz caixa; apenas material consumido reduz esse resultado. Comissões automáticas são deduzidas uma vez pelo valor da consulta, sem dedução duplicada quando pagas. Rentabilidade de procedimento é contribuição da produção, antes das despesas gerais.
- Saldo e inadimplência usam pagamentos atuais; não reconstituem posição histórica de fechamento. Ticket por paciente usa pacientes com pagamentos positivos no período; ticket por procedimento usa sessões concluídas.
- Arquivos de backup são lógicos, gerados em memória; adequados a bases pequenas. Para grandes volumes use backup nativo PostgreSQL, snapshot de anexos e processo de restauração próprio, com a mesma chave de criptografia.
- Não há exclusão física pela interface. Cadastros são inativados; pacientes sem histórico podem ser anonimizados. Retenção de prontuários exige política definida pela clínica, sem afirmar conformidade legal automática.
- Busca global cobre dados administrativos; não pesquisa dentro de textos clínicos criptografados. Não há recuperação de senha por e-mail: administrador usa o comando `changepassword`.
