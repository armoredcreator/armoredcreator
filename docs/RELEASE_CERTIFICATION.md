# Certificacao do release ArmoredCreator

## Release

- Ultima release publicada: `v1.0.1`.
- Revisao de catch-up integrado publicada na branch `armoredcreator-architecture-skeleton`; ainda nao possui tag de release. `v1.0.1` continua sendo a ultima release formal.
- Branch: `armoredcreator-architecture-skeleton`.
- Runtime de referencia: Windows, Python 3.11.
- O codigo e os assets versionados foram separados deliberadamente de credenciais, sessao Telegram, banco operacional, logs, videos e do runtime/modelos RVC instalados nesta maquina.

## Testes automatizados

Executado na arvore de codigo do release:

```powershell
py -3.11 -m pytest -q -W error::RuntimeWarning
```

Resultado da release `v1.0.1`: **243 passed, 1 skipped**. A revisao publicada na branch terminou em **250 passed, 1 skipped** no worktree e em `C:\Users\Administrador\Downloads\ArmoredCreator-final`; warnings de runtime foram tratados como erros. Os sete novos casos verificam checkpoint da descoberta sem cutover, concorrencia deterministica de descoberta/Vision durante Studio, falha de Vision concorrente sem avancar checkpoint, limite de catch-up sem ativar descoberta LIVE, producao serial por item, bloqueio apos falha historica de Vision e tratamento terminal `WAITING_VISION`. O teste concorrente usa fontes e servicos simulados: nao certifica a estabilidade do Telegram real sob longa operacao.

## Ensaio ponta a ponta isolado: caminho LIVE com Studio real

Executado em 2026-10-10, sem aguardar postagem espontanea e sem acessar o SQLite, a sessao ou os destinos Telegram de producao:

1. **Isolamento:** Python 3.11 criou um diretorio temporario com seu proprio SQLite, workspace, assets copiados e dados de checkpoint. O diretorio foi removido automaticamente ao terminar. Nenhum item da fila real foi consultado ou baixado.
2. **Midia sintetica:** FFmpeg gerou localmente um MP4 vertical de 720x1280, 24 fps e 3 segundos, usando padrao de cor verde, H.264 e sem audio. A ausencia de audio exercita o caminho sem voz/RVC; nao substitui os ensaios com fala.
3. **Injecao LIVE controlada:** um adaptador de teste entregou ao metodo real `Coordinator.run_live_once_async()` exatamente um candidato sintetico, identificado pela fonte de teste e topico 777. O checkpoint temporario com valor 9000 so avancou para 9001 apos o processamento completo.
4. **Ordem Vision/download:** Vision foi substituida por um double deterministico, que verifica como pre-condicao que o ORIGINAL ainda nao existe e retorna dados de afiliado sinteticos. So depois dessa decisao o callback de materializacao copiou a midia sintetica para o workspace.
5. **Sessao e isolamento por etapa:** o Reader de teste conectou antes da descoberta/materializacao e desconectou antes da producao/Hub (1 conexao e 1 desconexao). Nao houve login ou trafego de rede Telegram.
6. **Studio real:** a instancia `ArmoredStudio` executou o analisador, Audio Intelligence e exportador reais do repositorio, com `banner.png`, `efeitosonoro.wav` e FFmpeg. O modo sem audio foi exercitado; RVC nao deveria ser acionado para esse input.
7. **Publicacao simulada:** o Publisher de teste retornou confirmacao e ID sintetico, sem fazer upload externo. O estado final no banco temporario foi `PUBLISHED`; cleanup foi marcado completo e ORIGINAL e FINAL foram preservados.
8. **Arquivo e idempotencia:** FFmpeg abriu/decodificou o FINAL sem erro. Uma segunda consulta LIVE nao encontrou novo candidato e nao repetiu a publicacao; total de chamadas de `publish` permaneceu 1.
9. **Resultado observado:** `LIVE_COORDINATOR_SYNTHETIC_E2E=PASS`, `vision_before_download=PASS`, `studio_real=PASS`, `hub_simulated_confirmed=PASS`, `published_and_cleanup=PASS`, `checkpoint_after_success=9001`, `final_ffmpeg_probe=PASS`, `second_live_poll_no_duplicate=PASS`, `external_messages_sent=0`, `temporary_database_removed=True`.

Houve duas falhas apenas no harness antes do resultado final: uma primeira prova chamou a API de ingestao direta, que nao representa o gate Vision de catch-up; outra comparou o ID retornado com o ID bruto, ignorando o namespace da fonte. Ambos os harnesses foram corrigidos e seus diretorios temporarios descartados; a execucao LIVE acima foi repetida com a identidade escopada correta e passou. Nenhum erro de produto, mensagem externa ou alteracao do banco real resultou dessas tentativas.

