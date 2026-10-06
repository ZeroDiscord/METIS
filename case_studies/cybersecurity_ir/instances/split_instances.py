"""
Split multi-instance YAML files into individual cyber-001.yaml ... cyber-012.yaml files.
"""
import yaml
import os

instances_dir = os.path.dirname(os.path.abspath(__file__))

sources = [
    "easy_instances.yaml",
    "misleading_instances.yaml",
    "conflicting_instances.yaml",
]

total_exported = 0

for src in sources:
    src_path = os.path.join(instances_dir, src)
    if not os.path.exists(src_path):
        continue
    with open(src_path, "r", encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))
    for doc in docs:
        if not doc:
            continue
        for key, data in doc.items():
            if isinstance(data, dict) and "instance_id" in data:
                inst_id = data["instance_id"]
                out_path = os.path.join(instances_dir, f"{inst_id}.yaml")
                with open(out_path, "w", encoding="utf-8") as out_f:
                    yaml.dump(data, out_f, default_flow_style=False, sort_keys=False)
                print(f"Exported {inst_id} to {out_path}")
                total_exported += 1

print(f"Total exported: {total_exported} instances.")
