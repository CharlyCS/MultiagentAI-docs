"""CLI de prueba:  python -m agent.image_agent ["Nombre Empresa"]  (por defecto: client de config.yaml)"""

import argparse
import logging

import yaml

from .config import PROJECT_ROOT
from .image_web_agent import ImageWebAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Busca el logo de una empresa.")
    parser.add_argument("client_name", nargs="*", help="Nombre de la empresa")
    parser.add_argument("--skip-workflow", action="store_true",
                        help="Prueba solo el agente ReAct (debug)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for noisy in ("httpx", "ddgs", "primp", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    name = " ".join(args.client_name) or yaml.safe_load(
        open(PROJECT_ROOT / "data" / "config.yaml", encoding="utf-8"))["client"]

    if args.skip_workflow:
        from .react_agent import run_react_agent
        res = run_react_agent(name)
        print(res.get("image_path"), "| fuente:", res.get("source"), "| respaldo:", res.get("backup_url"))
        return

    agent = ImageWebAgent(name)
    print(agent.run())
    print("encontrado por:", agent.result.get("found_by"), "| fuente:", agent.result.get("source"))


if __name__ == "__main__":
    main()
