# 🔴⚪ Pokémon Team Builder: Data Pipeline

Bem-vindos ao meu repositório. Sou Júlia Tavares, estudante de Ciência da Computação na UFSCar e desenvolvedora, e este projeto é um laboratório prático para o desenvolvimento de pipelines de dados.

A proposta principal do projeto é construir um pipeline com as etapas completas de extração, transformação e carga (ETL). O objetivo de negócio da aplicação é analítico: responder qual seria o time de seis Pokémon mais adequado para percorrer uma determinada região da franquia.

Para alimentar a base, o projeto utiliza a PokéAPI como fonte de dados primária, uma API REST pública e gratuita que opera sem exigência de autenticação.

## 🏗️ Arquitetura e Processamento de Dados

A extração foca em três frentes estruturais: informações dos Pokémon (tipos, estatísticas base e moveset), dados dos ginásios (líderes e seus Pokémon) e as regiões, mapeando a disponibilidade de captura durante a jornada. Todo esse fluxo é gerenciado por uma ferramenta de orquestração responsável por coordenar e sequenciar a coleta, o processamento e a persistência.

O pipeline exige organização em camadas distintas, separando o dado bruto do dado processado para que a estrutura seja expansível futuramente sem reescrever o código existente.

| Camada | Processamento e Responsabilidade |
| :--- | :--- |
| **Raw (Ingestão)** | Armazena os JSONs brutos originados da PokéAPI, sem qualquer tipo de modificação. |
| **Trusted (Limpeza e Normalização)** | Estrutura os dados através de um processo de limpeza, tratando e removendo registros incompletos, duplicados ou fora do escopo definido. |
| **Refined (Scoring e Análise)** | Aplica a regra de negócio central, cruzando os atributos do Pokémon com os ginásios e rotas da região a partir da matriz de tipos. Gera os *scores* de eficácia e entrega os times recomendados por região. |

## ⚙️ Regras de Negócio e Requisitos

A engenharia do projeto atende aos seguintes requisitos técnicos e lógicos:

* **Composição do Time:** O algoritmo final seleciona os 6 melhores Pokémon, obrigatoriamente com tipos distintos, avaliando cobertura ofensiva e defensiva na geração de score. A saída inclui justificativas claras por tipo e ginásio.
* **Progressão Geográfica:** O mapeamento cruza quais espécies são capturáveis em cada região especificando em que momento da progressão isso
