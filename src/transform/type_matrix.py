"""
Camada de Transformação: matriz de efetividade de tipos.

A PokéAPI devolve, pra cada tipo, um campo "damage_relations" com listas de quais tipos ele causa dano dobrado/reduzido/nulo. Aqui eu transformo isso numa matriz simples: matriz[atacante][defensor] = multiplicador.

Essa matriz é a mesma independente da região, então só preciso gerar ela uma vez e todo o scoring (de qualquer região) reaproveita o mesmo arquivo. É também o único dado do cálculo de score que vem inteiro da API, sem nenhuma curadoria manual da minha parte.
"""
import json
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger()

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
TRUSTED_DIR = Path(__file__).resolve().parents[2] / "data" / "trusted"
TRUSTED_DIR.mkdir(parents=True, exist_ok=True)

# tipos "especiais" da API que não existem nos jogos removidos por estarem fora do escopo do projeto
TIPOS_FORA_DE_ESCOPO = {"unknown", "shadow"}

def construir_matriz_efetividade(caminho_raw: str = "tipos.json") -> dict[str, dict[str, float]]:
    """
    Retorna um dicionário: matriz[tipo_atacante][tipo_defensor] = multiplicador
    (2.0 = super efetivo, 0.5 = pouco efetivo, 0.0 = imune, 1.0 = neutro)
    """
    logger.info("[TRANSFORM] Construindo matriz de efetividade de tipos")

    with open(RAW_DIR / caminho_raw, encoding="utf-8") as f:
        tipos_crus = json.load(f)

    nomes_tipos = [t["name"] for t in tipos_crus if t["name"] not in TIPOS_FORA_DE_ESCOPO]
    removidos = len(tipos_crus) - len(nomes_tipos)
    if removidos > 0:
        logger.warning(f"[TRANSFORM] {removidos} tipo(s) fora do escopo removido(s) ({', '.join(TIPOS_FORA_DE_ESCOPO)})")

    # começa tudo neutro (1.0) e ajusta pelas relações reais da API
    matriz = {atk: {defe: 1.0 for defe in nomes_tipos} for atk in nomes_tipos}

    for tipo in tipos_crus:
        atacante = tipo["name"]
        if atacante in TIPOS_FORA_DE_ESCOPO:
            continue

        relacoes = tipo["damage_relations"]

        for alvo in relacoes["double_damage_to"]:
            defensor = alvo["name"]
            if defensor in matriz[atacante]:
                matriz[atacante][defensor] = 2.0

        for alvo in relacoes["half_damage_to"]:
            defensor = alvo["name"]
            if defensor in matriz[atacante]:
                matriz[atacante][defensor] = 0.5

        for alvo in relacoes["no_damage_to"]:
            defensor = alvo["name"]
            if defensor in matriz[atacante]:
                matriz[atacante][defensor] = 0.0

    logger.info(f"[TRANSFORM] Matriz construída com {len(nomes_tipos)} tipos válidos")

    caminho_saida = TRUSTED_DIR / "matriz_tipos.json"
    with open(caminho_saida, "w", encoding="utf-8") as f:
        json.dump(matriz, f, ensure_ascii=False, indent=2)
    logger.info(f"[TRANSFORM] Matriz de tipos salva em '{caminho_saida}'")

    return matriz


if __name__ == "__main__":
    construir_matriz_efetividade()