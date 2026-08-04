# -*- coding: utf-8 -*-
import subprocess
import re
import os
import logging
from PIL import Image, ImageEnhance, ImageFilter

import config

logger = logging.getLogger(__name__)

def _preprocess_image(image_path):
    """Preprocesses the image for better OCR results."""
    try:
        img = Image.open(image_path).convert('L')

        # Phone photos of receipts are often downscaled to ~1024px, leaving the
        # small print below Tesseract's minimum legible x-height.
        short_side = min(img.size)
        if short_side < config.OCR_MIN_SHORT_SIDE:
            scale = min(config.OCR_MAX_UPSCALE, config.OCR_MIN_SHORT_SIDE / short_side)
            img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
            img = ImageEnhance.Contrast(img).enhance(1.5)
            logger.debug(f"Upscaled {os.path.basename(image_path)} by {scale:.2f}x to {img.size}")
        else:
            img = ImageEnhance.Contrast(img).enhance(2.0)

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

    command = ['tesseract', processed_image_path, 'stdout', '-l', 'kor+eng', '--psm', '6']
    if config.TESSDATA_DIR and os.path.isdir(config.TESSDATA_DIR):
        command += ['--tessdata-dir', config.TESSDATA_DIR]

    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=True, encoding='utf-8'
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
    elif '상세 이용내역' in text and '결제확정' in text:
        receipt_type = '신한카드(앱)'
    elif '신한카드' in text:
        receipt_type = '신한카드(실물)'
    elif 'deep on' in text_lower:
        receipt_type = '신한카드'
    elif 'hana card' in text_lower or '하나카드' in text_lower or '5181-85' in text:
        receipt_type = '하나카드'
    elif 'samsung card' in text_lower or '삼성카드' in text_lower or '삼성' in text_lower:
        receipt_type = '삼성카드'
    
    logger.debug(f"Classified receipt as: {receipt_type}")
    return receipt_type

def find_date(text):
    """Finds a date in YYYY-MM-DD format."""
    for pattern, prefix in ((r'(20\d{2})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})일?', ''),
                            (r'(\d{2})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})일?', '20')):
        for match in re.finditer(pattern, text):
            year, month, day = match.groups()
            if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                return f"{prefix}{year}-{month.zfill(2)}-{day.zfill(2)}"
            logger.debug(f"Rejected implausible date candidate: '{match.group(0).strip()}'")
    logger.warning("Could not find a valid date in receipt.")
    return "Not found"

def find_time(text):
    """Finds a time in HH:MM:SS format from the receipt text."""
    # Priority 1: Look for time near keywords like 승인시간, 결제시간, 거래시간
    time_keywords = ['승인일시', '승인시간', '결제일시', '결제시간', '거래일시', '거래시간', '시간']
    for keyword in time_keywords:
        # Tolerate OCR-inserted spaces inside the keyword ('승인 일시') and an
        # intervening date ('[승인 일시] 2026-07-03 11:41:17').
        spaced = r'\s*'.join(keyword)
        keyword_pattern = (
            rf'{spaced}[^\d\n]*(?:\d{{2,4}}[-./]\d{{1,2}}[-./]\d{{1,2}}\s*)?'
            rf'(\d{{1,2}})[:\s시](\d{{2}})[:\s분]?(\d{{2}})?초?'
        )
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
    """Extracts a comma-formatted amount (X,XXX or X,XXX,XXX) followed by 원 suffix."""
    match = re.search(r'(\d{1,3}(?:,\d{3})+)\s*원', line)
    if match:
        amount_str = match.group(1).replace(',', '')
        if amount_str.isdigit():
            logger.debug(f"Extracted amount '{amount_str}' using '원' pattern from line: '{line.strip()}'")
            return amount_str
    return None

def extract_amount_from_line(line):
    """Extracts a comma-formatted amount from a line, tolerating OCR-inserted spaces."""
    match = re.search(r'(\d{1,3}(?:\s*[,，.]\s*\d{3})+)', line)
    if match:
        amount_str = re.sub(r'[\s,，.]', '', match.group(1))
        if amount_str.isdigit():
            logger.debug(f"Extracted amount '{amount_str}' from line: '{line.strip()}'")
            return amount_str
    return None

# Lines carrying comma-formatted numbers that are never the payment total:
# 해피콘/카카오페이 굿딜 preloads a 500,000원 balance, and merchant addresses
# contain building numbers like '203,204호'.
_NON_AMOUNT_LINE_RE = re.compile(r'잔\s*액|잔\s*여|포\s*인\s*트|적\s*립|주\s*소')

def _extract_amounts_universal(text):
    """Finds all plausible receipt amounts using relaxed matching (handles OCR spaces/periods)."""
    pattern = re.compile(r'(\d{1,3}(?:\s*[,，.]\s*\d{3})+)')
    amounts = []
    for line in text.split('\n'):
        if _NON_AMOUNT_LINE_RE.search(line):
            logger.debug(f"Skipping non-amount line: '{line.strip()}'")
            continue
        for match in pattern.finditer(line):
            cleaned = re.sub(r'[\s,，.]', '', match.group(1))
            if cleaned.isdigit():
                amount = int(cleaned)
                if 1000 <= amount <= 9999900:
                    amounts.append(amount)
    return amounts

