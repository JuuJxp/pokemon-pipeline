"""
DAG de orquestração do pipeline Pokémon.

Sequência: extrair pokémons -> extrair tipos -> parsear/limpar pokémons -> construir matriz de tipos -> calcular score e selecionar o time -> criar tabelas -> carregar pokémons -> carregar time recomendado.

Cada task chama uma função já testada isoladamente em src/. Se qualquer task falhar, o Airflow marca a DAG como falha e as tasks seguintes não rodam.

A extração hoje traz o dex nacional inteiro (todas as gerações), não só uma região, então essa parte do pipeline não muda dependendo da região escolhida. O que muda é só o cálculo de score e a seleção do time, que usam o conjunto de ginásios da região pedida.

Adicionei o parâmetro "regiao" no nível da DAG (visível na tela de "Acionar" do Airflow) exatamente pra não precisar editar código toda vez que eu quiser gerar o time recomendado de uma região diferente. As regiões válidas hoje são as que estão em src/config.py; se eu digitar uma região sem dataset de ginásios, o próprio pipeline avisa isso com um erro (validar_regiao), em vez de travar por causa de um FileNotFoundError.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pendulum
from airflow.sdk import DAG
from airflow.providers.standard.operators.python import PythonOperator

from src.extract.extract_pokeapi import extrair_todos_pokemons, extrair_tipos
from src.transform.parse_pokemon import transformar_pokemons
from src.transform.type_matrix import construir_matriz_efetividade
from src.transform.scoring import gerar_time_recomendado
from src.load.load_postgres import carregar_tudo


def task_extrair_pokemons(**kwargs):
    extrair_todos_pokemons()


def task_extrair_tipos(**kwargs):
    extrair_tipos()


def task_transformar_pokemons(**kwargs):
    transformar_pokemons()


def task_construir_matriz(**kwargs):
    construir_matriz_efetividade()


def task_calcular_time(**kwargs):
    # kwargs["params"] traz o valor escolhido na tela de "Acionar" do Airflow (ou o default, se a DAG rodar sem editar nada)
    regiao = kwargs["params"]["regiao"]
    gerar_time_recomendado(regiao)


def task_carregar_tudo(**kwargs):
    regiao = kwargs["params"]["regiao"]
    carregar_tudo(regiao)


with DAG(
    dag_id="pipeline_pokemon_pokeapi",
    description="Pipeline ETL Pokemon: extracao real da PokeAPI, scoring por tipo e carga no PostgreSQL",
    schedule=None,  # execucao manual; podia ser trocada para '@daily' se quisessemos agendamento automatico
    start_date=pendulum.datetime(2026, 1, 1, tz="America/Sao_Paulo"),
    catchup=False,
    tags=["pokemon", "engenharia_dados", "semana9"],
    # Regiões disponíveis hoje: kanto, johto, hoenn, sinnoh (ver src/config.py)
    params={"regiao": "kanto"},
) as dag:

    extrair_pokemons_task = PythonOperator(
        task_id="extrair_pokemons",
        python_callable=task_extrair_pokemons,
    )

    extrair_tipos_task = PythonOperator(
        task_id="extrair_tipos",
        python_callable=task_extrair_tipos,
    )

    transformar_pokemons_task = PythonOperator(
        task_id="transformar_pokemons",
        python_callable=task_transformar_pokemons,
    )

    construir_matriz_task = PythonOperator(
        task_id="construir_matriz_tipos",
        python_callable=task_construir_matriz,
    )

    calcular_time_task = PythonOperator(
        task_id="calcular_score_e_selecionar_time",
        python_callable=task_calcular_time,
    )

    carregar_tudo_task = PythonOperator(
        task_id="carregar_no_postgres",
        python_callable=task_carregar_tudo,
    )

    (
        extrair_pokemons_task
        >> extrair_tipos_task
        >> transformar_pokemons_task
        >> construir_matriz_task
        >> calcular_time_task
        >> carregar_tudo_task
    )