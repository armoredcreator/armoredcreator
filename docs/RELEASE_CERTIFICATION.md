# Certificacao do release ArmoredCreator

## Release

- Versao inicial congelada: `v1.0.0`; versao corrigida de retencao: `v1.0.1`.
- Branch: `armoredcreator-architecture-skeleton`.
- Runtime de referencia: Windows, Python 3.11.
- O codigo e os assets versionados foram separados deliberadamente de credenciais, sessao Telegram, banco operacional, logs, videos e do runtime/modelos RVC instalados nesta maquina.

## Testes automatizados

Executado na arvore de codigo do release:

```powershell
py -3.11 -m pytest -q -W error::RuntimeWarning
```

Resultado na versao `v1.0.1`: **243 passed, 1 skipped**. Warnings de runtime foram tratados como erros. A suite inclui testes para schema/migracao SQLite, recuperacao apos restart, coleta historica, Vision antes do download, isolamento por fonte, limites do ArmoredStock, classificacao de audio, Studio, Hub, reconciliacao de publicacao, resultado `UNKNOWN`, retomada idempotente e preservacao do original e do resultado final apos cleanup.

## Validacao real controlada

Com autorizacao do operador, foi processado um unico video de uma das fontes configuradas; a coleta historica ilimitada nao foi iniciada.

1. A sessao autenticada teve acesso de leitura as tres fontes Telegram.
2. O Telegram Bot API local respondeu a autenticacao. Os tres destinos foram resolvidos como topicos de forum; o bot era membro e tinha permissao de envio em cada um.
3. A Vision consultou um link Shopee real da fonte selecionada e persistiu a aprovacao do produto e da oferta de afiliado. Antes dessa decisao, o original ainda nao existia em disco.
4. O ArmoredStock materializou exatamente um original aprovado (6.896.748 bytes), sem erro e preservando a identidade da fonte.
5. O pipeline real concluiu Studio e Hub. O SQLite terminou em `PUBLISHED`; o Hub persistiu `CONFIRMED`, o destino correspondia a rota da fonte e o cleanup concluiu depois da confirmacao. Na versao `v1.0.0`, o cleanup removeu o arquivo final apos o envio; `v1.0.1` corrige isso e preserva o original e o video final publicado.
6. Uma verificacao independente da conversa Telegram confirmou a mensagem publicada. A repeticao de `publish_once` retornou o mesmo ID Telegram; o banco manteve um unico registro de publicacao, sem duplicacao.
7. As credenciais e IDs privados de chats/mensagens nao foram incluidos neste documento. A sessao, banco operacional e configuracao real continuam locais e ignorados pelo Git.

## Preparacao da instalacao local

Requer Python 3.11+, FFmpeg e o runtime/modelos do ArmoredStudio/RVC configurados na maquina. O runtime de terceiros nao e distribuido neste repositorio.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
New-Item -ItemType Directory -Force .\credentials | Out-Null
Copy-Item .\credentials\project.env.example .\credentials\project.env
```

Preencha `credentials/project.env` localmente com as credenciais e os tres pares de fontes/destinos. Configure tambem `BOT_API_EXE` para o executavel local do Telegram Bot API. Nunca compartilhe ou versiona `credentials/project.env`.

## Execucao

Para iniciar a operacao continua automatizada, executar na raiz do projeto:

```powershell
.\START_ALL.bat
```

O launcher verifica ou inicia o Telegram Bot API local e inicia o Coordinator. O Coordinator usa SQLite, executa a descoberta/recuperacao pendente e segue para o monitoramento continuo; o processamento de producao e publicacao real fica habilitado quando `ARMORED_HUB_DRY_RUN=0`.

As etapas historicas tambem podem ser executadas e inspecionadas separadamente, sem iniciar Studio ou publicacao:

```powershell
python .\run_catchup_stage.py sync
python .\run_catchup_stage.py vision
python .\run_catchup_stage.py stock
```

`sync` com `ARMORED_SYNC_CATCHUP_LIMIT=0` percorre o historico completo e pode ser longo. As etapas staged preservam o estado SQLite; nao apague o banco para repetir uma etapa. Depois de revisar os resultados, inicie a operacao continua com `.\START_ALL.bat`.

## Limites do que foi certificado

A execucao real prova um percurso completo de um item e o comportamento de reconciliacao no destino selecionado. Nao certifica que terceiros permanecerao disponiveis, que todos os formatos/idiomas de audio funcionarao, nem que o catch-up completo terminara sem itens `WAITING_VISION` ou falhas de rede. A operacao historica completa deve ser monitorada e retomada pelos checkpoints; nenhum sistema externo pode ser prometido como 100% disponivel.

O arquivo final da publicacao controlada em `v1.0.0` foi removido pelo cleanup anterior e nao pode ser restaurado sem reprocessar o original. A partir de `v1.0.1`, o cleanup preserva o original e o resultado publicado, removendo apenas os artefatos temporarios do workspace. Essa mudanca de retencao foi verificada pela suite automatizada; nao foi feita uma segunda publicacao real so para testar a politica de limpeza. Manter todos os resultados finais aumenta o uso de disco e exige monitoramento no notebook.

A coleta historica e a producao sao estagios ordenados, nao dois loops paralelos: o fluxo atual completa descoberta, Vision e materializacao serial do catch-up antes da producao historica; LIVE comeca depois do cutover. A coleta de mensagens novas simultanea com producao historica ainda nao esta implementada/validada.
