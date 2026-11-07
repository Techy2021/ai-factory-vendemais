from collections import Counter
import json

from pydantic import ValidationError

from app.airtable import AirtableClient, AirtableConfig, AirtableError
from app.main import _score_for_lead
from app.models import Lead


def main() -> None:
    examined = 0
    valid = 0
    invalid = 0
    failures: Counter[tuple[str, str]] = Counter()

    try:
        client = AirtableClient(AirtableConfig.from_env())
        for record in client.iter_records():
            examined += 1
            normalized_record = dict(record)
            normalized_record["icp_match_score"] = _score_for_lead(
                record.get("icp_match_score")
            )

            try:
                Lead.model_validate(normalized_record)
            except ValidationError as error:
                invalid += 1
                for detail in error.errors(
                    include_input=False,
                    include_context=False,
                    include_url=False,
                ):
                    location = detail["loc"]
                    field_name = ".".join(str(part) for part in location) or "<modelo>"
                    failures[(field_name, str(detail["type"]))] += 1
            else:
                valid += 1
    except AirtableError:
        raise SystemExit(
            "Diagnostico interrompido: falha segura no cliente Airtable."
        ) from None

    summary = {
        "total_registros_examinados": examined,
        "validos": valid,
        "invalidos": invalid,
        "falhas_por_campo_e_tipo": [
            {"campo": field, "tipo": failure_type, "frequencia": count}
            for (field, failure_type), count in sorted(failures.items())
        ],
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
