"""
Camada de Extração (Extract) — PokéAPI real.

Essa é a evolução da função extrair() que eu já tinha feito, mas troquei pra bater na PokéAPI de verdade, mantendo a mesma ideia: uma função busca, loga quantos registros vieram, e devolve os dados pra quem chamou continuar o pipeline.

No início eu tinha feito a extração por geração (só os Pokémon de Kanto, por exemplo), pensando em processar região por região. Mas decidi mudar pra buscar o dex nacional inteiro de uma vez só (função extrair_todos_pokemons). O motivo é que o time recomendado não precisa ficar restrito aos Pokémon "daquela região" pra enfrentar os ginásios dela, na prática qualquer Pokémon do jogo pode ser levado pra qualquer lugar, então faz mais sentido calcular o score contra TODOS os Pokémon disponíveis e só trocar o conjunto de ginásios conforme a região escolhida. Isso também deixa mais simples de adicionar região nova depois, não preciso extrair nada de novo, só criar o arquivo de ginásios daquela região.

Responsabilidades desta etapa:
- Buscar os dados na API
- Salvar exatamente como vieram em data/raw/ (JSON cru, sem transformação)
- Registrar log e não derrubar o pipeline inteiro se 1 Pokémon falhar
"""
import json
import time
from pathlib import Path

import requests

from src.utils.logger import get_logger

logger = get_logger()

BASE_URL = "https://pokeapi.co/api/v2"
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

TIMEOUT = 10
MAX_TENTATIVAS = 3
LIMITE_LISTAGEM = 100000

def _get_com_retry(url: str) -> dict | None:
    """GET com algumas tentativas antes de desistir daquele recurso."""
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            resp = requests.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"[EXTRACT] Falha ao buscar '{url}' (tentativa {tentativa}/{MAX_TENTATIVAS}): {e}"
            )
            time.sleep(1)
    logger.error(f"[EXTRACT] Desisti de '{url}' após {MAX_TENTATIVAS} tentativas")
    return None


def extrair_todos_pokemons() -> list[dict]:
    """
    Extrai o dex nacional inteiro (todas as gerações de uma vez).

    Primeiro busca a lista completa de nomes/URLs em /pokemon, depois faz uma chamada por Pokémon pra pegar os detalhes (tipos, stats). Mas só precisa rodar isso uma vez; o resultado fica salvo em data/raw/pokemons_todos.json e o pipeline reaproveita esse arquivo depois, sem precisar bater na API de novo a cada execução (a não ser que eu queira atualizar os dados).
    """
    logger.info("[EXTRACT] Iniciando extração do dex nacional completo")

    lista = _get_com_retry(f"{BASE_URL}/pokemon?limit={LIMITE_LISTAGEM}")
    if lista is None:
        logger.error("[EXTRACT] Não foi possível obter a listagem de Pokémon, abortando extração")
        return []

    especies = lista["results"]
    logger.info(f"[EXTRACT] {len(especies)} Pokémon encontrados no dex nacional")

    pokemons_crus = []
    falhas = 0

    for i, especie in enumerate(especies, start=1):
        dados = _get_com_retry(especie["url"])
        if dados is None:
            falhas += 1
            continue
        pokemons_crus.append(dados)

        # log de progresso a cada 200 pra eu conseguir acompanhar no terminal
        if i % 200 == 0:
            logger.info(f"[EXTRACT] Progresso: {i}/{len(especies)} Pokémon processados")

    if falhas > 0:
        logger.warning(f"[EXTRACT] {falhas} Pokémon(s) não puderam ser extraídos e foram ignorados")

    logger.info(f"[EXTRACT] {len(pokemons_crus)} Pokémon extraídos com sucesso no total")

    caminho = RAW_DIR / "pokemons_todos.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(pokemons_crus, f, ensure_ascii=False, indent=2)
    logger.info(f"[EXTRACT] Dados brutos salvos em '{caminho}'")

    return pokemons_crus


def extrair_pokemons_por_geracao(geracao_id: int = 1) -> list[dict]:
    """
    Função legada da primeira versão do projeto, quando eu ainda extraía região por região. Deixei aqui porque pode ser útil pra testes rápidos, mas o pipeline principal hoje usa extrair_todos_pokemons() acima.

    Extrai todos os Pokémon de uma geração (ex: geração 1 = Kanto, IDs 1-151).
    """
    logger.info(f"[EXTRACT] Iniciando extração da geração {geracao_id}")

    info_geracao = _get_com_retry(f"{BASE_URL}/generation/{geracao_id}")
    if info_geracao is None:
        logger.error(f"[EXTRACT] Não foi possível obter a geração {geracao_id}, abortando extração")
        return []

    especies = info_geracao["pokemon_species"]
    logger.info(f"[EXTRACT] {len(especies)} espécies encontradas na geração {geracao_id}")

    pokemons_crus = []
    falhas = 0

    for especie in especies:
        nome = especie["name"]
        dados = _get_com_retry(f"{BASE_URL}/pokemon/{nome}")
        if dados is None:
            falhas += 1
            continue
        pokemons_crus.append(dados)

    if falhas > 0:
        logger.warning(f"[EXTRACT] {falhas} Pokémon(s) não puderam ser extraídos e foram ignorados")

    logger.info(f"[EXTRACT] {len(pokemons_crus)} Pokémon extraídos com sucesso da geração {geracao_id}")

    caminho = RAW_DIR / f"pokemons_geracao_{geracao_id}.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(pokemons_crus, f, ensure_ascii=False, indent=2)
    logger.info(f"[EXTRACT] Dados brutos salvos em '{caminho}'")

    return pokemons_crus


def extrair_tipos() -> list[dict]:
    """
    Extrai a matriz de efetividade de todos os tipos (fraquezas/resistências).

    Esse é o dado que alimenta o cálculo de score depois
    """
    logger.info("[EXTRACT] Iniciando extração da matriz de tipos")

    lista_tipos = _get_com_retry(f"{BASE_URL}/type")
    if lista_tipos is None:
        logger.error("[EXTRACT] Não foi possível obter a lista de tipos, abortando")
        return []

    tipos_crus = []
    for tipo in lista_tipos["results"]:
        dados = _get_com_retry(tipo["url"])
        if dados is None:
            continue
        tipos_crus.append(dados)

    logger.info(f"[EXTRACT] {len(tipos_crus)} tipos extraídos com sucesso")

    caminho = RAW_DIR / "tipos.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(tipos_crus, f, ensure_ascii=False, indent=2)
    logger.info(f"[EXTRACT] Dados brutos salvos em '{caminho}'")

    return tipos_crus


if __name__ == "__main__":
    # permite rodar `python -m src.extract.extract_pokeapi` pra testar isolado
    extrair_todos_pokemons()
    extrair_tipos()