def bytes_to_bitstr(b: bytes) -> str:
    return ''.join(f'{byte:08b}' for byte in b)

def text_to_bitstr(s: str) -> str:
    return bytes_to_bitstr(s.encode('utf-8'))

def compute_crc_remainder(bits: str, poly: str) -> str:
    """Oblicza resztę CRC używając XOR."""
    degree = len(poly) - 1
    poly_int = int(poly, 2)
    
    # Konwertuj dane na liczbę i dołącz zera
    dividend = int(bits + "0" * degree, 2)
    
    # XOR z wielomianem
    for i in range(len(bits)):
        # Sprawdź bit na pozycji i (od lewej)
        if dividend & (1 << (len(bits) + degree - 1 - i)):
            dividend ^= (poly_int << (len(bits) + degree - 1 - i - degree))
    
    # Zwróć resztę jako bity
    return format(dividend, f'0{degree}b')

def create_frame(text: str, poly: str) -> str:
    """
    Nadawca:
    data_bits + crc_bits
    """
    data_bits = text_to_bitstr(text)
    crc_bits = compute_crc_remainder(data_bits, poly)
    return data_bits + crc_bits

def validate_crc(frame_with_checksum: str, polynomial: str) -> bool:
    """Sprawdza CRC używając XOR."""
    degree = len(polynomial) - 1
    poly_int = int(polynomial, 2)
    
    # Konwertuj całą ramkę na liczbę
    dividend = int(frame_with_checksum, 2)
    
    # XOR z wielomianem
    for i in range(len(frame_with_checksum) - degree):
        if dividend & (1 << (len(frame_with_checksum) - 1 - i)):
            dividend ^= (poly_int << (len(frame_with_checksum) - 1 - i - degree))
    
    # Sprawdź czy reszta to zera
    remainder = dividend & ((1 << degree) - 1)
    return remainder == 0

def check_frame(frame_bits: str, poly: str) -> bool:
    """
    Odbiorca:
    dzieli CAŁĄ ramkę (data + crc)
    Jeśli ramka jest OK, remainder powinien być ALL ZEROS
    """
    return validate_crc(frame_bits, poly)
