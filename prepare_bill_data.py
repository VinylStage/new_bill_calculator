
import pandas as pd

def convert_receipts_to_bill_data(receipts_file, output_file):
    """
    Converts the receipts CSV to the format required by the bill calculator.
    """
    try:
        # Read the sorted and numbered receipts file
        receipts_df = pd.read_csv(receipts_file)

        # Check for necessary columns
        if 'No.' not in receipts_df.columns or 'Amount' not in receipts_df.columns:
            print("Error: receipts.csv is missing 'No.' or 'Amount' columns.")
            return

        # Create the new dataframe with 'Item' and 'Amount'
        # 'Item' will be the number from the 'No.' column
        bill_data_df = receipts_df[['No.', 'Amount']].copy()
        bill_data_df.rename(columns={'No.': 'Item'}, inplace=True)

        # Save the new CSV in the required format
        bill_data_df.to_csv(output_file, index=False)
        
        print(f"Successfully converted {receipts_file} to {output_file}")

    except FileNotFoundError:
        print(f"Error: The file {receipts_file} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Input file is our main receipts CSV
    source_csv = "/Users/vinyl/Downloads/receipt/receipts.csv"
    # Output file is the one the calculator script expects
    destination_csv = "/Users/vinyl/Downloads/receipt/bill_calculator/data.csv"
    
    convert_receipts_to_bill_data(source_csv, destination_csv)
