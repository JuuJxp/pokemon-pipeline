# Pipeline Pokémon: time recomendado por região

Esse projeto usa a PokéAPI para montar um pipeline de dados completo, com extração, transformação e carga, orquestrado pelo Airflow e persistido no PostgreSQL. A ideia central é responder qual seria o time de seis Pokémon mais indicado para enfrentar os ginásios de uma região, cruzando os tipos de cada Pokémon com a matriz de efetividade de tipos e com os tipos dos líderes de ginásio.

## Como o projeto foi pensado

Comecei estruturando o projeto em camadas, seguindo o modelo Raw, Trusted e Refined. A camada Raw guarda exatamente o que a PokéAPI devolve, sem nenhuma alteração. A camada Trusted já tem os dados limpos e só com os campos que interessam pro projeto. E o que chamo de Refined aqui é o resultado final, o time recomendado já calculado e salvo no banco.

Enquanto montava a extração, percebi que a PokéAPI não tem nenhum recurso de ginásios ou líderes de ginásio. Isso não existe na API. Como esse dado é de conhecimento público dos jogos e é bem pequeno (os 8 líderes de cada região, com seus nomes e tipos), montei um JSON curado manualmente pra cada região que decidi suportar e documentei isso no próprio arquivo, deixando claro que ali é dado de referência estático, complementando o que vem da API. Já a matriz de efetividade de tipos, que é o coração do cálculo de score, vem inteira da API real, no endpoint de tipos.

No começo eu tinha feito a extração região por região, trazendo só os Pokémon daquela geração. Depois que decidi suportar mais de uma região, mudei de ideia: a extração hoje traz o dex nacional inteiro de uma vez (mais de 1300 Pokémon, contando todas as gerações), e o que muda por região é só o conjunto de ginásios usado no cálculo do score. Faz mais sentido assim porque, no jogo, qualquer Pokémon pode ser levado pra qualquer região, então não fazia sentido limitar os candidatos do time por causa de onde eles "nasceram". Hoje o projeto suporta Kanto, Johto, Hoenn e Sinnoh, e a região é escolhida como parâmetro na hora de disparar a DAG no Airflow, sem precisar mexer em código nenhum.

O cálculo do score funciona assim: para cada Pokémon, comparo seus tipos contra o tipo de cada um dos 8 líderes de ginásio, duas vezes. Uma vez pra ver o quanto esse Pokémon atacando causaria de dano no ginásio, e outra pra ver o quanto o ginásio atacando causaria de dano nesse Pokémon. Somo essas diferenças pros 8 ginásios e ainda incluo um pequeno peso baseado nas stats totais do Pokémon, só como critério de desempate entre Pokémon com cobertura de tipo parecida. No fim, ordeno todos os 151 Pokémon por esse score e seleciono os 6 melhores garantindo que nenhum tenha o mesmo tipo primário de outro já escolhido, pra maximizar a cobertura do time.

## Estrutura do repositório

```
pokemon-pipeline/
├── dags/
│   └── pokemon_pipeline_dags.py
├── src/
│   ├── extract/
│   │   └── extract_pokeapi.py
│   ├── transform/
│   │   ├── parse_pokemon.py
│   │   ├── type_matrix.py
│   │   └── scoring.py
│   ├── load/
│   │   └── load_postgres.py
│   ├── utils/
│   │   └── logger.py
│   └── config.py
├── data/
│   ├── raw/
│   ├── trusted/
│   └── reference/
│       ├── gyms_kanto.json
│       ├── gyms_johto.json
│       ├── gyms_hoenn.json
│       └── gyms_sinnoh.json
├── logs/
├── requirements.txt
├── .env.example
└── .gitignore
```

Cada etapa do pipeline ficou isolada no seu próprio arquivo, seguindo a separação entre extração, transformação e carga que o projeto pedia. Pra adicionar uma nova região, basta criar um novo arquivo `gyms_<regiao>.json` na pasta de referência, no mesmo formato dos existentes, e incluir o nome da região na lista `REGIOES_DISPONIVEIS` em `src/config.py`. Nenhum outro arquivo precisa ser tocado.

