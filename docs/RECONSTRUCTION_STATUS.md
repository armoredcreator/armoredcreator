# Status da reconstrução

## Referências comparadas

- **Baseline funcional congelado:** `armoredcreator/armoredcreator-test` (README com arquitetura, contratos e evidências certificadas).
- **Evolução de Vision-before-download / coleta histórica:** `armoredcreator/armoredcreator-audio-lab`.
- **Referência principal de integração atual:** branch `fix/global-discovery-vision-download-production-20261009`, commit `f4a72a466bb6eb40653be755d697cf666eb62cec`.
- **Referência específica do ArmoredStock independente:** branch `feat/armoredstock-independent-tool`, commit `dbfa2b2bec48c9b684ab1a61f4a496147653a56e`.
- Os repositórios `armoredcreator-test` e `armoredcreator-testbase` não foram alterados.

## O que está portado na branch de reconstrução

- ArmoredSync, ciclo de vida Telegram, descoberta histórica e rotas de três fontes.
- ArmoredVision V1, validação Shopee e aprovação antes do download.
- ArmoredIA, Policy, ranking determinístico e evidência de candidatas.
- ArmoredStudio, análise de áudio e processamento RVC.
- ArmoredHub, reconciliação e idempotência.
- Coordinator, SQLite, checkpoints, Recovery, Startup Audit, storage e trace.
- Coleta histórica separada em Sync → Vision → Stock.
- **ArmoredStock** como ferramenta de linha de comando independente, reutilizando o Coordinator e a mesma implementação canônica da etapa `stock` para evitar lógica duplicada.
- Configuração de exemplo, launcher, documentação e testes textuais.

O pipeline de orquestração e o gerador de legendas foram reimplementados nesta reconstrução em vez de copiados literalmente. Devem ser tratados como código novo até a suíte validar o contrato completo.

## Contrato do ArmoredStock

- Exige exatamente três fontes configuradas em `credentials/project.env`.
- Usa Coordinator como raiz de composição e adquire o lease de runtime SQLite.
- Bloqueia o download se houver candidatos ainda sem decisão da Vision, evidência de aprovação interrompida ou RECOVERY pré-download inválido.
- Materializa somente itens aprovados pela Vision, um por vez e em ordem determinística por fonte/mensagem.
- Mantém os workspaces separados por fonte e repara somente caminhos ausentes/legados; não sobrescreve ORIGINAL já existente.
- Para na primeira falha de download, mantém checkpoints seguros e devolve um relatório resumido.
- Não executa ArmoredIA, Studio/RVC, Hub, publicação, cleanup, nem muda CATCH-UP para LIVE.
- Entradas suportadas: `python .\\run_catchup_stage.py stock` e `python .\\run_armored_stock.py`. Ambas chamam a mesma lógica de etapa, sem duplicar implementação.

## Bloqueios para declarar a reconstrução concluída

1. Copiar os arquivos binários originais `ArmoredStudio/assets/banner.png` e `ArmoredStudio/assets/efeitosonoro.wav` do laboratório.
2. Preencher localmente `BOT_API_EXE` em `credentials/project.env`; o launcher não deve conter caminho de máquina fixo.
3. Executar `python -m pytest -q -W error::RuntimeWarning` e corrigir cada falha real.
4. Auditar imports, rotas das três fontes e migrações SQLite no repositório reconstruído.
5. Validar: Vision sem download quando rejeitada; download só após aprovação; classificação PT-BR/idioma estrangeiro/música/sem áudio; publicação com `CONFIRMED/ABSENT/UNKNOWN`; restart e checkpoints; CATCH-UP → LIVE.
6. Confirmar o comportamento independente do ArmoredStock em banco de teste, inclusive bloqueio por Vision pendente, preservação de ORIGINAL e parada na primeira falha.
7. Não ativar produção nem afirmar ponta a ponta até que os gates anteriores tenham evidência observável.

## Exclusões deliberadas

O script `scripts/reset_certification_lab.ps1` não foi portado porque é um utilitário de reset destrutivo do laboratório e não deve fazer parte do caminho operacional padrão. Os testes `tests/test_invariants.py` e `tests/test_studio_story_format.py`, que haviam ficado de fora na primeira portagem, foram recuperados do laboratório e incluídos novamente.

Este documento é um registro de status, não um certificado de funcionamento real.
