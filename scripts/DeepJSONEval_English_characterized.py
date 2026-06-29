import pandas as pd
import json

# ===========================
# Input / Output
# ===========================
INPUT_FILE = "DeepJSONEval_English - DeepJSONEval_English(1).csv"
OUTPUT_FILE = "DeepJSONEval_English_characterized.csv"

df = pd.read_csv(INPUT_FILE)

# --------------------------------------------------
# Helper functions
# --------------------------------------------------

primitive_types = {"string", "integer", "number", "boolean", "null"}

def walk(schema):
    """Yield every node in a JSON schema."""
    if isinstance(schema, dict):
        yield schema

        # properties
        if "properties" in schema:
            for child in schema["properties"].values():
                yield from walk(child)

        # items
        if "items" in schema:
            yield from walk(schema["items"])

        # composition keywords
        for key in ["anyOf", "oneOf", "allOf"]:
            if key in schema:
                for child in schema[key]:
                    yield from walk(child)

def collect_types(schema):
    types = set()

    for node in walk(schema):
        t = node.get("type")

        if isinstance(t, str):
            if t in primitive_types:
                types.add(t)

        elif isinstance(t, list):
            for x in t:
                if x in primitive_types:
                    types.add(x)

    return ", ".join(sorted(types))

def has_array(schema):
    return any(node.get("type") == "array" for node in walk(schema))

def array_of_objects(schema):
    for node in walk(schema):
        if node.get("type") == "array":
            items = node.get("items", {})
            if isinstance(items, dict):
                if items.get("type") == "object":
                    return True
    return False

def array_of_primitives(schema):
    for node in walk(schema):
        if node.get("type") == "array":
            items = node.get("items", {})
            if isinstance(items, dict):
                t = items.get("type")
                if t in primitive_types:
                    return True
    return False

def nesting_depth(schema):
    """
    Maximum object nesting depth.
    Root object = depth 1.
    """

    def dfs(node, depth):

        max_depth = depth

        if isinstance(node, dict):

            if node.get("type") == "object":
                props = node.get("properties", {})
                for child in props.values():
                    max_depth = max(max_depth, dfs(child, depth + 1))

            elif node.get("type") == "array":
                items = node.get("items", {})
                max_depth = max(max_depth, dfs(items, depth))

        return max_depth

    start = 1 if schema.get("type") == "object" else 0
    return dfs(schema, start)

def has_enum(schema):
    return any("enum" in node for node in walk(schema))


# --------------------------------------------------
# Characterize each schema
# --------------------------------------------------

rows = []

for _, row in df.iterrows():

    schema = json.loads(row["schema"])

    rows.append({
        "true_depth": row["true_depth"],
        "primitive_types": collect_types(schema),
        "has_array": has_array(schema),
        "array_of_objects": array_of_objects(schema),
        "array_of_primitives": array_of_primitives(schema),
        "detected_nesting_depth": nesting_depth(schema),
        "has_enum": has_enum(schema)
    })

# Save results
result = pd.DataFrame(rows)
result.to_csv(OUTPUT_FILE, index=False)

print(f"Saved {OUTPUT_FILE}")
print(result.head())