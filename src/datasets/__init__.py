from src.datasets.arqa import load_arqa
from src.datasets.deepjson import load_deepjson
from src.datasets.schema_to_json import load_schema_to_json


def load_dataset(dataset_name, dataset_path, context_path=None, max_rows=None):
    name = dataset_name.lower()

    if name == "arqa":
        return load_arqa(
            dataset_path=dataset_path,
            context_path=context_path,
            max_rows=max_rows,
        )

    if name in ["deepjsoneval", "deepjson"]:
        return load_deepjson(
            dataset_path=dataset_path,
            max_rows=max_rows,
        )

    if name in ["schematojson", "schema_to_json", "schema-to-json"]:
        return load_schema_to_json(
            dataset_path=dataset_path,
            max_rows=max_rows,
        )

    raise ValueError(f"Unknown dataset: {dataset_name}")
