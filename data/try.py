import pandas as pd

data = {'col1': [1, 2], 'col2': [3, 4], 'col3': [5, 6]}
df = pd.DataFrame(data)
print("Original DataFrame:")
print(df)

# Reindex columns to a new order, adding a new column 'col4' which will be NaN
new_column_order = ['col3', 'col2', 'col1', 'col4']
df_reindexed = df.reindex(columns=new_column_order) # or df.reindex(new_column_order, axis=1)

print("\nReindexed DataFrame:")
print(df_reindexed)
