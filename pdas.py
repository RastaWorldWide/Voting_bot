import json
import pandas as pd

with open("C:/Users/ikuli/Downloads/votes2.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

# Преобразуем: из {id: record} → [record1, record2, ...]
records = list(data.values())

# Или, если хотите сохранить chat_id как колонку (а не потерять его):
# records = [{**v, 'chat_id_key': k} for k, v in data.items()]  # если chat_id не дублируется внутри

df = pd.DataFrame(records)

# При необходимости упорядочить колонки:
df = df[['chat_id', 'fio', 'department', 'nominee', 'date']]

df.to_excel('votes2.xlsx', index=False, engine='openpyxl')