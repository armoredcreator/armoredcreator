# ArmoredStock

Ferramenta independente para materializar no disco os vídeos históricos que já foram aprovados pela ArmoredVision.

## Execução

Na raiz do repositório, com `credentials/project.env` configurado:

```powershell
python .\\run_armored_stock.py
```

Também é possível executar a etapa Stock pelo executor histórico:

```powershell
python .\\run_catchup_stage.py stock
```

Ambas as entradas usam esta implementação e o mesmo Coordinator/lease SQLite. A ferramenta exige exatamente três fontes configuradas, bloqueia se houver decisões de Vision pendentes, baixa somente originais aprovados, processa um item por vez e interrompe no primeiro erro.

ArmoredStock não executa legenda/IA, Studio/RVC, Hub, publicação, limpeza de arquivos de trabalho ou transição para LIVE. Nunca apaga ou sobrescreve um ORIGINAL já existente.
