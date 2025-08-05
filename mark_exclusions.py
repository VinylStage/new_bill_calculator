
import pandas as pd

def mark_excluded_items(csv_file, excluded_ids):
    """
    Adds an 'Exclude' column to the CSV file based on a list of IDs.
    """
    try:
        df = pd.read_csv(csv_file)

        # Ensure the 'No.' column exists
        if 'No.' not in df.columns:
            print(f"Error: No 'No.' column found in {csv_file}")
            return

        # Add the '제외유무' (Exclude Y/N) column
        # Mark 'Y' if the item number is in the excluded list, otherwise 'N'
        df['제외유무'] = df['No.'].apply(lambda x: 'Y' if x in excluded_ids else 'N')

        # Save the updated dataframe back to the CSV
        df.to_csv(csv_file, index=False)

        print(f"Successfully added '제외유무' column to {csv_file}")

    except FileNotFoundError:
        print(f"Error: The file {csv_file} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    receipts_csv_path = "/Users/vinyl/Downloads/receipt/receipts.csv"
    # This is the list of item numbers to be excluded from the calculator script
    items_to_exclude = [2, 3, 4, 5, 7, 10, 11, 12, 13, 14, 15, 16, 19, 20, 21, 25]
    
    mark_excluded_items(receipts_csv_path, items_to_exclude)
