import pandas as pd
import os

# Get absolute paths relative to this script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)

input_file = os.path.join(backend_dir, "data", "raw_excel", "RAK_Ceramics_With_Pages_Linked.xlsx")
output_file = os.path.join(backend_dir, "data", "processed_csv", "products_cleaned.csv")

# Read Excel
df = pd.read_excel(input_file)

# Standardize column names (strip, lowercase, replace spaces)
df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

# Map 'image_link' to 'image_path' for consistency if it exists
if 'image_link' in df.columns:
    df = df.rename(columns={'image_link': 'image_path'})

# Remove completely empty rows
df = df.dropna(how="all")

# Remove duplicate rows
df = df.drop_duplicates()

# Fill missing values with empty string
df = df.fillna("")

# Convert all string columns to stripped text
for col in df.columns:
    if df[col].dtype == "object":
        df[col] = df[col].astype(str).str.strip()

# Save cleaned CSV
os.makedirs(os.path.dirname(output_file), exist_ok=True)
df.to_csv(output_file, index=False)

print("Cleaned CSV saved successfully!")
print(f"Rows: {len(df)}")
print(f"Columns: {list(df.columns)}")