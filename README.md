# Projeto Equipe Pokémon: Pipeline de Dados

[cite_start]Este repositório contém o projeto que estou desenvolvendo para construir um pipeline de dados focado nas etapas de extração, transformação e carga (ETL)[cite: 4]. [cite_start]O objetivo central deste estudo é processar os dados para responder qual seria o time de seis Pokémon mais adequado para percorrer uma determinada região[cite: 4].

## Fonte de Dados
[cite_start]Toda a base do projeto consome dados da PokéAPI (https://pokeapi.co/)[cite: 2]. [cite_start]A escolha dessa fonte se deve ao fato de ser uma API REST pública e gratuita que não exige autenticação[cite: 2]. [cite_start]A extração é dividida em três frentes principais[cite: 3]:
* [cite_start]**Pokémon**: Obtenção de tipos, estatísticas base e moveset[cite: 3].
* [cite_start]**Ginásios**: Identificação dos líderes de cada região e os Pokémon que eles utilizam[cite: 3].
* [cite_start]**Regiões**: Levantamento de dados de regiões como Kanto, Johto e Hoenn, mapeando quais Pokémon estão disponíveis para captura e em que momento exato da jornada[cite: 3].

## Arquitetura e Modelagem de Dados
[cite_start]O fluxo de processamento é gerenciado por uma ferramenta de orquestração responsável por coordenar as tarefas de coleta, processamento e persistência[cite: 7]. [cite_start]O pipeline foi organizado em camadas distintas para separar os dados brutos dos dados processados [cite: 19][cite_start], permitindo a futura inclusão de novas regiões sem a necessidade de reescrever a base[cite: 8, 21].

[cite_start]A divisão ocorre nas seguintes camadas[cite: 27, 30, 34]:
* [cite_start]**Camada Raw**: Armazena os arquivos JSON brutos exatamente como chegam da API, sem nenhuma modificação[cite: 27, 28].
* [cite_start]**Camada Trusted**: Contém os dados submetidos à limpeza e normalização[cite: 29]. [cite_start]Nesta etapa, dados incompletos, duplicados ou fora do escopo definido são sumariamente removidos e as informações são estruturadas[cite: 22, 23, 31].
* [cite_start]**Camada Refined**: Camada final que armazena os scores processados e os times recomendados por região[cite: 34, 35].

## Regra de Negócio e Scoring
[cite_start]Durante a transformação, o código calcula a matriz de efetividade de tipos para avaliar os Pokémon em relação aos ginásios locais[cite: 13]. [cite_start]Cada Pokémon recebe um score de eficácia focado na sua cobertura ofensiva e defensiva cruzada com os atributos das rotas e ginásios da região[cite: 5, 14].

[cite_start]O resultado final seleciona os 6 melhores Pokémon de tipos distintos para formar a equipe[cite: 15]. [cite_start]Todos esses dados processados são persistidos em um banco de dados[cite: 6, 16]. [cite_start]Isso garante que consultas futuras à equipe recomendada e às justificativas de tipo e ginásio sejam feitas de forma imediata, sem reprocessamento[cite: 6, 16]. [cite_start]O pipeline é totalmente reprodutível, garantindo que execuções com os mesmos parâmetros resultem nas mesmas saídas[cite: 20].
