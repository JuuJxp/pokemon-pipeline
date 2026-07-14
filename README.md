# 🔴 Extraction & Analytics Pipeline: Pokémon Team Builder

Este repositório contém o desenvolvimento de um pipeline de dados ponta a ponta (ETL) projetado para responder a um problema analítico específico: **qual é o time de 6 Pokémon mais adequado para vencer os desafios de uma determinada região?** O projeto é estruturado de forma modular e escalável, utilizando dados de consumo público para modelar cenários reais de engenharia de dados.

---

## 🔌 Fonte de Dados

A origem primária dos dados é a **[PokéAPI](https://pokeapi.co/)**, uma API REST pública e gratuita que não exige autenticação. A extração foca em três frentes principais de dados:
* **Pokémon:** Atributos de tipos, estatísticas base e moveset.
* **Ginásios:** Estrutura de líderes e seus respectivos times por região.
* **Regiões (ex: Kanto, Johto, Hoenn):** Mapeamento de quais Pokémon estão disponíveis para captura em cada rota e em qual momento da jornada ocorrem.

---

## 🏗️ Arquitetura de Dados (Camadas Medallion)

O pipeline segue rigorosamente a separação física e lógica entre as etapas de ingestão, transformação e análise, garantindo que o fluxo de dados seja escalável e de fácil manutenção.

| Origem / Processamento | Camada | Descrição do Dado |
| :--- | :--- | :--- |
| **Extração direta da PokéAPI** | 📁 **Camada Raw** | JSONs brutos da API salvos exatamente como foram coletados, sem qualquer modificação. |
| **Limpeza e Normalização** | 📁 **Camada Trusted** | Dados limpos, estruturados e normalizados. Nesta etapa, são tratados dados incompletos, duplicados ou registros fora do escopo do projeto. |
| **Scoring por Região** | 📁 **Camada Refined** | Armazena a matriz de tipos aplicada, scores de eficácia calculados e as recomendações consolidadas dos times. |

---

## ⚙️ Regras de Negócio e Requisitos do Sistema

O pipeline foi projetado sob diretrizes rígidas para garantir consistência analítica e reprodutibilidade técnica.

### Requisitos Funcionais
* **Mapeamento de Progressão:** Filtrar e determinar em qual ponto da jornada regional cada espécie torna-se capturável.
* **Cálculo de Matriz de Efetividade:** Cruzar os atributos de tipos dos Pokémon contra as fraquezas e forças dos líderes de ginásio de cada região específica.
* **Algoritmo de Scoring:** Gerar uma pontuação individual de eficácia para cada Pokémon por região, ponderando sua cobertura ofensiva e defensiva.
* **Seleção de Time:** Compor o time ideal de exatamente **6 Pokémon**, exigindo obrigatoriamente que possuam **tipos distintos**.
* **Persistência de Dados:** Gravar os dados processados e refinados em banco de dados para permitir consultas analíticas rápidas, evitando reprocessar todo o pipeline a cada nova consulta.
* **Entrega de Resultados:** Retornar o time ideal acompanhado de uma justificativa técnica detalhada por tipo e ginásio correspondente.

### Requisitos Não Funcionais
* **Desacoplamento de ETL:** Divisão clara e isolada entre os processos de extração, transformação e carga.
* **Reproduzibilidade:** Garantia de idempotência. Executar o pipeline múltiplas vezes com os mesmos parâmetros produzirá resultados idênticos no banco de dados.
* **Manutenibilidade e Escalabilidade:** O código é estruturado de forma modular. Adicionar uma nova região ou alterar critérios de pontuação no futuro não exige a reescrita dos módulos existentes.
* **Orquestração de Fluxo:** Utilização de ferramenta de orquestração para coordenar o sequenciamento seguro das etapas de coleta, processamento e persistência.
