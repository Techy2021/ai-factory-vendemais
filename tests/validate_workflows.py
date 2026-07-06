#!/usr/bin/env python3
"""
Validador estrutural dos dois artefatos de workflow:
  1. workflows/vendemais-make-blueprint.json  (blueprint Make.com)
  2. n8n-mirror/workflows/vendemais-enrich-v0.json  (mirror n8n)

NAO chama API nenhuma. So carrega os JSON e checa a estrutura.
Roda: python tests/validate_workflows.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

MAKE_PATH = os.path.join(ROOT, "workflows", "vendemais-make-blueprint.json")
N8N_PATH = os.path.join(ROOT, "n8n-mirror", "workflows", "vendemais-enrich-v0.json")

failures = []


def check(cond, msg):
    status = "PASS" if cond else "FALHOU"
    print(f"  [{status}] {msg}")
    if not cond:
        failures.append(msg)


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


print("== Make blueprint ==")
make = load(MAKE_PATH)
check(isinstance(make.get("name"), str) and make["name"], "blueprint tem 'name' nao-vazio")
flow = make.get("flow")
check(isinstance(flow, list), "blueprint tem 'flow' como lista")
check(len(flow) >= 5, f"flow tem >= 5 modulos (achou {len(flow)})")
check(all("module" in m for m in flow), "todo item de flow tem 'module'")
check(isinstance(make.get("metadata"), dict), "blueprint tem 'metadata'")

print("== n8n mirror ==")
n8n = load(N8N_PATH)
nodes = n8n.get("nodes")
connections = n8n.get("connections")
check(isinstance(nodes, list), "mirror tem 'nodes' como lista")
check(len(nodes) >= 5, f"nodes tem >= 5 nodes (achou {len(nodes)})")
check(isinstance(connections, dict), "mirror tem 'connections' como objeto")

node_names = {n.get("name") for n in nodes}
# toda conexao (origem e destino) referencia um node existente
refs_ok = True
for src, payload in connections.items():
    if src not in node_names:
        refs_ok = False
    for outputs in payload.get("main", []):
        for link in outputs:
            if link.get("node") not in node_names:
                refs_ok = False
check(refs_ok, "todas as connections referenciam nodes existentes")

# o fluxo encadeia os 5 passos (cada node, exceto o ultimo, tem saida)
chained = sum(1 for s in connections if s in node_names)
check(chained >= 4, f"ha encadeamento entre os passos (>= 4 origens, achou {chained})")

print()
if failures:
    print(f"RESULTADO: {len(failures)} verificacao(oes) falhou(aram).")
    sys.exit(1)
print("RESULTADO: todas as verificacoes passaram.")