## Logging e tratamento de erros

Cada módulo usa o mesmo logger, configurado em `src/utils/logger.py`, que grava tanto no console quanto em `logs/pipeline.log`. Na extração, se algum Pokémon específico falhar ao ser buscado na API (por instabilidade de rede, por exemplo), o pipeline registra um aviso e continua com os demais, em vez de derrubar a execução inteira. Na transformação, rodo uma validação de qualidade depois da limpeza, checando nulos, duplicatas e valores fora do intervalo esperado pras stats, e a execução é interrompida se alguma dessas checagens falhar.

## Reprodutibilidade

A camada de carga sempre apaga os dados daquela tabela antes de inserir de novo. Isso significa que rodar o pipeline várias vezes com os mesmos dados de entrada sempre deixa o banco no mesmo estado final, sem ficar duplicando linhas a cada execução.

## Como rodar localmente

O projeto foi desenvolvido e testado no WSL (Ubuntu) rodando dentro do Windows, com Python 3.14, PostgreSQL 18 e Airflow 3.2.2.

1. Clone o repositório e entre na pasta:
```bash
git clone https://github.com/JuuJxp/pokemon-pipeline.git
cd pokemon-pipeline
```

2. Crie e ative o ambiente virtual, depois instale as dependências:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Suba o PostgreSQL (no WSL ele não inicia sozinho) e crie o usuário e o banco:
```bash
sudo service postgresql start
sudo -u postgres psql
```
Dentro do psql:
```sql
CREATE USER julia WITH PASSWORD 'sua_senha';
CREATE DATABASE pokemon_pipeline OWNER julia;
```

4. Copie o `.env.example` para `.env` e preencha com as credenciais que você acabou de criar.

5. Configure o Airflow pra apontar pra pasta `dags/` do projeto:
```bash
export AIRFLOW_HOME=~/airflow
airflow db migrate
```
Edite `~/airflow/airflow.cfg` e mude `dags_folder` pro caminho completo da pasta `dags/` desse repositório.

6. Suba o Airflow:
```bash
airflow standalone
```
Acesse `http://localhost:8080` com o usuário e senha que aparecem no terminal, ative a DAG `pipeline_pokemon_pokeapi` e clique em Acionar. Antes de confirmar, o Airflow mostra um campo `regiao` que vem preenchido com `kanto`; pra gerar o time de outra região, basta trocar esse valor por `johto`, `hoenn` ou `sinnoh` antes de disparar.

## Resultado

Rodando com o parâmetro `regiao` no valor padrão (Kanto), o time recomendado ficou assim:

| Ordem | Pokémon | Tipo 1 | Tipo 2 | Score |
|---|---|---|---|---|
| 1 | Exeggutor | grass | psychic | 4.89 |
| 2 | Nidoking | poison | ground | 4.62 |
| 3 | Starmie | water | psychic | 3.88 |
| 4 | Sandslash | ground | nenhum | 3.83 |
| 5 | Dragonite | dragon | flying | 3.19 |
| 6 | Zapdos | electric | flying | 2.43 |

Faz sentido olhando pros ginásios de Kanto: Ground cobre bem contra Rock, Electric e Fire, Water cobre contra Fire e Ground, e assim por diante. O time como um todo cobre a maioria dos 8 tipos dos líderes.

## Limitações e próximos passos

O projeto hoje suporta 4 regiões (Kanto, Johto, Hoenn e Sinnoh), cada uma com seus 8 ginásios clássicos. Estender pra outra região é simples, só falta criar o arquivo `gyms_<regiao>.json` correspondente e incluir o nome em `src/config.py`. Uma limitação que continua existindo é que o dataset de ginásios foi montado manualmente, então qualquer erro de digitação nesses arquivos afeta o cálculo do score, diferente dos dados que vêm direto da API. Outra coisa que ainda não fiz é tratar regiões que têm mais de 8 ginásios ou formato diferente de progressão (algumas gerações mais recentes mudam essa estrutura), então por enquanto o projeto assume sempre 8 ginásios no formato clássico.
