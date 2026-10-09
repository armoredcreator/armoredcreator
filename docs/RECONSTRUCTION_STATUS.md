# Status da reconstrução

## Origem

- Repositório de referência: `armoredcreator/armoredcreator-audio-lab`
- Branch de referência: `fix/global-discovery-vision-download-production-20261009`
- Commit de referência observado: `f4a72a466bb6eb40653be755d697cf666eb62cec`
- Repositório congelado `armoredcreator-testbase`: intocado.

## O que foi portado

- ArmoredSync e ciclo de vida Telegram.
- ArmoredVision V1 e resolução Shopee.
- ArmoredIA, Policy, ranking determinístico e evidência de candidatas.
- ArmoredStudio, análise de áudio e processamento RVC.
- ArmoredHub, reconciliação e idempotência.
- Coordinator, SQLite, checkpoints, catch-up, Recovery, Startup Audit, storage e trace.
- Configuração de exemplo, launcher, documentação e testes automatizados textuais.

O pipeline de orquestração e o gerador de legendas foram reimplementados nesta reconstrução em vez de copiados literalmente. Devem ser tratados como código novo até a suíte validar o contrato completo.

## Itens que ainda bloqueiam declarar a reconstrução concluída

1. Copiar os arquivos binários originais `ArmoredStudio/assets/banner.png` e `ArmoredStudio/assets/efeitosonoro.wav` do laboratório.
2. Preencher `BOT_API_EXE` em `credentials/project.env` com o caminho local do Telegram Bot API; o launcher já não contém caminho de máquina fixo.
3. Executar `python -m pytest -q -W error::RuntimeWarning` e corrigir cada falha real.
4. Auditar imports, rotas de três fontes e migrações SQLite no repositório reconstruído.
5. Executar os gates reais: Vision sem download quando rejeitada; download só após aprovação; classificação PT-BR/idioma estrangeiro/música/sem áudio; publicação com `CONFIRMED/ABSENT/UNKNOWN`; restart e checkpoints; CATCH-UP → LIVE.
6. Não ativar produção nem afirmar ponta a ponta até que os gates anteriores tenham evidência observável.

## Exclusões deliberadas

O script `scripts/reset_certification_lab.ps1` não foi portado porque é um utilitário de reset destrutivo do laboratório e não deve fazer parte do caminho operacional padrão. Dois testes legados não foram portados nesta etapa; a cobertura equivalente precisa ser adicionada ou os testes devem ser recuperados manualmente.

Este documento é um registro de status, não um certificado de funcionamento real.
