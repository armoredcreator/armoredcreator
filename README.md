# ArmoredCreator

Implementação incremental da esteira Telegram → Vision/Shopee → download → inteligência de áudio → Studio → Hub, com SQLite como fonte de verdade.

## Regras que não podem ser quebradas

- O Coordinator é a única raiz de composição.
- SQLite guarda estados, evidências, checkpoints e publicações.
- No máximo um item de mídia ativo por vez.
- Vision precisa aprovar o link antes de qualquer download.
- Não existem filas físicas nem dependência de Redis, RabbitMQ, Celery ou Kafka.
- Uma publicação com resultado `UNKNOWN` nunca é reenviada automaticamente.
- Cleanup somente depois de confirmação `CONFIRMED`.
- Só narração PT-BR confirmada pode usar RVC; os demais tipos de áudio não chamam RVC.

## Estado desta reconstrução

Este branch implementa o núcleo de controle, persistência, configuração, contratos de adapters e testes determinísticos. As integrações reais Telegram/Shopee, o classificador acústico, o Studio/RVC e o transporte Telegram de publicação precisam ser ligados aos adapters existentes e validados no ambiente real. Não declare o sistema operacional completo até concluir esses gates.

## Desenvolvimento

Requer Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python -m pytest -q
```

Configure as fontes por variável de ambiente `ARMORED_SOURCES_JSON`, um JSON array com `source_id`, `destination_id` e `topic_id`. Segredos de Telegram/Shopee ficam fora do Git.

O banco padrão é `storage/database/armoredcreator.db`; a raiz pode ser definida por `ARMORED_ROOT`. Os caminhos são resolvidos a partir da raiz do projeto, não da pasta de trabalho atual.

## Gates de validação real

1. Auditar SQLite/checkpoints existentes sem apagá-los.
2. Confirmar descoberta histórica e deduplicação por fonte/mensagem.
3. Confirmar que Vision rejeitada ou inconclusiva nunca aciona download.
4. Medir latência de validação e só então considerar concorrência pequena.
5. Confirmar áudio PT-BR/não PT-BR/música/silêncio com amostras rotuladas.
6. Confirmar publicação e reconciliação: `CONFIRMED`, `ABSENT`, `UNKNOWN`.
7. Confirmar recovery após reinício e CATCH-UP → LIVE sem saltar bloqueios.

Testes unitários não substituem integração real. Não conecte o runner de produção nem execute publicação externa antes de configurar e verificar cada adapter.
