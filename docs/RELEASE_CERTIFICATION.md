# Certificacao do release ArmoredCreator

## Release

- Ultima release publicada: `v1.0.1`.
- Revisao de catch-up integrado publicada na branch `armoredcreator-architecture-skeleton`, commit `352ebad`; ainda nao possui tag de release. `v1.0.1` continua sendo a ultima release formal.
- Branch: `armoredcreator-architecture-skeleton`.
- Runtime de referencia: Windows, Python 3.11.
- O codigo e os assets versionados foram separados deliberadamente de credenciais, sessao Telegram, banco operacional, logs, videos e do runtime/modelos RVC instalados nesta maquina.

## Testes automatizados

Executado na arvore de codigo do release:

```powershell
py -3.11 -m pytest -q -W error::RuntimeWarning
```

Resultado da release `v1.0.1`: **243 passed, 1 skipped**. A revisao publicada na branch terminou em **250 passed, 1 skipped** no worktree e em `C:\Users\Administrador\Downloads\ArmoredCreator-final`; warnings de runtime foram tratados como erros. Os sete novos casos verificam checkpoint da descoberta sem cutover, concorrencia deterministica de descoberta/Vision durante Studio, falha de Vision concorrente sem avancar checkpoint, limite de catch-up sem ativar descoberta LIVE, producao serial por item, bloqueio apos falha historica de Vision e tratamento terminal `WAITING_VISION`. O teste concorrente usa fontes e servicos simulados: nao certifica a estabilidade do Telegram real sob longa operacao.

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

As etapas historicas de diagnostico tambem podem ser executadas separadamente, sem iniciar Studio ou publicacao:

```powershell
python .\run_catchup_stage.py sync
python .\run_catchup_stage.py vision
python .\run_catchup_stage.py stock
```

`sync` com `ARMORED_SYNC_CATCHUP_LIMIT=0` percorre o historico completo e pode ser longo. As etapas staged preservam o estado SQLite; nao apague o banco para repetir uma etapa. O fluxo integrado normal e `.\START_ALL.bat`; o Coordinator preserva as reservas/checkpoints, descobre e valida mensagens novas durante a producao e termina um item aprovado antes de baixar o proximo.

## Limites do que foi certificado

A execucao real prova um percurso completo de um item e o comportamento de reconciliacao no destino selecionado. Nao certifica que terceiros permanecerao disponiveis, que todos os formatos/idiomas de audio funcionarao, nem que o catch-up completo terminara sem itens `WAITING_VISION` ou falhas de rede. A operacao historica completa deve ser monitorada e retomada pelos checkpoints; nenhum sistema externo pode ser prometido como 100% disponivel.

O arquivo final da publicacao controlada em `v1.0.0` foi removido pelo cleanup anterior e nao pode ser restaurado sem reprocessar o original. A partir de `v1.0.1`, o cleanup preserva o original e o resultado publicado, removendo apenas os artefatos temporarios do workspace. Essa mudanca de retencao foi verificada pela suite automatizada; nao foi feita uma segunda publicacao real so para testar a politica de limpeza. Manter todos os resultados finais aumenta o uso de disco e exige monitoramento no notebook.

A revisao local adiciona descoberta/Vision de mensagens novas em paralelo a producao historica; a sessao Telegram e liberada antes do Hub usar a mesma sessao, e a producao Studio/Hub executa com uma conexao SQLite propria. A cobertura de concorrencia e de checkpoints e automatizada com servicos simulados; a coleta historica completa real e a operacao LIVE prolongada ainda nao foram executadas nesta revisao.

## Validacao pendente para certificacao operacional

- Catch-up real completo nas tres fontes; o historico pode ser extenso, consumir disco e gerar publicacoes reais. Monitorar execucao, erros e espaco livre antes de iniciar.
- Operacao real prolongada apos cutover e confirmacao de que mensagens novas continuam sendo ingeridas sem atrasos/perdas.
- Matriz de audio em amostras autorizadas PT-BR, fala estrangeira, musica e sem audio; a verificacao real anterior cobriu apenas um clipe classificado como `MUSIC_ONLY`, sem gate RVC.
- Throughput/retencao de originais e finais em lote. A politica preserva ambos, portanto o consumo de armazenamento aumenta.
- A consulta Shopee valida produto/oferta afiliada encontrada, nao garante estoque ou disponibilidade universal do varejista.
