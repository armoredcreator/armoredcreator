# Operacao e retomada do catch-up

Atualizado em 2026-10-10, por volta de 12:29 (horario local UTC-3). Este registro descreve o estado observado nesta maquina; nao substitui o SQLite.

## Versao e localizacao

- Projeto operacional: `C:\Users\Administrador\Downloads\ArmoredCreator-final`.
- Branch Git: `armoredcreator-architecture-skeleton`, commit `1b535a4`.
- Ultima release formal com tag: `v1.0.1`. O codigo mais novo esta publicado na branch, mas ainda nao foi congelado como release.
- A arvore operacional contem o codigo atualizado, credenciais privadas, sessao Telegram, banco SQLite e runtime local do Studio. Esses dados privados/runtime nao sao versionados.

## O que ja foi concluido

- Catch-up integrado: descoberta historica, Vision antes de download, producao/publicacao serial por item, coleta/Vision de mensagens novas durante a producao, retomada SQLite e checkpoints protegidos contra falhas tecnicas.
- Testes da revisao: `py -3.11 -m pytest -q -W error::RuntimeWarning` passou com **250 passed, 1 skipped** no worktree e em Downloads. `compileall` dos pacotes e `git diff --check` tambem passaram.
- O commit da implementacao e documentacao de certificacao esta publicado no GitHub; os 132 arquivos versionados foram comparados por hash com Downloads.
- Ja existe uma publicacao real anterior confirmada e idempotente, registrada no banco.

## Execucao real atual

O Coordinator foi iniciado em `Downloads\ArmoredCreator-final` em 2026-10-10 por volta de 12:14, com historico completo (`ARMORED_SYNC_CATCHUP_LIMIT=0`) e publicacao real habilitada (`ARMORED_HUB_DRY_RUN=0`). Foi limitado a **uma iteracao LIVE apos o catch-up** para esta validacao; essa limitacao existe somente no ambiente do processo, nao no arquivo de credenciais.

Ultima observacao registrada (aproximadamente 12:29):

- 379 itens no SQLite: 378 `RECEIVED` e 1 `PUBLISHED` anterior.
- Tres fontes ainda em CATCH-UP; zero checkpoints historicos persistidos e zero fontes marcadas como concluidas.
- Uma publicacao confirmada no banco; zero publicacoes `UNKNOWN`.
- Lease do Coordinator presente: **nao iniciar outra instancia**.
- Aproximadamente 198 GB livres.
- O processo estava presente/respondendo. Tres itens foram reservados na janela anterior de aproximadamente 2m37s, mas essa taxa nao e estavel nem permite estimar o total. Os logs nao fornecem progresso por pagina; verificar se a leitura historica continua ou se a conexao ficou aguardando o Telegram. Isso nao prova conclusao nem falha.

## Prazo estimado

Ainda nao ha ETA confiavel. O numero total de candidatos elegiveis no historico nao e conhecido; a leitura pode incluir muitas mensagens sem video e paginas/tópicos que ainda nao foram percorridos. Depois da descoberta ainda faltam Vision, processamento serial, publicacoes reais, cleanup e cutover. Com o ritmo parcial observado, a execucao pode levar horas ou mais se o historico for grande; somente os estados SQLite e a conclusao de cada etapa permitem estreitar a previsao.

As publicacoes durante esta execucao sao efeitos reais nos topicos configurados. Nao apagar nem recriar o banco, sessao ou storage.

## O que falta comprovar

1. Termino da descoberta historica das tres fontes e classificacao Vision dos candidatos.
2. Download, Studio/IA, publicacao confirmada no destino correto e cleanup preservando ORIGINAL/FINAL para cada candidato aprovado.
3. Cutover para LIVE somente apos o catch-up completo; observar ao menos uma mensagem nova real e depois a continuidade do monitoramento.
4. Validar com amostras autorizadas as classes de audio PT-BR, fala estrangeira, musica e sem audio, incluindo o gate RVC. A evidencia real anterior foi somente um clipe classificado como `MUSIC_ONLY`.
5. Avaliar consumo de disco e quotas externas em lote. A etapa de legendas usa Gemini; Vision/publicacao dependem das APIs Shopee/Telegram. A disponibilidade dessas quotas nao pode ser inferida pelos testes locais.

Ainda nao declarar a revisao como release 100% certificada nem criar nova tag antes desses gates reais. `docs/RELEASE_CERTIFICATION.md` registra o resultado automatizado e os limites de validacao.

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
