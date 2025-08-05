import os
import re
import csv
import subprocess

def extract_text_from_image(image_path):
    """Uses Tesseract to extract text from an image."""
    try:
        result = subprocess.run(
            ['tesseract', image_path, 'stdout', '-l', 'kor+eng'],
            capture_output=True, text=True, check=True, encoding='utf-8'
        )
        return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error processing {image_path}: {e}")
        return ""

def classify_receipt(text):
    """Classifies the receipt based on a hierarchy of keywords and patterns."""
    text_lower = text.lower()
    if 'coffee bean' in text_lower or '커피빈' in text_lower:
        return '커피빈'
    if 'starbucks' in text_lower or '스타벅스' in text_lower:
        return '스타벅스'
    if 'deep on' in text_lower:
        return '신한카드'
    # Add specific card number prefix for Hana Card as a fallback
    if 'hana card' in text_lower or '하나카드' in text_lower or '5181-85' in text:
        return '하나카드'
    return '기타'

def find_date(text):
    """Finds a date in YYYY-MM-DD format."""
    match = re.search(r'(20\d{2})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})일?', text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    match = re.search(r'(\d{2})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})일?', text)
    if match:
        year, month, day = match.groups()
        return f"20{year}-{month.zfill(2)}-{day.zfill(2)}"
    return "Not found"

def extract_amount_from_line(line):
    """Extracts only the numeric part of a potential amount."""
    # This regex is now simpler and only captures digits and commas.
    match = re.search(r'([\d,]{2,})', line)
    if match:
        amount_str = match.group(1).replace(',', '')
        if amount_str.isdigit():
            return amount_str
    return None

def find_amount(text, receipt_type):
    """Finds the total amount based on the receipt type and refined logic."""
    lines = text.split('\n')

    if receipt_type == '신한카드':
        card_line_index = -1
        for i, line in enumerate(lines):
            if 'deep on' in line.lower():
                card_line_index = i
                break
        if card_line_index != -1:
            # Search backwards from the line before the card name
            for i in range(card_line_index - 1, -1, -1):
                amount = extract_amount_from_line(lines[i])
                if amount and int(amount) > 100:
                    return amount

    # Keyword-based search for all types
    # Using a specific order of keywords to get the most reliable amount
    keywords = ['승인금액', '결제금액', '결제 금액', '합계', '승인 금액']
    for keyword in keywords:
        for line in lines:
            if keyword in line:
                amount = extract_amount_from_line(line)
                if amount:
                    return amount

    return "Not found"

def process_receipts(directory):
    """Processes all images in a directory."""
    receipts_data = []
    image_files = [f for f in os.listdir(directory) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    for filename in image_files:
        image_path = os.path.join(directory, filename)
        print(f"Processing {filename}...")
        text = extract_text_from_image(image_path)
        if not text:
            continue

        receipt_type = classify_receipt(text)
        date = find_date(text)
        amount = find_amount(text, receipt_type)
        
        receipts_data.append([filename, date, amount, receipt_type])
        print(f"  -> Type: {receipt_type}, Date: {date}, Amount: {amount}")

    return receipts_data

def write_to_csv(data, csv_path):
    """Writes the extracted data to a CSV file."""
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Filename', 'Date', 'Amount', 'Type'])
        writer.writerows(data)

if __name__ == "__main__":
    receipt_dir = "/Users/vinyl/Downloads/receipt/"
    output_csv = os.path.join(receipt_dir, "receipts.csv")
    
    data = process_receipts(receipt_dir)
    
    if data:
        write_to_csv(data, output_csv)
        print(f"\nSuccessfully created {output_csv} with {len(data)} entries.")
    else:
        print("No receipts were processed.")
