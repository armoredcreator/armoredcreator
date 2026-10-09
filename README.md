# ArmoredCreator — reconstrução do pipeline

Este repositório reúne a reconstrução comparada de duas referências:
- baseline funcional congelado: `armoredcreator/armoredcreator-test`;
- evolução Vision-before-download e coleta histórica: `armoredcreator/armoredcreator-audio-lab`.

A visão inicial está em [`docs/VISAO_GERAL_ARMORED_CREATOR.md`](docs/VISAO_GERAL_ARMORED_CREATOR.md) e a documentação de referência do laboratório em [`docs/REFERENCIA_LAB_README.md`](docs/REFERENCIA_LAB_README.md).

## Arquitetura e invariantes

- **Coordinator** é a única raiz de composição.
- **SQLite** é a fonte de verdade para estado, checkpoints, eventos, tentativas e publicações.
- **CATCH-UP → LIVE** é controlado por estado persistente; um bloqueio técnico não pode ser saltado.
- **Vision-before-download**: a aprovação Shopee é persistida antes de materializar a mídia.
- No máximo **um item de mídia ativo** por vez. Não há filas físicas nem Redis, RabbitMQ, Celery ou Kafka.
- Cada fonte mantém roteamento e workspace separados: `storage/Videos GRUPO_FONTE_1`, `storage/Videos GRUPO_FONTE_2`, `storage/Videos GRUPO_FONTE_3`.
- **Áudio**: RVC somente para narração PT-BR confirmada com confiança suficiente. Fala estrangeira, música, silêncio ou classificação incerta não chamam RVC; o áudio original é silenciado e o efeito do projeto é aplicado.
- **Hub** reconcilia publicação. `UNKNOWN` nunca é republicado automaticamente.
- **Cleanup** somente após publicação confirmada; o ORIGINAL é preservado como evidência de recuperação.
- **ArmoredStock** é uma ferramenta independente para materializar, um por vez, os originais já aprovados pela Vision. Não executa IA, Studio/RVC, Hub, publicação, cleanup nem cutover para LIVE.

## Coleta histórica por etapas

Cada comando executa uma única etapa e termina. Configure `credentials/project.env` e garanta que nenhuma outra instância esteja usando o banco.

```powershell
python .\\run_catchup_stage.py sync
python .\\run_catchup_stage.py vision
python .\\run_catchup_stage.py stock
```

- **Sync** reserva metadados do histórico das três fontes no SQLite, sem baixar mídia.
- **Vision** valida candidatos e persiste a decisão; os não aprovados ficam em `WAITING_VISION`, sem download.
- **ArmoredStock** baixa apenas originais aprovados, serialmente, e para na primeira falha. Só execute depois de a etapa Vision terminar sem erros.
- Alternativa de entrada direta para a ferramenta independente: `python .\\run_armored_stock.py`. Ela usa o mesmo Coordinator, lease SQLite e implementação da etapa `stock`; não cria um segundo pipeline.
- A conclusão de Stock não significa que os vídeos foram processados/publicados. Não inicie `START_ALL.bat` ou `run_coordinator.py` sem decidir explicitamente a continuação para produção.

Detalhes operacionais e condições de parada estão em [`CATCH_UP_STAGES.md`](CATCH_UP_STAGES.md).

## Instalação local

Requer Python 3.11+, FFmpeg e o runtime/modelos RVC utilizados pelo Studio.

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q -W error::RuntimeWarning
```

Configure as credenciais privadas em `credentials/project.env`, usando `credentials/project.env.example` como modelo. Não versionar tokens, hashes ou chaves reais. Antes de executar `START_ALL.bat`, configure `BOT_API_EXE` para o executável local do Telegram Bot API.

## Estado desta reconstrução

O Coordinator, Sync, Vision, Studio, Hub, Recovery, SQLite, roteamento multi-source, coleta por etapas e documentação foram portados/comparados com as referências indicadas. O núcleo `armored_core/pipeline.py` e o gerador `ArmoredIA/caption/generator.py` foram reimplementados nesta reconstrução e devem ser tratados como código novo até a suíte completa validar seus contratos.

Os binários originais `ArmoredStudio/assets/banner.png` e `ArmoredStudio/assets/efeitosonoro.wav` ainda precisam ser copiados do laboratório; não foram incluídos nesta portagem textual. Veja [`ArmoredStudio/assets/README.md`](ArmoredStudio/assets/README.md) e [`docs/RECONSTRUCTION_STATUS.md`](docs/RECONSTRUCTION_STATUS.md).

Os repositórios de referência `armoredcreator-test` e `armoredcreator-testbase` permanecem intocados. Este repositório ainda não deve ser considerado operacional até que CI e gates reais de ponta a ponta sejam aprovados.
