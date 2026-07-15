"""
Camada de Carga: persistência no PostgreSQL.

Duas tabelas:
- pokemons: todos os Pokémon processados (camada Trusted), o dex nacional inteiro, pra consulta geral
- times_recomendados: o resultado do scoring, um time por região. Como agora dá pra gerar o time de várias regiões, essa tabela guarda todas elas ao mesmo tempo, usando "regiao" como parte da chave primária, então rodar o pipeline pra Johto não apaga o time que já tinha sido calculado pra Kanto.

Cada execução faz DELETE + INSERT dos dados daquela carga antes de gravar de novo. Assim, rodar o pipeline várias vezes com os mesmos dados de entrada sempre resulta no mesmo estado final do banco, sem ficar duplicando linha a cada execução.
"""
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

from src.utils.logger import get_logger

logger = get_logger()

load_dotenv()

TRUSTED_DIR = Path(__file__).resolve().parents[2] / "data" / "trusted"

DDL_POKEMONS = """
CREATE TABLE IF NOT EXISTS pokemons (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    tipo_1 TEXT NOT NULL,
    tipo_2 TEXT NOT NULL,
    hp INTEGER,
    ataque INTEGER,
    defesa INTEGER,
    ataque_especial INTEGER,
    defesa_especial INTEGER,
    velocidade INTEGER,
    carregado_em TIMESTAMP NOT NULL
);
"""

DDL_TIMES_RECOMENDADOS = """
CREATE TABLE IF NOT EXISTS times_recomendados (
    regiao TEXT NOT NULL,
    ordem INTEGER NOT NULL,
    pokemon_id INTEGER NOT NULL,
    pokemon_nome TEXT NOT NULL,
    tipo_1 TEXT NOT NULL,
    tipo_2 TEXT NOT NULL,
    score_final NUMERIC NOT NULL,
    carregado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (regiao, ordem)
);
"""


def _conectar():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def criar_tabelas() -> None:
    logger.info("[LOAD] Garantindo que as tabelas existem")
    with _conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(DDL_POKEMONS)
            cur.execute(DDL_TIMES_RECOMENDADOS)
        conn.commit()
    logger.info("[LOAD] Tabelas prontas")


def carregar_pokemons(caminho_csv: str = "pokemons_trusted.csv") -> int:
    """Persiste a camada Trusted de Pokémon inteira (substitui o conteúdo anterior)."""
    df = pd.read_csv(TRUSTED_DIR / caminho_csv)
    agora = datetime.now()

    logger.info(f"[LOAD] Iniciando carga de {len(df)} Pokémon")

    with _conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pokemons")
            for _, row in df.iterrows():
                cur.execute(
                    """
                    INSERT INTO pokemons
                        (id, nome, tipo_1, tipo_2, hp, ataque, defesa,
                         ataque_especial, defesa_especial, velocidade, carregado_em)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        int(row["id"]), row["nome"], row["tipo_1"], row["tipo_2"],
                        int(row["hp"]), int(row["ataque"]), int(row["defesa"]),
                        int(row["ataque_especial"]), int(row["defesa_especial"]),
                        int(row["velocidade"]), agora,
                    ),
                )
        conn.commit()

    logger.info(f"[LOAD] {len(df)} Pokémon persistidos na tabela 'pokemons'")
    return len(df)


def carregar_time_recomendado(regiao: str = "kanto") -> int:
    """Persiste o time recomendado de uma região (substitui o time anterior dessa região)."""
    caminho = TRUSTED_DIR / f"time_recomendado_{regiao}.csv"
    df = pd.read_csv(caminho)
    agora = datetime.now()

    logger.info(f"[LOAD] Iniciando carga do time recomendado para '{regiao}'")

    with _conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM times_recomendados WHERE regiao = %s", (regiao,))
            for ordem, (_, row) in enumerate(df.iterrows(), start=1):
                cur.execute(
                    """
                    INSERT INTO times_recomendados
                        (regiao, ordem, pokemon_id, pokemon_nome, tipo_1, tipo_2, score_final, carregado_em)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        regiao, ordem, int(row["id"]) if "id" in row else 0,
                        row["nome"], row["tipo_1"], row["tipo_2"],
                        float(row["score_final"]), agora,
                    ),
                )
        conn.commit()

    logger.info(f"[LOAD] Time recomendado de '{regiao}' persistido ({len(df)} Pokémon)")
    return len(df)


def carregar_tudo(regiao: str = "kanto") -> None:
    criar_tabelas()
    carregar_pokemons()
    carregar_time_recomendado(regiao)


if __name__ == "__main__":
    carregar_tudo("kanto")