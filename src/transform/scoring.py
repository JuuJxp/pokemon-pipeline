"""
Camada de Transformação: scoring e seleção do time.

Essa é a parte em que cruzo os tipos de cada Pokémon com os tipos dos líderes de ginásio da região escolhida (usando a matriz de efetividade da PokéAPI) pra calcular um score de cobertura ofensiva e defensiva, e a partir disso seleciono os 6 melhores Pokémon com tipos distintos entre si.
"""
import json
from pathlib import Path

import pandas as pd

from src.config import validar_regiao
from src.utils.logger import get_logger

logger = get_logger()

TRUSTED_DIR = Path(__file__).resolve().parents[2] / "data" / "trusted"
REFERENCE_DIR = Path(__file__).resolve().parents[2] / "data" / "reference"


def carregar_ginasios(regiao: str) -> list[dict]:
    validar_regiao(regiao)

    caminho = REFERENCE_DIR / f"gyms_{regiao}.json"
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    logger.info(f"[SCORING] {len(dados['ginasios'])} ginásios carregados para a região '{regiao}'")
    return dados["ginasios"]


def _tipos_do_pokemon(row: pd.Series) -> list[str]:
    tipos = [row["tipo_1"]]
    if row["tipo_2"] != "nenhum":
        tipos.append(row["tipo_2"])
    return tipos


def score_ofensivo(tipos_pokemon: list[str], tipo_ginasio: str, matriz: dict) -> float:
    """Melhor multiplicador entre os tipos do Pokémon atacando o tipo do ginásio."""
    return max(matriz.get(t, {}).get(tipo_ginasio, 1.0) for t in tipos_pokemon)


def score_defensivo(tipos_pokemon: list[str], tipo_ginasio: str, matriz: dict) -> float:
    """
    Dano combinado que o tipo do ginásio causaria nesse Pokémon (produto das
    relações, já que dois tipos fracos à mesma coisa multiplicam a fraqueza).
    Quanto MENOR esse valor, melhor a defesa do Pokémon nesse confronto.
    """
    multiplicador = 1.0
    for t in tipos_pokemon:
        multiplicador *= matriz.get(tipo_ginasio, {}).get(t, 1.0)
    return multiplicador


def calcular_scores(df_pokemons: pd.DataFrame, ginasios: list[dict], matriz: dict) -> pd.DataFrame:
    """
    Calcula, para cada Pokémon, o score agregado contra todos os ginásios da
    região: soma de (efetividade ofensiva - efetividade defensiva) em cada
    confronto, mais um pequeno bônus proporcional às stats totais (critério
    de desempate entre Pokémon com cobertura de tipo parecida).
    """
    logger.info(f"[SCORING] Calculando scores contra {len(ginasios)} ginásios")

    df = df_pokemons.copy()
    stats_cols = ["hp", "ataque", "defesa", "ataque_especial", "defesa_especial", "velocidade"]
    df["stats_totais"] = df[stats_cols].sum(axis=1)
    bonus_stats = df["stats_totais"] / df["stats_totais"].max() * 0.5  # peso pequeno, pois é desempate

    scores = []
    justificativas = []
    for _, row in df.iterrows():
        tipos = _tipos_do_pokemon(row)
        pontos_por_ginasio = []
        for g in ginasios:
            ofensivo = score_ofensivo(tipos, g["tipo"], matriz)
            defensivo = score_defensivo(tipos, g["tipo"], matriz)
            pontos_por_ginasio.append({
                "ginasio": g["lider"],
                "tipo_ginasio": g["tipo"],
                "ofensivo": ofensivo,
                "defensivo": defensivo,
            })
        score_bruto = sum(p["ofensivo"] - p["defensivo"] for p in pontos_por_ginasio)
        scores.append(score_bruto)
        justificativas.append(json.dumps(pontos_por_ginasio, ensure_ascii=False))

    df.loc[:, "score_bruto"] = scores
    df.loc[:, "score_final"] = df["score_bruto"] + bonus_stats
    df.loc[:, "justificativa"] = justificativas

    logger.info("[SCORING] Scores calculados para todos os Pokémon")
    return df


def selecionar_time(df_com_score: pd.DataFrame, tamanho: int = 6) -> pd.DataFrame:
    """
    Seleciona os N melhores Pokémon com tipo_1 distintos entre si
    """
    logger.info(f"[SCORING] Selecionando os {tamanho} melhores Pokémon com tipos distintos")

    df_ordenado = df_com_score.sort_values("score_final", ascending=False)

    selecionados = []
    tipos_usados = set()

    for _, row in df_ordenado.iterrows():
        if row["tipo_1"] in tipos_usados:
            continue
        selecionados.append(row)
        tipos_usados.add(row["tipo_1"])
        if len(selecionados) == tamanho:
            break

    if len(selecionados) < tamanho:
        logger.warning(
            f"[SCORING] Só foi possível selecionar {len(selecionados)}/{tamanho} Pokémon com tipos distintos"
        )

    df_time = pd.DataFrame(selecionados)
    logger.info(f"[SCORING] Time selecionado: {', '.join(df_time['nome'].tolist())}")
    return df_time


def gerar_time_recomendado(regiao: str = "kanto") -> pd.DataFrame:
    """
    Orquestra o fluxo pra uma região: carrega o dex nacional já tratado, carrega os ginásios da região pedida, calcula o score de todo
    mundo contra aqueles ginásios e seleciona o time final.

    O parâmetro regiao é o que permite escolher qual conjunto de ginásios usar sem duplicar lógica. Na DAG do Airflow isso vira um
    parâmetro que dá pra escolher na hora de disparar a execução.
    """
    df_pokemons = pd.read_csv(TRUSTED_DIR / "pokemons_trusted.csv")

    with open(TRUSTED_DIR / "matriz_tipos.json", encoding="utf-8") as f:
        matriz = json.load(f)

    ginasios = carregar_ginasios(regiao)

    df_com_score = calcular_scores(df_pokemons, ginasios, matriz)
    df_time = selecionar_time(df_com_score)

    caminho_saida = TRUSTED_DIR / f"time_recomendado_{regiao}.csv"
    df_time.to_csv(caminho_saida, index=False)
    logger.info(f"[SCORING] Time recomendado salvo em '{caminho_saida}'")

    return df_time


if __name__ == "__main__":
    time = gerar_time_recomendado("kanto")
    print(time[["nome", "tipo_1", "tipo_2", "score_final"]])