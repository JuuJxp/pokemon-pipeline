"""
Camada de Transformação: parsing dos Pokémon.

O JSON da camada Raw vem gigante (sprites, cries, moveset completo de todas as versões do jogo). Aqui eu extraio só o que o projeto precisa: nome, tipos e estatísticas base. É a mesma ideia de "limpar e estruturar" que eu já tinha feito, só que agora em cima do formato da PokéAPI

Reaproveitei as funções remover_duplicatas / tratar_nulos / corrigir_tipos com os mesmos nomes e o mesmo estilo de log ([TRANSFORM], [QUALIDADE]) que eu já usava, só o conteúdo interno mudou pra lidar com nova estrutura.
"""
import json
from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger()

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
TRUSTED_DIR = Path(__file__).resolve().parents[2] / "data" / "trusted"
TRUSTED_DIR.mkdir(parents=True, exist_ok=True)


def _extrair_stat(stats: list[dict], nome_stat: str) -> int | None:
    """Busca uma stat específica (hp, attack, etc.) na lista de stats do Pokémon."""
    for item in stats:
        if item["stat"]["name"] == nome_stat:
            return item["base_stat"]
    return None


def parsear_pokemons(pokemons_crus: list[dict]) -> pd.DataFrame:
    """
    Converte a lista de JSONs crus da PokéAPI num DataFrame com uma linha por Pokémon.

    Filtro pelas formas base aqui (campo is_default da API). Sem esse filtro, o total passa de 1300 registros porque a PokéAPI trata cada Mega Evolução, forma regional (Alola, Galar, Hisui) e forma Gigantamax como um "Pokémon" separado no endpoint /pokemon. Isso é diferente de espécie, que é o que a Pokédex Nacional conta (1025 hoje).
    """
    logger.info("[TRANSFORM] Iniciando parsing dos Pokémon (Raw -> Trusted)")

    formas_alternativas = [p for p in pokemons_crus if not p.get("is_default", True)]
    pokemons_base = [p for p in pokemons_crus if p.get("is_default", True)]

    if formas_alternativas:
        logger.info(
            f"[TRANSFORM] {len(formas_alternativas)} forma(s) alternativa(s) "
            f"(mega, regional, gmax etc.) removida(s), mantendo só formas base"
        )

    registros = []
    for p in pokemons_base:
        tipos = [t["type"]["name"] for t in p["types"]]
        registros.append({
            "id": p["id"],
            "nome": p["name"],
            "tipo_1": tipos[0] if len(tipos) > 0 else None,
            "tipo_2": tipos[1] if len(tipos) > 1 else None,
            "hp": _extrair_stat(p["stats"], "hp"),
            "ataque": _extrair_stat(p["stats"], "attack"),
            "defesa": _extrair_stat(p["stats"], "defense"),
            "ataque_especial": _extrair_stat(p["stats"], "special-attack"),
            "defesa_especial": _extrair_stat(p["stats"], "special-defense"),
            "velocidade": _extrair_stat(p["stats"], "speed"),
        })

    df = pd.DataFrame(registros)
    logger.info(f"[TRANSFORM] {len(df)} Pokémon parseados")
    return df


def remover_duplicatas(df: pd.DataFrame) -> pd.DataFrame:
    """API real não deveria trazer duplicatas, mas mantemos a verificação por segurança e consistência do pipeline."""
    antes = len(df)
    df = df.drop_duplicates(subset=["id"])
    removidos = antes - len(df)
    if removidos > 0:
        logger.warning(f"[TRANSFORM] {removidos} duplicata(s) removida(s)")
    else:
        logger.info("[TRANSFORM] Nenhuma duplicata encontrada")
    return df


def corrigir_tipos(df: pd.DataFrame) -> pd.DataFrame:
    """Garante que as colunas numéricas realmente são numéricas."""
    df = df.copy()
    logger.info("[TRANSFORM] Corrigindo tipos das colunas")

    colunas_numericas = ["hp", "ataque", "defesa", "ataque_especial", "defesa_especial", "velocidade"]
    for col in colunas_numericas:
        df.loc[:, col] = pd.to_numeric(df[col], errors="coerce")
        invalidos = df[col].isna().sum()
        if invalidos > 0:
            logger.warning(f"[TRANSFORM] {invalidos} valor(es) inválido(s) em '{col}' convertido(s) para nulo")

    return df


def tratar_nulos(df: pd.DataFrame) -> pd.DataFrame:
    """
    tipo_2 é naturalmente nulo pra Pokémon de um tipo só (ex: Charmander é só Fogo), é preenchido com 'nenhum' pra deixar explícito. Já hp/ataque/etc nulos indicariam falha na extração.
    """
    df = df.copy()
    logger.info("[TRANSFORM] Tratando valores nulos")

    df.loc[:, "tipo_2"] = df["tipo_2"].fillna("nenhum")

    colunas_criticas = ["nome", "tipo_1", "hp", "ataque", "defesa", "ataque_especial", "defesa_especial", "velocidade"]
    for col in colunas_criticas:
        nulos = df[col].isna().sum()
        if nulos > 0:
            logger.error(f"[TRANSFORM] '{col}' tem {nulos} valor(es) nulo(s) inesperado(s) (possível falha de extração)")

    return df


def validar_qualidade(df: pd.DataFrame) -> bool:
    """Mesma ideia, validações de sanidade após a limpeza."""
    logger.info("[QUALIDADE] Iniciando validações de qualidade")
    passou = True

    colunas_criticas = ["nome", "tipo_1", "hp", "ataque"]
    for col in colunas_criticas:
        nulos = df[col].isna().sum()
        if nulos > 0:
            logger.error(f"[QUALIDADE] Coluna '{col}' ainda tem {nulos} valor(es) nulo(s)")
            passou = False
        else:
            logger.info(f"[QUALIDADE] '{col}': sem nulos")

    duplicatas = df.duplicated(subset=["id"]).sum()
    if duplicatas > 0:
        logger.error(f"[QUALIDADE] {duplicatas} duplicata(s) ainda presente(s)")
        passou = False
    else:
        logger.info("[QUALIDADE] Sem duplicatas")

    for col in ["hp", "ataque", "defesa", "ataque_especial", "defesa_especial", "velocidade"]:
        fora = df[(df[col] < 1) | (df[col] > 255)]
        if not fora.empty:
            logger.error(f"[QUALIDADE] '{col}' tem {len(fora)} valor(es) fora do range esperado (1-255)")
            passou = False
        else:
            logger.info(f"[QUALIDADE] '{col}': todos os valores dentro do range")

    status = "PASSOU" if passou else "FALHOU"
    logger.info(f"[QUALIDADE] Resultado final das validações: {status}")
    return passou


def transformar_pokemons(caminho_raw: str = "pokemons_todos.json") -> pd.DataFrame:
    """Orquestra o parsing + limpeza, e salva a camada Trusted."""
    with open(RAW_DIR / caminho_raw, encoding="utf-8") as f:
        pokemons_crus = json.load(f)

    df = parsear_pokemons(pokemons_crus)
    df = remover_duplicatas(df)
    df = corrigir_tipos(df)
    df = tratar_nulos(df)

    if not validar_qualidade(df):
        raise ValueError("Dados de Pokémon reprovados na validação de qualidade.")

    caminho_saida = TRUSTED_DIR / "pokemons_trusted.csv"
    df.to_csv(caminho_saida, index=False)
    logger.info(f"[TRANSFORM] Camada Trusted salva em '{caminho_saida}' ({len(df)} registros)")

    return df


if __name__ == "__main__":
    transformar_pokemons()