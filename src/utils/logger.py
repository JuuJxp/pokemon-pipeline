"""
Configuração central de logging do pipeline.

Reaproveita o padrão criado na Semana 5 (formato com horário e nível,
handlers.clear() para permitir reimportação segura, propagate=False para
não vazar pros loggers do root/Airflow), mas agora grava também em arquivo
dentro de logs/, o que a versão em notebook não fazia.
"""
import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(exist_ok=True)


def get_logger(nome: str = "pipeline_pokemon") -> logging.Logger:
    logger = logging.getLogger(nome)

    if logger.handlers:
        # já configurado (evita handlers duplicados se a função for chamada
        # mais de uma vez, ex: dentro de tasks do Airflow)
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler_console = logging.StreamHandler(sys.stdout)
    handler_console.setFormatter(formatter)
    handler_console.setLevel(logging.INFO)

    handler_arquivo = logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8")
    handler_arquivo.setFormatter(formatter)
    handler_arquivo.setLevel(logging.DEBUG)

    logger.addHandler(handler_console)
    logger.addHandler(handler_arquivo)

    return logger