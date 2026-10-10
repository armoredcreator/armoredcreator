# Operação de catch-up por etapas

O fluxo integrado normal é `run_coordinator.py`/`START_ALL.bat`: ele descobre o histórico, executa Vision sem mídia, mantém a descoberta de mensagens novas durante a produção e conclui cada item aprovado antes de materializar o próximo. O cutover para LIVE só ocorre depois de finalizar a produção e não haver falhas técnicas pendentes.

Os comandos deste documento são ferramentas de diagnóstico/controle manual. Cada invocação executa uma única etapa e encerra. Não execute uma etapa ao mesmo tempo que o processo contínuo ou outra instância que use o mesmo banco.

Execute no PowerShell, a partir da raiz do projeto, com `credentials/project.env` configurado e sem outra instância do Coordinator usando o banco:

## 1. Sync histórico das três fontes

```powershell
python .\run_catchup_stage.py sync
```

Reserva metadados no SQLite na ordem das fontes configuradas. Não executa Vision nem baixa mídia. A descoberta percorre todos os tópicos paginados, aceita histórico geral de grupos/canais sem fórum e reserva vídeos mesmo sem link; esses vídeos ficam para a Vision decidir, sem download.

Se `ARMORED_SYNC_CATCHUP_LIMIT` estiver finito, o Sync falha antes de reservar itens; remova a variável ou configure `0` para buscar o histórico completo. Só avance se o comando terminar com código 0 e o relatório indicar varredura histórica esgotada e sem erros. O estado histórico permanece em CATCH-UP; esta etapa não faz cutover para LIVE.

## 2. Vision nas três fontes

Depois de revisar o relatório do Sync, execute explicitamente:

```powershell
python .\run_catchup_stage.py vision
```

Classifica candidatos duráveis elegíveis com `stop_after_vision=True`. Vídeos sem link Shopee ou com produto não resolvido ficam em `WAITING_VISION`; nenhum vídeo é baixado nesta etapa. Falhas técnicas param a etapa no primeiro item, produzem relatório não-zero e devem ser resolvidas antes de continuar.

## 3. ArmoredStock nas três fontes

Depois de revisar o relatório da Vision, execute explicitamente:

```powershell
python .\run_catchup_stage.py stock
```

Só começa se não houver candidatos aguardando decisão da Vision. Baixa, um por vez, somente originais aprovados pela Vision; a primeira falha interrompe a etapa para preservar a ordem. Não executa IA, Studio/RVC, Hub, Telegram/publicação, cleanup ou LIVE.

## Após ArmoredStock

O relatório de Stock confirma apenas a materialização dos originais aprovados; não confirma Studio, Hub ou publicação. Quando for a hora de iniciar a produção integrada, execute `START_ALL.bat` ou `run_coordinator.py`. O Coordinator retoma os itens persistidos no SQLite e conclui o fluxo respeitando a ordem por item.

## Segurança e retomada

- O SQLite é a fonte de verdade; não apague nem recrie o banco/storage para repetir uma etapa.
- As etapas são idempotentes em relação às reservas duráveis; uma etapa pode ser repetida após interrupção.
- Não se marca o histórico como completo nem se avança para LIVE durante Sync, Vision ou Stock.
- Cada comando encerra após a etapa escolhida. Não há avanço automático entre as três. O modo staged não instancia Studio/RVC, IA ou Hub.
- Use os IDs de fonte e tópicos definidos em `credentials/project.env`; nunca publique esse arquivo ou seus segredos nos logs. O PowerShell mostra início, erros e um relatório final compacto; o progresso detalhado de download fica desativado por padrão e só aparece se `ARMORED_SYNC_VERBOSE_PROGRESS=1`.
