import pandas as pd

df = pd.DataFrame(columns=['Наименование', 'Показатель'])
df.loc[len(df.index)] = [20, 7]
print(df.to_excel('1.xlsx', index=False))