# Notas da Joana — coisas que eu queria ter resolvido

Oi, sou eu de novo. Anotando aqui tudo que ficou na minha cabeça e não tive tempo de arrumar antes de sair. Em ordem de urgência (acho).

## 🔴 Crítico

- **Scheduler tá OFF.** O cenário tá rodando manual porque o "On" do scheduler tá no meu espaço pessoal Make — quando eu saí, a Cláudia desligou pra não consumir minha quota de operations. Hoje alguém do time clica "Run once" todo dia de manhã.

- **API key da OpenAI é minha pessoal.** Tá saindo uns **US$ 18/mês do meu cartão de crédito pessoal**. Já avisei o financeiro mas ninguém me reembolsou ainda. Precisa migrar pra conta OpenAI corporativa **URGENTE** — a chave atual eu vou ter que revogar quando o mestrado começar pra valer (daqui a alguns meses).

- **Custo da OpenAI tá saindo de controle.** Alguns prompts gastam até **8k tokens** porque os snippets do Google vêm enormes (sites com texto cheio). Já vi execução de US$ 0,02. Multiplica por 5k/mês = US$ 100/mês só de LLM. Truncar os snippets a uns 500 chars cada resolveria.

## 🟡 Importante

- **Duas conexões no Make vão precisar reconfigurar manualmente** quando vocês migrarem o cenário pra conta corporativa:
  1. HubSpot OAuth (precisa um admin do HubSpot autorizar de novo)
  2. Airtable PAT (gerar token novo na conta corporativa)
  Essas conexões **não exportam no blueprint JSON** do Make. Aprendi isso na pior hora.

- **Sem error handling em nenhum módulo.** Se a OpenAI devolve JSON quebrado, o cenário morre silencioso. Já aconteceu umas 3x em novembro e ninguém viu por dias.

- **Sem deduplicação.** Se um AE edita o stage do deal duas vezes, enriquece duas vezes. Já tem leads com 4 linhas no Airtable.

## 🟢 Nice to have (que eu nunca cheguei a fazer)

- Achei que ia ter tempo de fazer um **relatório de impacto** (quantos deals enriquecidos, quanto custou, qual o lift de conversão), mas só consegui o cenário no ar. Desculpa, Cláudia.
- Queria ter feito um **dashboard no Looker Studio** ligando o Airtable. Nem comecei.
- Mapear **LGPD** disso aqui — passa dado de empresa-cliente nos EUA via OpenAI. Levantei a bandeira pro jurídico mas eles nunca responderam.

Beijos e boa sorte! 💛
— Joana
