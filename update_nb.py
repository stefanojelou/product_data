import json
import os
import pandas as pd # Not used but good to have in context if needed

nb_path = 'notebooks/analysis copy 2.ipynb'
with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Define modifications
mod_A_needle = "sessions_duration = load_if_exists('sessions_duration.csv')"
mod_A_code = [
    "\n",
    "nodes_usage = load_if_exists('nodes_usage.csv')\n",
    "if nodes_usage is not None:\n",
    "    nodes_usage['company_id'] = pd.to_numeric(nodes_usage['company_id'], errors='coerce')\n"
]

mod_B_needle = "final = final.merge(sessions_duration, on='company_id', how='left')"
mod_B_code = [
    "\n",
    "    # Merge nodes usage if available\n",
    "    if 'nodes_usage' in dir() and nodes_usage is not None:\n",
    "        # Aggregate total nodes per company\n",
    "        nodes_agg = nodes_usage.groupby('company_id')['nodes_created'].sum().reset_index(name='total_nodes_created')\n",
    "        final = final.merge(nodes_agg, on='company_id', how='left')\n",
    "        final['total_nodes_created'] = final['total_nodes_created'].fillna(0).astype(int)\n",
    "    else:\n",
    "        final['total_nodes_created'] = 0\n"
]

# Apply modifications
cells_modified = 0
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        
        # Mod A
        if mod_A_needle in source and "nodes_usage =" not in source:
            cell['source'].extend(mod_A_code)
            print("Applied Mod A (Loading)")
            cells_modified += 1
            
        # Mod B
        if mod_B_needle in source and "nodes_agg =" not in source:
            # Append to end of cell
            cell['source'].extend(mod_B_code)
            print("Applied Mod B (Merging)")
            cells_modified += 1

if cells_modified > 0:
    with open(nb_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)
    print(f"Saved {nb_path} with {cells_modified} modifications.")
else:
    print("No modifications applied (maybe already present).")

