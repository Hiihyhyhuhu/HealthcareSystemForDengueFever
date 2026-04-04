import pandas as pd

df = pd.read_csv("output/metadata.csv")
reorder = ["filename", "query", "language", "image_url", "page_url", "status"]
df = df.reindex(columns=reorder)

df.to_csv("output/metadata.csv", index=False)