import argparse
import asyncio
import sys
import logging
import ollama

from configs.config import ModelsConfig
from database.session import create_db_engine
from processing.retriever import Retriever
from processing.generator import Generator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


async def main(top_k: int):
    model_name = "qwen2.5:3b"
    client = ollama.AsyncClient(host="http://localhost:11434")

    if not await check_ollama_model(client, model_name):
        return

    engine = create_db_engine()
    retriever = Retriever(engine, ModelsConfig.EMBEDDER, ModelsConfig.RERANKER)
    generator = Generator(client=client, model_name=model_name)

    try:
        await run_chat_loop(retriever, generator, top_k)
    finally:
        engine.dispose()


async def run_chat_loop(retriever: Retriever, generator: Generator, top_k: int):
    while True:
        try:
            question = await asyncio.to_thread(input, "\nВы: ")
            
            question = question.strip()
            if not question:
                continue
            
            if question.lower() in ("exit", "quit", "q", "выход"):
                print("Завершение работы...")
                break

            await process_question(question, top_k, retriever, generator)

        except KeyboardInterrupt:
            print("\nПрервано пользователем. Выход.")
            break
        except EOFError:
            break


async def process_question(
    question: str, 
    top_k: int, 
    retriever: Retriever, 
    generator: Generator
):
    print(f"\nВопрос: {question}")
    print("-" * 60)
    
    chunks = retriever.search(question, top_k=top_k)
    contexts = [c.text for c in chunks]
    
    print("[Ответ модели]:")
    async for token in generator.generate_stream(question, contexts):
        print(token, end="", flush=True)
    print("\n" + "=" * 60)


async def check_ollama_model(client: ollama.AsyncClient, model_name: str) -> bool:
    logger.info("Проверка доступности модели в Ollama...")
    try:
        models_info = await client.list()
        available_models = [m.model for m in models_info.models]
        if model_name not in available_models:
            logger.error(f"Модель {model_name} не найдена в Ollama!")
            return False
        return True
    except Exception as e:
        logger.error(f"Не удалось подключиться к Ollama: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Интерактивный RAG-ассистент")
    parser.add_argument("--top-k", type=int, default=5, help="Количество чанков для контекста (по умолчанию 5)")
    args = parser.parse_args()
    
    try:
        asyncio.run(main(args.top_k))
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")
        sys.exit(0)