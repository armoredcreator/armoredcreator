# ArmoredCreator — reconstrução do pipeline

Este repositório reúne a reconstrução comparada de duas referências:
- baseline funcional congelado: `armoredcreator/armoredcreator-test`;
- evolução Vision-before-download e coleta histórica: `armoredcreator/armoredcreator-audio-lab`.

A visão geral está em [`docs/VISAO_GERAL_ARMORED_CREATOR.md`](docs/VISAO_GERAL_ARMORED_CREATOR.md), e o status de auditoria em [`docs/RECONSTRUCTION_STATUS.md`](docs/RECONSTRUCTION_STATUS.md).

## Arquitetura e invariantes

- **Coordinator** é a única raiz de composição.
- **SQLite** é a fonte de verdade para estado, checkpoints, eventos, tentativas e publicações.
- **CATCH-UP → LIVE** é controlado por estado persistente; um bloqueio técnico não pode ser saltado.
- **Vision-before-download**: a aprovação Shopee é persistida antes de materializar a mídia.
- No máximo **um item de mídia ativo** por vez. Não há filas físicas nem Redis, RabbitMQ, Celery ou Kafka.
- Cada fonte mantém roteamento e workspace separados: `storage/Videos GRUPO_FONTE_1`, `storage/Videos GRUPO_FONTE_2`, `storage/Videos GRUPO_FONTE_3`.
- **Áudio**: RVC somente para narração PT-BR confirmada com confiança suficiente. Fala estrangeira, música, silêncio ou classificação incerta não chamam RVC; o áudio original é silenciado e o efeito original do projeto é aplicado.
- **Hub** reconcilia publicação. `UNKNOWN` nunca é republicado automaticamente.
- **Cleanup** somente após publicação confirmada; o ORIGINAL é preservado como evidência de recuperação.
- **ArmoredStock** é uma ferramenta independente em `ArmoredStock/service.py`. Ela usa o Coordinator e SQLite existentes para materializar, um por vez, somente originais aprovados pela Vision. Não executa IA, Studio/RVC, Hub, publicação, cleanup nem cutover para LIVE.

## Coleta histórica por etapas

Cada comando executa uma única etapa e termina. Configure `credentials/project.env` e garanta que nenhuma outra instância esteja usando o banco.

```powershell
python .\\run_catchup_stage.py sync
python .\\run_catchup_stage.py vision
python .\\run_catchup_stage.py stock
```

- **Sync** reserva metadados do histórico das três fontes no SQLite, sem baixar mídia.
- **Vision** valida candidatos e persiste a decisão; os não aprovados ficam em `WAITING_VISION`, sem download.
- **ArmoredStock** baixa apenas originais aprovados, serialmente, e para na primeira falha.
- Também é possível iniciar a ferramenta diretamente com `python .\\run_armored_stock.py`. Os dois comandos usam a mesma implementação de ArmoredStock, sem duplicar a lógica de materialização.
- A conclusão de Stock não significa que os vídeos foram processados/publicados. Não inicie `START_ALL.bat` ou `run_coordinator.py` sem decidir explicitamente a continuação para produção.

Consulte [`CATCH_UP_STAGES.md`](CATCH_UP_STAGES.md) para os gates operacionais.

## Instalação local

Requer Python 3.11+, FFmpeg e o runtime/modelos RVC utilizados pelo Studio.

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q -W error::RuntimeWarning
```

Configure as credenciais privadas em `credentials/project.env`, usando `credentials/project.env.example` como modelo. Não versionar tokens, hashes ou chaves reais. Antes de executar `START_ALL.bat`, configure `BOT_API_EXE` para o executável local do Telegram Bot API.

## Limpeza de repositório

A árvore de produção não inclui mais os scripts experimentais antigos de descoberta web, reteste manual de metadados e smoke test isolado de legenda, nem a dependência separada do experimento de descoberta V2. A validação reproduzível fica na suíte de testes; os fluxos reais do Telegram continuam sendo gates explícitos de ponta a ponta.

Os assets originais `ArmoredStudio/assets/banner.png` e `ArmoredStudio/assets/efeitosonoro.wav` estão presentes no repositório.

## Estado

Os repositórios de referência `armoredcreator-test` e `armoredcreator-testbase` permanecem intocados. A reconstrução ainda exige CI verde após estas alterações e validação real no ambiente Telegram local antes de ser declarada operacional. Consulte [`docs/RECONSTRUCTION_STATUS.md`](docs/RECONSTRUCTION_STATUS.md).
