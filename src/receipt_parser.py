# -*- coding: utf-8 -*-
import subprocess
import re
import os
import logging
from PIL import Image, ImageEnhance

logger = logging.getLogger(__name__)

def _preprocess_image(image_path):
    """Preprocesses the image for better OCR results."""
    try:
        img = Image.open(image_path)
        # Convert to grayscale
        img = img.convert('L')
        # Increase contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        
        processed_image_path = os.path.splitext(image_path)[0] + "_processed.png"
        img.save(processed_image_path)
        return processed_image_path
    except Exception as e:
        logger.error(f"Error during image preprocessing for {image_path}: {e}")
        return None

def extract_text_from_image(image_path):
    """Uses Tesseract to extract text from an image after preprocessing."""
    processed_image_path = _preprocess_image(image_path)
    if not processed_image_path:
        return ""

    try:
        result = subprocess.run(
            ['tesseract', processed_image_path, 'stdout', '-l', 'kor+eng', '--psm', '6'],
            capture_output=True, text=True, check=True, encoding='utf-8'
        ).stdout
        logger.debug(f"Successfully extracted text from {image_path}:\n---START TEXT---\n{result}\n---END TEXT---")
        return result
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Error processing {processed_image_path}: {e}")
        return ""
    finally:
        if os.path.exists(processed_image_path):
            os.remove(processed_image_path)

def classify_receipt(text):
    """Classifies the receipt based on a hierarchy of keywords and patterns."""
    text_lower = text.lower()
    receipt_type = '기타' # Default
    if 'coffee bean' in text_lower or '커피빈' in text_lower:
        receipt_type = '커피빈'
    elif 'starbucks' in text_lower or '스타벅스' in text_lower:
        receipt_type = '스타벅스'
    elif 'deep on' in text_lower:
        receipt_type = '신한카드'
    elif 'hana card' in text_lower or '하나카드' in text_lower or '5181-85' in text:
        receipt_type = '하나카드'
    elif 'samsung card' in text_lower or '삼성카드' in text_lower:
        receipt_type = '삼성카드'
    
    logger.debug(f"Classified receipt as: {receipt_type}")
    return receipt_type

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

def find_time(text):
    """Finds a time in HH:MM:SS format from the receipt text."""
    # Priority 1: Look for time near keywords like 승인시간, 결제시간, 거래시간
    time_keywords = ['승인시간', '결제시간', '거래시간', '시간', '결제일시', '승인일시']
    for keyword in time_keywords:
        # Find keyword and look for time pattern nearby
        keyword_pattern = rf'{keyword}[:\s]*(\d{{1,2}})[:\s시](\d{{2}})[:\s분]?(\d{{2}})?초?'
        match = re.search(keyword_pattern, text)
        if match:
            hour, minute, second = match.groups()
            second = second if second else "00"
            time_str = f"{hour.zfill(2)}:{minute.zfill(2)}:{second.zfill(2)}"
            logger.debug(f"Found time '{time_str}' using keyword '{keyword}'")
            return time_str

    # Priority 2: Look for 오전/오후 (AM/PM) format
    ampm_pattern = r'(오전|오후)\s*(\d{1,2})[:\s시](\d{2})[:\s분]?(\d{2})?초?'
    match = re.search(ampm_pattern, text)
    if match:
        ampm, hour, minute, second = match.groups()
        hour = int(hour)
        if ampm == '오후' and hour != 12:
            hour += 12
        elif ampm == '오전' and hour == 12:
            hour = 0
        second = second if second else "00"
        time_str = f"{str(hour).zfill(2)}:{minute.zfill(2)}:{second.zfill(2)}"
        logger.debug(f"Found time '{time_str}' using AM/PM pattern")
        return time_str

    # Priority 3: Look for standard time patterns (HH:MM:SS or HH:MM)
    # First try HH:MM:SS
    time_pattern = r'(\d{1,2}):(\d{2}):(\d{2})'
    match = re.search(time_pattern, text)
    if match:
        hour, minute, second = match.groups()
        if 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59 and 0 <= int(second) <= 59:
            time_str = f"{hour.zfill(2)}:{minute.zfill(2)}:{second.zfill(2)}"
            logger.debug(f"Found time '{time_str}' using HH:MM:SS pattern")
            return time_str

    # Try HH:MM pattern
    time_pattern = r'(\d{1,2}):(\d{2})(?!\d|:)'
    match = re.search(time_pattern, text)
    if match:
        hour, minute = match.groups()
        if 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59:
            time_str = f"{hour.zfill(2)}:{minute.zfill(2)}:00"
            logger.debug(f"Found time '{time_str}' using HH:MM pattern")
            return time_str

    # Priority 4: Look for Korean time format (XX시 XX분)
    korean_time_pattern = r'(\d{1,2})시\s*(\d{2})분(?:\s*(\d{2})초)?'
    match = re.search(korean_time_pattern, text)
    if match:
        hour, minute, second = match.groups()
        second = second if second else "00"
        if 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59:
            time_str = f"{hour.zfill(2)}:{minute.zfill(2)}:{second.zfill(2)}"
            logger.debug(f"Found time '{time_str}' using Korean time pattern")
            return time_str

    logger.debug("Time not found, returning default 00:00:00")
    return "00:00:00"

