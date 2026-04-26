"""Create the MongoDB Atlas Vector Search index for NaviRag Trading."""

from src.utils.mongodb import MongoDBClient


def main() -> None:
    """Request creation of the configured MongoDB Atlas vector index."""
    try:
        created = MongoDBClient().create_vector_index()
    except RuntimeError as error:
        print(str(error))
    except Exception as error:
        print(f"No se pudo crear/verificar el indice vectorial. Tipo: {type(error).__name__}")
    else:
        if created:
            print("Indice vectorial solicitado en MongoDB Atlas.")
        else:
            print("Indice vectorial ya existia en MongoDB Atlas.")


if __name__ == "__main__":
    main()
