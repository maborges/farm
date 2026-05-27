import asyncio
from loguru import logger

from core.background_jobs import run_background_jobs


def main() -> None:
    try:
        asyncio.run(run_background_jobs())
    except KeyboardInterrupt:
        logger.info("Background worker parado pelo usuário.")
    finally:
        from core.database import engine

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(engine.dispose())
            logger.info("Database engine disposed in background worker.")
        except Exception as exc:
            logger.error(f"Erro ao fechar engine no background worker: {exc}")
        finally:
            loop.close()


if __name__ == "__main__":
    main()
