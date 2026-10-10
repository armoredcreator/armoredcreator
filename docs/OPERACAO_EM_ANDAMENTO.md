# Operacao e retomada do catch-up

Atualizado em 2026-10-10, 12:57 (horario local UTC-3). Este registro descreve o estado observado nesta maquina; nao substitui o SQLite.

## Versao e localizacao

- Projeto operacional: `C:\Users\Administrador\Downloads\ArmoredCreator-final`.
- Branch Git: `armoredcreator-architecture-skeleton` (esta atualizacao operacional sera publicada nesta branch).
- Ultima release formal com tag: `v1.0.1`. O codigo mais novo esta publicado na branch, mas ainda nao foi congelado como release.
- A arvore operacional contem o codigo atualizado, credenciais privadas, sessao Telegram, banco SQLite e runtime local do Studio. Esses dados privados/runtime nao sao versionados.

## O que ja foi concluido

- Catch-up integrado: descoberta historica, Vision antes de download, producao/publicacao serial por item, coleta/Vision de mensagens novas durante a producao, retomada SQLite e checkpoints protegidos contra falhas tecnicas.
- Testes da revisao: `py -3.11 -m pytest -q -W error::RuntimeWarning` passou com **250 passed, 1 skipped** no worktree e em Downloads. `compileall` dos pacotes e `git diff --check` tambem passaram.
- Teste isolado adicional durante o catch-up: `py -3.11 -m pytest -q tests\test_e2e_recovery.py tests\test_catch_up_pipeline_e2e.py tests\test_staged_catchup_production_order.py -W error::RuntimeWarning` passou com **14 passed em 8,69 s**, usando SQLite temporario e doubles/simulacao; nao publicou no Telegram nem acessou o banco operacional.
- O commit da implementacao e documentacao de certificacao esta publicado no GitHub; os 132 arquivos versionados foram comparados por hash com Downloads.
- Ja existe uma publicacao real anterior confirmada e idempotente, registrada no banco.

## Execucao real atual

O Coordinator foi iniciado em `Downloads\ArmoredCreator-final` em 2026-10-10 por volta de 12:14, com historico completo (`ARMORED_SYNC_CATCHUP_LIMIT=0`) e publicacao real habilitada (`ARMORED_HUB_DRY_RUN=0`). Foi limitado a **uma iteracao LIVE apos o catch-up** para esta validacao; essa limitacao existe somente no ambiente do processo, nao no arquivo de credenciais.

Ultima observacao registrada (12:57:33):

- 18.727 itens registrados: 18.570 `RECEIVED`, 157 `WAITING_VISION`, 1 `VISION` e 1 `PUBLISHED` anterior. `RECEIVED` aqui significa estado de fila/reserva; nao significa aprovado, processado ou publicado.
- Um agregado separado encontrou 133 itens com `affiliate_url` persistido. Isso nao certifica que Studio/Hub terminaram para eles.
- Tres fontes ainda em CATCH-UP; zero checkpoints historicos persistidos e zero fontes marcadas como concluidas.
- Uma publicacao registrada anteriormente. A consulta de status `UNKNOWN` nao foi valida para o esquema atual; nao inferir contagem de ambiguidades a partir dela.
- Lease do Coordinator presente: **nao iniciar outra instancia**.
- Aproximadamente 198 GB livres.
- Launcher e Coordinator estavam presentes/respondendo; iniciados as 12:14:08. O item mais recente foi atualizado as 12:57:29 e o Coordinator acumulava CPU. Isso indica atividade recente, mas nao identifica em qual fonte/topico a leitura esta nem prova que o historico terminou. O log operacional permanece sem atualizacoes desde a inicializacao, portanto nao fornece progresso por pagina nem diagnostico conclusivo.

## Prazo estimado

Ainda nao ha ETA confiavel e, sim, ainda falta bastante: apos cerca de 43 minutos, o banco registra 18.727 itens, mas nenhuma das tres fontes concluiu o historico e nao ha checkpoint historico. Apenas 133 tem `affiliate_url` persistido; 157 estao `WAITING_VISION`, e a grande maioria continua `RECEIVED`. O tamanho total do historico elegivel e desconhecido e o log nao reporta paginas/progresso por fonte, portanto nao e possivel converter o ritmo atual em horas/dias restantes. Alem de terminar a descoberta, ainda sera necessario resolver/classificar candidatos, produzir sequencialmente os aprovados, confirmar publicacoes, concluir cleanup e validar cutover/LIVE.

As publicacoes durante esta execucao sao efeitos reais nos topicos configurados. Nao apagar nem recriar o banco, sessao ou storage.

## O que falta comprovar

1. Termino da descoberta historica das tres fontes e classificacao Vision dos candidatos.
2. Download, Studio/IA, publicacao confirmada no destino correto e cleanup preservando ORIGINAL/FINAL para cada candidato aprovado.
3. Depois do catch-up, validar LIVE por uma janela finita de ociosidade (processo ativo, polling/reconexao saudavel, sem erros) e por uma mensagem sintetica deterministica em grupo/destino privados de teste. Nao e preciso esperar publicacao espontanea nos grupos reais; nao usar destinos de producao para o teste sintetico.
4. Validar com amostras autorizadas as classes de audio PT-BR, fala estrangeira, musica e sem audio, incluindo o gate RVC. A evidencia real anterior foi somente um clipe classificado como `MUSIC_ONLY`.
5. Avaliar consumo de disco e quotas externas em lote. A etapa de legendas usa Gemini; Vision/publicacao dependem das APIs Shopee/Telegram. A disponibilidade dessas quotas nao pode ser inferida pelos testes locais.

Ainda nao declarar a revisao como release 100% certificada nem criar nova tag antes desses gates reais. `docs/RELEASE_CERTIFICATION.md` registra o resultado automatizado e o plano de comprovacao LIVE independente de trafego espontaneo.

## Verificacao e retomada segura

Consulte o estado sem listar IDs/conteudo com este PowerShell na raiz do projeto:

```powershell
@'
import sqlite3
from pathlib import Path
p = Path(r"storage\database\armoredcreator.db").resolve()
c = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True, timeout=10)
try:
    print("states:", dict(c.execute("select state,count(*) from items group by state")))
    print("checkpoints:", c.execute("select count(*) from sync_source_topics").fetchone()[0])
    print("sources complete:", c.execute("select coalesce(sum(historical_complete),0) from sync_sources").fetchone()[0])
    print("runtime lease:", c.execute("select count(*) from runtime_locks").fetchone()[0])
finally:
    c.close()
'@ | py -3.11 -
```

- Enquanto o processo possuir o lease, nao iniciar Sync, Stock, Coordinator ou outra ferramenta contra o mesmo banco.
- Se a conversa/IA encerrar, o processo local pode continuar enquanto o processo do Coordinator permanecer ativo. Se ele parar, aguardar o lease ser liberado e conferir o estado acima antes de retomar.
- Retomada integrada padrao, a partir de `C:\Users\Administrador\Downloads\ArmoredCreator-final`: `.\START_ALL.bat`. Ela usa a configuracao local e pode publicar itens reais; executar somente se nao houver outra instancia usando o banco.
- O progresso duravel fica no SQLite. Uma interrupcao nao perde as reservas/artefatos ja gravados; a leitura Telegram pode repetir parte do historico ainda nao consolidado em checkpoints.
