# ArmoredCreator — Visão Geral do Projeto

## Objetivo

A ArmoredCreator será uma esteira automática que encontra vídeos nos grupos do Telegram, verifica se os links de afiliado da Shopee estão utilizáveis, prepara os vídeos, publica no destino correto e registra o resultado. Ela deve processar o histórico antigo e continuar acompanhando mensagens novas.

Este documento registra a visão inicial do projeto. Ele descreve o comportamento desejado; não afirma que essas funções já estejam implementadas ou validadas.

## Como o sistema funciona

1. **Telegram — encontrar conteúdo**
   - Ler o histórico dos grupos configurados.
   - Continuar acompanhando novas mensagens.
   - Identificar a fonte e a mensagem original de cada conteúdo.

2. **Banco de dados — controlar o trabalho**
   - Registrar cada item e seu estado atual.
   - Guardar o que já foi feito para evitar trabalho repetido.
   - Permitir retomar após uma queda ou reinicialização.

3. **Vision — verificar o link Shopee**
   - Consultar a disponibilidade do produto e validar o link antes de baixar o vídeo.
   - Se o link não for aprovado ou a resposta não for conclusiva, não baixar o vídeo.
   - Registrar o resultado e o motivo para que seja possível entender o que aconteceu.

4. **Download — baixar apenas o necessário**
   - Baixar somente conteúdos aprovados.
   - Manter no máximo um vídeo em processamento ativo por vez, para controlar o uso do computador e evitar que os arquivos se acumulem.

5. **Inteligência de áudio — entender o som**
   - Distinguir narração em português, fala em outro idioma, música sem fala e ausência de áudio.
   - Quando houver narração em português identificada com confiança suficiente, permitir o uso do RVC.
   - Nos demais casos, não chamar o RVC: silenciar o áudio original e aplicar o efeito sonoro definido para o projeto.

6. **Studio — preparar o vídeo**
   - Executar o tratamento de áudio e vídeo definido pelo projeto.
   - Manter o volume do efeito sonoro alinhado ao padrão de introdução e encerramento.
   - Só avançar quando o resultado da etapa estiver registrado.

7. **Hub — publicar no destino certo**
   - Encaminhar o resultado ao grupo e tópico associados à fonte original.
   - Confirmar o resultado do envio antes de considerar a publicação concluída.
   - Se não for possível saber se o envio ocorreu, verificar antes de tentar publicar novamente.

8. **Finalização — registrar e continuar**
   - Guardar o resultado final no banco de dados.
   - Limpar arquivos temporários somente quando for seguro.
   - Liberar o item atual e seguir para o próximo.

## Como tratar a coleta histórica

A coleta histórica deve ser separada do processamento de vídeos.

### Fase A — descobrir e validar
- Aproveitar primeiro os registros já existentes no banco de dados.
- Consultar o histórico do Telegram apenas para descobrir mensagens que realmente estejam faltando.
- Validar os links Shopee sem baixar todos os vídeos.
- Salvar cada resultado imediatamente para que uma interrupção não apague o progresso.

### Fase B — processar e publicar
- Selecionar um item aprovado.
- Baixar e processar esse item.
- Publicar no destino correto e confirmar o resultado.
- Só então liberar o processamento para o próximo item.

A coleta e a validação podem avançar sem precisar esperar que cada vídeo passe por download, áudio e publicação. Porém, o processamento de mídia permanece limitado para não sobrecarregar o computador.

## Velocidade e estabilidade

- Começar medindo o tempo real das consultas, em vez de presumir uma velocidade.
- Registrar quantos itens foram examinados, aprovados, rejeitados, ficaram inconclusivos ou falharam tecnicamente.
- Testar primeiro consultas sequenciais e, depois, uma concorrência pequena e controlada para validação de links.
- Respeitar limites e erros da Shopee; aumentar a concorrência somente se os testes demonstrarem ganho sem aumentar bloqueios ou resultados incorretos.
- Usar tempos limite e tentativas limitadas, com motivo de erro visível.
- Estimar o tempo restante com base na velocidade medida, não em promessas.

## Regras fundamentais

1. **Progresso preservado:** ao reiniciar, continuar dos itens pendentes.
2. **Sem duplicidade:** não repetir uma publicação sem verificar o que aconteceu quando o resultado anterior for desconhecido.
3. **Fontes separadas:** manter a origem de cada item e encaminhá-lo ao destino correspondente.
4. **Download consciente:** verificar o link antes de baixar o vídeo.
5. **Uso controlado do computador:** limitar o processamento de mídia e monitorar o trabalho.
6. **Resultados explicáveis:** cada item deve ter estado, horário e motivo do resultado.
7. **Falha recuperável:** um erro temporário não deve apagar o progresso nem ser confundido com indisponibilidade do produto.

## Ordem de desenvolvimento

1. Criar o banco de dados e a coleta histórica retomável.
2. Implementar e medir a validação dos links antes do download.
3. Implementar o download controlado.
4. Implementar e validar a classificação e o tratamento de áudio.
5. Implementar publicação, confirmação e recuperação segura.
6. Testar o fluxo completo com evidências reais.
7. Ativar o acompanhamento contínuo de mensagens novas e verificar a convivência com a coleta histórica.

Cada etapa deve ser testada antes de avançar. Testes automatizados são importantes, mas não substituem a confirmação de que Telegram, Shopee, processamento de mídia e publicação funcionam de ponta a ponta.

## Resultado esperado

Uma aplicação que coleta o histórico sem baixar tudo antecipadamente, valida links antes de gastar recursos com vídeos, processa um item por vez, publica no destino correto e consegue continuar de onde parou. Depois de alcançar o fim do histórico disponível, continua acompanhando novas mensagens.

**Status deste documento:** visão e requisitos iniciais. A implementação e o funcionamento real de cada etapa precisam ser verificados separadamente.
