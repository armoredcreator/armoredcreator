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

## Ensaio ponta a ponta isolado com Studio real

Em 2026-10-10 foi executado um item de teste em diretorio temporario, sem abrir nem alterar o banco operacional do catch-up:

1. FFmpeg gerou um MP4 sintetico vertical, sem audio. O SQLite, workspace e assets foram isolados sob um diretorio temporario, removido ao fim do ensaio.
2. O caminho integrado de catch-up reservou o item, chamou Vision antes da materializacao, e so entao persistiu o original. Vision foi simulada e verificou explicitamente que o original ainda nao existia.
3. `ArmoredStudio` real executou analise e exportacao usando os assets locais `banner.png` e `efeitosonoro.wav`; o MP4 final foi decodificado por FFmpeg sem erro.
4. Publisher foi simulado: confirmou uma publicacao com ID sintetico. O item terminou `PUBLISHED`, cleanup foi concluido, ORIGINAL e FINAL permaneceram, e repetir o pipeline nao publicou novamente (uma chamada total).

Resultado: `E2E=PASS`, Vision-before-download, Studio real, validacao do arquivo final e idempotencia no pipeline. Limite: esta prova nao chamou Shopee Vision nem Telegram Hub reais; as integracoes reais sao cobertas apenas pela publicacao controlada documentada abaixo e pelo ensaio real anterior, nao por este item sintetico. A prova tambem nao certifica a matriz de audio falado/RVC.

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
