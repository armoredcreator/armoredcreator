# ArmoredCreator — reconstrução do pipeline

Este repositório reúne a reconstrução da implementação de referência do laboratório `armoredcreator-audio-lab`, branch `fix/global-discovery-vision-download-production-20261009`, preservando a visão inicial em [`docs/VISAO_GERAL_ARMORED_CREATOR.md`](docs/VISAO_GERAL_ARMORED_CREATOR.md).

## Arquitetura e invariantes

- **Coordinator** é a única raiz de composição.
- **SQLite** é a fonte de verdade para estado, checkpoints, eventos, tentativas e publicações.
- **CATCH-UP → LIVE** é controlado por estado persistente; um bloqueio técnico não pode ser saltado.
- **Vision-before-download**: a aprovação Shopee é persistida antes de materializar a mídia.
- No máximo **um item de mídia ativo** por vez. Não há filas físicas nem Redis, RabbitMQ, Celery ou Kafka.
- Cada fonte mantém seu roteamento e workspace separados: `storage/Videos GRUPO_FONTE_1`, `storage/Videos GRUPO_FONTE_2`, `storage/Videos GRUPO_FONTE_3`.
- **Áudio**: RVC somente para narração PT-BR confirmada com confiança suficiente. Fala estrangeira, música, silêncio ou classificação incerta não chamam RVC; o áudio original é silenciado e o efeito do projeto é aplicado.
- **Hub** reconcilia publicação. `UNKNOWN` nunca é republicado automaticamente.
- **Cleanup** somente após publicação confirmada; o ORIGINAL é preservado como evidência de recuperação.

## Instalação local

Requer Python 3.11+, FFmpeg e o runtime/modelos RVC utilizados pelo Studio.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q -W error::RuntimeWarning
```

Configure as credenciais privadas em `credentials/project.env`, usando `credentials/project.env.example` como modelo. O arquivo `.env.example` é referência de compatibilidade; o ambiente operacional deve manter a configuração centralizada e não versionar segredos.

Antes de executar `START_ALL.bat`, configure o caminho do executável local do Telegram Bot API em `credentials/project.env`. Não coloque tokens, hashes ou chaves reais no Git.

## Estado desta reconstrução

O Coordinator, Sync, Vision, Studio, Hub, Recovery, SQLite, roteamento multi-source e testes textuais foram portados do branch de referência. O núcleo `armored_core/pipeline.py` e o gerador `ArmoredIA/caption/generator.py` foram reimplementados nesta reconstrução para manter o contrato de Vision-before-download e a evidência das legendas. A versão ainda precisa passar pela suíte completa e pela validação real ponta a ponta neste repositório antes de ser declarada operacional.

Os binários `ArmoredStudio/assets/banner.png` e `ArmoredStudio/assets/efeitosonoro.wav` precisam ser copiados do laboratório; não foram incluídos nesta portagem textual. Veja [`ArmoredStudio/assets/README.md`](ArmoredStudio/assets/README.md) e [`docs/RECONSTRUCTION_STATUS.md`](docs/RECONSTRUCTION_STATUS.md).

O repositório congelado `armoredcreator-testbase` não foi alterado.
