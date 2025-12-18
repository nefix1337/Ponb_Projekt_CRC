def bytes_to_bitstr(b: bytes) -> str:
    return ''.join(f'{byte:08b}' for byte in b)

def text_to_bitstr(s: str) -> str:
    return bytes_to_bitstr(s.encode('utf-8'))

def xor(a: str, b: str) -> str:
    return ''.join('0' if x == y else '1' for x, y in zip(a, b))

def mod2div(dividend: str, divisor: str) -> str:
    pick = len(divisor)
    tmp = dividend[:pick]

    while pick < len(dividend):
        if tmp[0] == '1':
            tmp = xor(divisor, tmp) + dividend[pick]
        else:
            tmp = xor('0' * pick, tmp) + dividend[pick]
        tmp = tmp.lstrip('0') or '0'
        pick += 1

    if tmp[0] == '1' and len(tmp) >= len(divisor):
        tmp = xor(divisor, tmp)

    return tmp[-(len(divisor) - 1):].rjust(len(divisor) - 1, '0')

def create_frame(text: str, poly: str) -> str:
    """
    Nadawca:
    data_bits + crc_bits
    """
    data_bits = text_to_bitstr(text)
    padded = data_bits + '0' * (len(poly) - 1)
    crc_bits = mod2div(padded, poly)
    return data_bits + crc_bits

def check_frame(frame_bits: str, poly: str) -> bool:
    """
    Odbiorca:
    dzieli CAŁĄ ramkę (data + crc)
    """
    remainder = mod2div(frame_bits, poly)
    return set(remainder) == {'0'}