def _extract_amount_with_won(line):
    """Extracts an amount from a line that follows the 'X,XXX 원' pattern."""
    match = re.search(r'([\d,]+)\s*원', line)
    if match:
        amount_str = match.group(1).replace(',', '')
        if amount_str.isdigit():
            logger.debug(f"Extracted amount '{amount_str}' using '원' pattern from line: '{line.strip()}'")
            return amount_str
    return None

def extract_amount_from_line(line):
    """Extracts only the numeric part of a potential amount, handling commas and periods."""
    match = re.search(r'(\d{1,3}(?:[.,]\d{3})*)', line)
    if match:
        amount_str = match.group(1).replace(',', '').replace('.', '')
        if amount_str.isdigit():
            logger.debug(f"Extracted amount '{amount_str}' from line: '{line.strip()}'")
            return amount_str
    return None

def find_amount(text, receipt_type):
    """Finds the total amount based on the receipt type and refined logic."""
    logger.debug(f"Finding amount for receipt type: {receipt_type}")
    lines = text.split('\n')

    if receipt_type == '신한카드':
        logger.debug("Using '신한카드' specific logic.")
        card_line_index = -1
        for i, line in enumerate(lines):
            if 'deep on' in line.lower():
                card_line_index = i
                logger.debug(f"Found 'deep on' at line {i}.")
                break
        if card_line_index != -1:
            for i in range(card_line_index - 1, -1, -1):
                line = lines[i]
                logger.debug(f"Scanning line above 'deep on': '{line.strip()}'")
                amount = extract_amount_from_line(line)
                if amount and int(amount) > 100:
                    logger.debug(f"Found amount {amount} using '신한카드' logic.")
                    return amount

    elif receipt_type in ['하나카드', '삼성카드']:
        logger.debug(f"Using '{receipt_type}' specific logic looking for '원' pattern.")
        potential_amounts = []
        for line in lines:
            amount = _extract_amount_with_won(line)
            if amount:
                potential_amounts.append(int(amount))
        
        if potential_amounts:
            max_amount = max(potential_amounts)
            logger.debug(f"Found amounts {potential_amounts}. Returning max: {max_amount}.")
            return str(max_amount)

    logger.debug("Using general keyword logic.")
    keywords = ['승인금액', '결제금액', '결제 금액', '합계', '승인 금액']
    for keyword in keywords:
        for line in lines:
            if keyword in line:
                logger.debug(f"Found keyword '{keyword}' in line: '{line.strip()}'")
                amount = extract_amount_from_line(line)
                if amount:
                    logger.debug(f"Found amount {amount} using keyword '{keyword}'.")
                    return amount
    
    logger.warning("Could not find amount in receipt.")
    return "Not found"