
import csv

def sort_and_number_csv(file_path):
    """Sorts a CSV by date and adds a numbering column."""
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)  # Skip header
            # Read data and handle potential errors
            data = []
            for row in reader:
                # Ensure row has the expected number of columns
                if len(row) == 4:
                    data.append(row)
                else:
                    print(f"Skipping malformed row: {row}")

        # Sort data by the 'Date' column (index 1)
        # This handles 'Not found' dates by placing them at the end
        data.sort(key=lambda x: (x[1] == 'Not found', x[1]))

        # Write back with numbering
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # Add 'No.' to the header
            writer.writerow(['No.'] + header)
            # Write numbered and sorted rows
            for i, row in enumerate(data, 1):
                writer.writerow([i] + row)
        
        print(f"Successfully sorted and numbered {file_path}")

    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    csv_file = "/Users/vinyl/Downloads/receipt/receipts.csv"
    sort_and_number_csv(csv_file)
