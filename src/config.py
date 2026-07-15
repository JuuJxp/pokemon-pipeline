"""
Registro central das regiões que o pipeline sabe processar.

Criei esse arquivo porque, assim que decidi suportar mais de uma região,
percebi que ia precisar validar em vários lugares (scoring, DAG) se a
região pedida realmente tem um dataset de ginásios correspondente. Em vez
de repetir essa checagem em cada arquivo, centralizei aqui.

Pra adicionar uma região nova: cria o arquivo data/reference/gyms_<nome>.json
seguindo o mesmo formato dos existentes, e adiciona o nome na lista abaixo.
Não precisa mexer em mais nada.
"""
from pathlib import Path

REGIOES_DISPONIVEIS = ["kanto", "johto", "hoenn", "sinnoh"]

REFERENCE_DIR = Path(__file__).resolve().parents[1] / "data" / "reference"


def validar_regiao(regiao: str) -> None:
    """
    Levanta um erro se a região pedida não tiver dataset de ginásios,
    em vez de deixar o pipeline quebrar mais na frente com um FileNotFoundError
    """
    if regiao not in REGIOES_DISPONIVEIS:
        raise ValueError(
            f"Região '{regiao}' não suportada ainda. "
            f"Regiões disponíveis: {', '.join(REGIOES_DISPONIVEIS)}. "
            f"Pra adicionar uma nova, crie data/reference/gyms_{regiao}.json "
            f"e inclua o nome em REGIOES_DISPONIVEIS (src/config.py)."
        )