def _pick_most_likely_amount(amounts):
    """Returns the most frequent amount, ties broken by the largest value.
    A receipt's real total repeats across lines while noise (coupon balances,
    address digits) appears once, so frequency beats magnitude."""
    if not amounts:
        return None
    counts = {}
    for amount in amounts:
        counts[amount] = counts.get(amount, 0) + 1
    max_count = max(counts.values())
    return max(a for a, c in counts.items() if c == max_count)

def _extract_amounts_keyword_nofmt(text):
    """Last-resort: finds 4-5 digit amounts on total-keyword lines where OCR dropped the comma."""
    keyword_re = re.compile(r'(?:합\s*계|결제\s*금액|승인\s*금액|지불\s*금액|총\s*액)')
    amounts = []
    for line in text.split('\n'):
        if keyword_re.search(line):
            for m in re.finditer(r'\b(\d{4,5})\b', line):
                amount = int(m.group(1))
                if 1000 <= amount <= 99999:
                    amounts.append(amount)
    return amounts

def _find_vat_pair_totals(text):
    """Returns the charges implied by each 공급가/부가세 pair, in document order.

    Korean VAT is exactly 10%, so a supply value paired with a tax value one tenth
    its size implies a charge of their sum. A receipt split between several payers
    prints the shared bill first and this card's own approval last, which makes a
    second pair the tell-tale of a split payment."""
    numbers = []
    for match in re.finditer(r'(\d{1,3}(?:\s*[,，.]\s*\d{3})+)', text):
        cleaned = re.sub(r'[\s,，.]', '', match.group(1))
        if cleaned.isdigit() and 1000 <= int(cleaned) <= 9999900:
            numbers.append(int(cleaned))

    totals = []
    for i, supply in enumerate(numbers):
        # The tax always follows its supply value within a line or two.
        for vat in numbers[i + 1:i + 4]:
            if supply > vat and abs(supply / 10 - vat) <= 1.5:
                total = supply + vat
                if total not in totals:
                    totals.append(total)
    return totals

def detect_split_payment(text):
    """Returns (bill total, amount charged to this card) when the receipt looks
    split between payers, otherwise None."""
    totals = _find_vat_pair_totals(text)
    if len(totals) > 1 and totals[-1] < totals[0]:
        return totals[0], totals[-1]
    return None

def find_amount(text, receipt_type):
    """Finds the total amount based on the receipt type and refined logic."""
    logger.debug(f"Finding amount for receipt type: {receipt_type}")
    lines = text.split('\n')

    # A bill split between payers shows the shared total and, further down, the
    # amount this card was actually approved for — which is what gets claimed.
    split = detect_split_payment(text)
    if split:
        bill_total, charged = split
        logger.warning(
            f"분할 결제로 보입니다. 영수증 전체 금액 {bill_total:,}원 중 "
            f"이 카드 승인분 {charged:,}원을 사용합니다."
        )
        return str(charged)

    if receipt_type == '신한카드(앱)':
        logger.debug("Using '신한카드(앱)' specific logic.")
        start_idx = -1
        end_idx = len(lines)
        for i, line in enumerate(lines):
            if '상세 이용내역' in line:
                start_idx = i
            if start_idx != -1 and '공급가' in line:
                end_idx = i
                break
        for line in lines[start_idx + 1:end_idx]:
            match = re.search(r'(\d{1,3}(?:,\d{3})+)', line)
            if match:
                amount = match.group(1).replace(',', '')
                if int(amount) > 100:
                    logger.debug(f"Found amount {amount} using '신한카드(앱)' logic.")
                    return amount

    elif receipt_type == '신한카드(실물)':
        logger.debug("Using '신한카드(실물)' specific logic.")
        amounts = []
        for line in lines:
            if _NON_AMOUNT_LINE_RE.search(line):
                continue
            match = re.search(r'(\d{1,3}(?:,\d{3})+)', line)
            if match:
                amount = int(match.group(1).replace(',', ''))
                if amount > 100:
                    amounts.append(amount)
        if amounts:
            picked = _pick_most_likely_amount(amounts)
            logger.debug(f"Found amount {picked} using '신한카드(실물)' logic (candidates: {amounts}).")
            return str(picked)

    elif receipt_type == '신한카드':
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
        logger.debug(f"Using '{receipt_type}' specific logic.")
        won_amounts = []
        for line in lines:
            amount = _extract_amount_with_won(line)
            if amount:
                won_amounts.append(int(amount))
        universal_amounts = _extract_amounts_universal(text)
        all_amounts = won_amounts + universal_amounts
        if all_amounts:
            picked = _pick_most_likely_amount(all_amounts)
            logger.debug(f"Found amounts (원:{won_amounts}, universal:{universal_amounts}). Selected: {picked}.")
            return str(picked)

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

    logger.debug("Using universal amount fallback.")
    relaxed = _extract_amounts_universal(text)
    nofmt = _extract_amounts_keyword_nofmt(text)
    all_amounts = relaxed + nofmt
    if all_amounts:
        picked = _pick_most_likely_amount(all_amounts)
        logger.debug(f"Universal fallback (relaxed:{relaxed}, nofmt:{nofmt}) → selected: {picked}")
        return str(picked)

    logger.warning("Could not find amount in receipt.")
    return "Not found"