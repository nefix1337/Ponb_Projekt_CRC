#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test CRC dla BIT_FLIP"""

from crc import create_frame, check_frame

# Test
message = "Hello"
poly = "1010"

# Utwórz ramkę
frame = create_frame(message, poly)
print(f"Oryginalna ramka: {frame}")
print(f"Długość ramki: {len(frame)} bitów")

# Sprawdź CRC oryginału
crc_ok = check_frame(frame, poly)
print(f"CRC CHECK (oryginal): {crc_ok} (powinno być True)")

# Zmień 1 bit
if frame:
    idx = len(frame) // 2  # Zmień bit w środku
    flipped = '1' if frame[idx] == '0' else '0'
    corrupted = frame[:idx] + flipped + frame[idx+1:]
    
    print(f"\nZmieniono bit na pozycji {idx}:")
    print(f"Przed: {frame[:idx]}[{frame[idx]}]{frame[idx+1:]}")
    print(f"Po:    {corrupted[:idx]}[{flipped}]{corrupted[idx+1:]}")
    
    # Sprawdź CRC uszkodzonej ramki
    crc_ok = check_frame(corrupted, poly)
    print(f"\nCRC CHECK (uszkodzona): {crc_ok} (powinno być False)")
    
    if crc_ok:
        print("\n❌ BŁĄD! CRC nie wykrył zmiany bitu!")
    else:
        print("\n✅ OK! CRC prawidłowo wykrył błąd!")