**Conclusao exata:** o Coordinator percorreu o caminho LIVE real do codigo e completou uma mensagem injetada deterministicamente com Studio real, em ambiente privado local e ponta a ponta ate uma confirmacao simulada. Esta prova nao chamou Shopee Vision real nem Telegram Hub real. Nao havia rota privada Telegram de teste configurada; por isso nao e seguro enviar o video sintetico para os destinos de producao. Existe uma publicacao real individual anterior documentada abaixo, mas ela nao transforma este ensaio em validacao de ponta a ponta de rede em LIVE. A matriz de audio falado/RVC tambem continua pendente.

## Testes automatizados de LIVE

Comando executado em 2026-10-10:

```powershell
py -3.11 -m pytest -q tests\test_live_polling_rate.py tests\test_live_reconnect.py tests\test_live_reconnect_watchdog.py -W error::RuntimeWarning
```

Resultado: **5 passed em 1,72 s**. A cobertura verificou round-robin de topicos, descoberta/materializacao e conclusao de um candidato por ciclo, tratamento de erro temporario com nova tentativa e reconexao apos timeout do watchdog. As fontes e as confirmacoes externas nesses testes sao simuladas. Nao e um soak test do Telethon real.

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

## Comprovacao do modo LIVE sem depender de postagem espontanea

O teste de disponibilidade LIVE nao deve esperar dias por uma nova mensagem natural. Sao duas verificacoes distintas:

1. **Disponibilidade em ociosidade:** depois do catch-up, manter o processo por uma janela finita sem novas mensagens e confirmar que continua ativo, que o polling/reconexao progride e que nao ha crescimento indevido de fila nem erros. Isso comprova monitoramento ocioso, nao a entrega de uma mensagem nova.
2. **Entrega deterministica de mensagem:** usar a fonte simulada em testes automatizados para injetar uma mensagem durante LIVE e verificar ingestao, identidade/fonte, checkpoint e processamento sem duplicacao. Os testes de polling round-robin e watchdog de reconexao cobrem parte deste contrato.
3. **Integracao Telegram controlada:** se for necessaria evidencia do transporte real, enviar uma mensagem sintetica para um grupo privado de teste e encaminhar para um destino privado de teste, nunca para os topicos de producao. Confirmar deteccao unica, rota, publicacao/confirmacao e idempotencia. Esta verificacao requer um destino de teste configurado e nao depende de trafego espontaneo dos grupos reais.

Uma mensagem nova observada nos grupos de producao pode ser registrada como evidencia adicional, mas nao e pre-requisito nem se deve afirmar que houve uma entrega real apenas com o teste simulado. A operacao ociosa LIVE tambem nao substitui a conclusao do catch-up historico.

## Limites do que foi certificado

A execucao real prova um percurso completo de um item e o comportamento de reconciliacao no destino selecionado. Nao certifica que terceiros permanecerao disponiveis, que todos os formatos/idiomas de audio funcionarao, nem que o catch-up completo terminara sem itens `WAITING_VISION` ou falhas de rede. A operacao historica completa deve ser monitorada e retomada pelos checkpoints; nenhum sistema externo pode ser prometido como 100% disponivel.

O arquivo final da publicacao controlada em `v1.0.0` foi removido pelo cleanup anterior e nao pode ser restaurado sem reprocessar o original. A partir de `v1.0.1`, o cleanup preserva o original e o resultado publicado, removendo apenas os artefatos temporarios do workspace. Essa mudanca de retencao foi verificada pela suite automatizada; nao foi feita uma segunda publicacao real so para testar a politica de limpeza. Manter todos os resultados finais aumenta o uso de disco e exige monitoramento no notebook.

A revisao local adiciona descoberta/Vision de mensagens novas em paralelo a producao historica; a sessao Telegram e liberada antes do Hub usar a mesma sessao, e a producao Studio/Hub executa com uma conexao SQLite propria. A cobertura de concorrencia e de checkpoints e automatizada com servicos simulados; a coleta historica completa real e uma janela observada de LIVE ocioso ainda nao foram executadas nesta revisao. Nao e necessario esperar uma mensagem natural para validar essas duas propriedades; consultar o plano de comprovacao LIVE acima.

## Validacao pendente para certificacao operacional

- Catch-up real completo nas tres fontes; o historico pode ser extenso, consumir disco e gerar publicacoes reais. Monitorar execucao, erros e espaco livre antes de iniciar.
- Janela finita de disponibilidade LIVE ociosa apos cutover, sem exigir que os grupos produzam mensagens espontaneamente.
- Integracao real de nova mensagem usando grupo e destino privados de teste; nao usar os destinos de producao para mensagem sintetica.
- Matriz de audio em amostras autorizadas PT-BR, fala estrangeira, musica e sem audio; a verificacao real anterior cobriu apenas um clipe classificado como `MUSIC_ONLY`, sem gate RVC.
- Throughput/retencao de originais e finais em lote. A politica preserva ambos, portanto o consumo de armazenamento aumenta.
- A consulta Shopee valida produto/oferta afiliada encontrada, nao garante estoque ou disponibilidade universal do varejista.
