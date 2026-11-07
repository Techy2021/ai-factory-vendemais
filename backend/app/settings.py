import os


ENVIRONMENT = os.environ.get("VENDEMAIS_ENV", "production")
if ENVIRONMENT not in {"development", "production"}:
    raise RuntimeError("VENDEMAIS_ENV deve ser development ou production.")

IS_PRODUCTION = ENVIRONMENT == "production"
