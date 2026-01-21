def bytes_to_bitstr(b: bytes) -> str:
    return ''.join(f'{byte:08b}' for byte in b)

def text_to_bitstr(s: str) -> str:
    return bytes_to_bitstr(s.encode('utf-8'))

def crc_calculate(data: str, polynomial: str) -> str:
    """Oblicza CRC dla danych binarnych."""
    r = len(polynomial) - 1
    padded = list(data + "0" * r)

    for i in range(len(data)):
        if padded[i] == "1":
            for j in range(len(polynomial)):
                padded[i + j] = str(
                    int(padded[i + j]) ^ int(polynomial[j])
                )

    return "".join(padded[-r:])

def create_frame(text: str, poly: str) -> str:
    """
    Nadawca:
    data_bits + crc_bits
    """
    data_bits = text_to_bitstr(text)
    crc_bits = crc_calculate(data_bits, poly)
    return data_bits + crc_bits

def crc_verify(data_with_crc: str, polynomial: str) -> bool:
    """Sprawdza poprawność danych z CRC."""
    r = len(polynomial) - 1
    padded = list(data_with_crc)

    for i in range(len(data_with_crc) - r):
        if padded[i] == "1":
            for j in range(len(polynomial)):
                padded[i + j] = str(
                    int(padded[i + j]) ^ int(polynomial[j])
                )

    return all(b == "0" for b in padded[-r:])

def check_frame(frame_bits: str, poly: str) -> bool:
    """
    Odbiorca:
    dzieli CAŁĄ ramkę (data + crc)
    Jeśli ramka jest OK, remainder powinien być ALL ZEROS
    """
    return crc_verify(frame_bits, poly)
