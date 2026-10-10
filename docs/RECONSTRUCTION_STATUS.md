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
- Ferramentas staged independentes para Sync → Vision → Stock (diagnóstico/controle manual).
- Catch-up integrado no Coordinator: descobre e classifica o histórico sem mídia, mantém descoberta/Vision de mensagens novas durante a produção e materializa/processa/publica um item aprovado por vez.
- **ArmoredStock** como pacote de ferramenta independente em `ArmoredStock/service.py`; `run_armored_stock.py` é o launcher dedicado e `run_catchup_stage.py stock` delega à mesma implementação, sem duplicar materialização.
- Configuração de exemplo, launcher, documentação e testes textuais.

O pipeline de orquestração e o gerador de legendas foram restaurados a partir do branch de referência `fix/global-discovery-vision-download-production-20261009` após a comparação revelar divergências na primeira portagem. A suíte, os gates de produção e a execução real controlada estão documentados em [`RELEASE_CERTIFICATION.md`](RELEASE_CERTIFICATION.md).

## Contrato do ArmoredStock

- Exige exatamente três fontes configuradas em `credentials/project.env`.
- Usa Coordinator como raiz de composição e adquire o lease de runtime SQLite.
- Bloqueia o download se houver candidatos ainda sem decisão da Vision, evidência de aprovação interrompida ou RECOVERY pré-download inválido.
- Materializa somente itens aprovados pela Vision, um por vez e em ordem determinística por fonte/mensagem.
- Mantém os workspaces separados por fonte e repara somente caminhos ausentes/legados; não sobrescreve ORIGINAL já existente.
- Para na primeira falha de download, mantém checkpoints seguros e devolve um relatório resumido.
- Não executa ArmoredIA, Studio/RVC, Hub, publicação, cleanup, nem muda CATCH-UP para LIVE.
- Entradas suportadas: `python .\\run_catchup_stage.py stock` e `python .\\run_armored_stock.py`. Ambas chamam a mesma lógica de etapa, sem duplicar implementação.

## Estado da certificação

- A certificação de catch-up integrado inclui testes de ordem por item, checkpoints persistidos sem cutover, coleta/Vision concorrente durante Studio e bloqueio do cutover após falha técnica. Resultados e limites constam em [`RELEASE_CERTIFICATION.md`](RELEASE_CERTIFICATION.md).
- Três fontes Telegram e seus destinos foram resolvidos; o bot autenticou e tinha permissões de envio nos três tópicos.
- Um vídeo real autorizado percorreu Vision-before-download, ArmoredStock, Studio e publicação no destino da fonte. Telegram confirmou a mensagem, o SQLite persistiu `PUBLISHED`/`CONFIRMED` e a repetição idempotente retornou o mesmo ID sem duplicar a publicação.
- As credenciais, sessão Telegram, banco operacional, logs, mídias e runtime/modelos locais são dados de máquina e permanecem fora do Git.
- A execução real controlada anterior não substitui um catch-up histórico completo ou operação LIVE prolongada. Também não certifica disponibilidade futura de terceiros, todas as combinações de áudio ou operação sem supervisão.

## Limpeza deliberada

Os scripts experimentais `scripts/probe_google_shopee_discovery.py`, `scripts/retest_telegram_video_metadata.py` e `scripts/validate_caption_v1_real.py`, junto com `requirements-web-discovery.txt`, foram removidos por não fazerem parte do caminho operacional reproduzível. O script destrutivo `scripts/reset_certification_lab.ps1` também não foi portado. Os testes `tests/test_invariants.py` e `tests/test_studio_story_format.py` foram recuperados e mantidos.

O certificado com escopo, comandos, resultados e limitações está em [`RELEASE_CERTIFICATION.md`](RELEASE_CERTIFICATION.md).
