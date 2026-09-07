import pytest
from decimal import Decimal
from datetime import date
from backend.app.services.import_service import (
    parse_turkish_decimal,
    parse_flexible_date,
    guess_column_mapping,
    load_file_content
)

def test_parse_turkish_decimal():
    assert parse_turkish_decimal("1.250,50") == Decimal("1250.50")
    assert parse_turkish_decimal("1250,50 TL") == Decimal("1250.50")
    assert parse_turkish_decimal("750000") == Decimal("750000")
    assert parse_turkish_decimal("0,30") == Decimal("0.30")
    assert parse_turkish_decimal("geçersiz") is None
    assert parse_turkish_decimal(None) is None

def test_parse_flexible_date():
    assert parse_flexible_date("2026-09-04") == date(2026, 9, 4)
    assert parse_flexible_date("04.09.2026") == date(2026, 9, 4)
    assert parse_flexible_date("04/09/2026") == date(2026, 9, 4)
    assert parse_flexible_date("2026-09-04 14:30:00") == date(2026, 9, 4)
    assert parse_flexible_date("geçersiz-tarih") is None

def test_guess_column_mapping():
    headers = ["İşlem Tarihi", "Cari Adı", "Tutar (KDV Hariç)", "KDV Oranı", "Personel", "Bölüm"]
    mapping = guess_column_mapping(headers)
    assert mapping["date"] == "İşlem Tarihi"
    assert mapping["customer_name"] == "Cari Adı"
    assert mapping["amount_excl_vat"] == "Tutar (KDV Hariç)"
    assert mapping["vat_rate"] == "KDV Oranı"
    assert mapping["staff_name"] == "Personel"
    assert mapping["department_name"] == "Bölüm"

def test_load_csv_content():
    csv_content = (
        "Tarih;Müşteri;KDV Hariç;İşlem\n"
        "2026-09-01;Ahmet Yılmaz;10000;PPF Kaplama\n"
        "2026-09-02;Ayşe Kaya;5000;Seramik\n"
    ).encode("utf-8")
    
    headers, rows = load_file_content("test.csv", csv_content)
    assert headers == ["Tarih", "Müşteri", "KDV Hariç", "İşlem"]
    assert len(rows) == 2
    assert rows[0]["Müşteri"] == "Ahmet Yılmaz"
    assert rows[0]["KDV Hariç"] == "10000"

def test_mask_tax_id_length_adaptation():
    from backend.app.schemas.transaction import mask_tax_id

    # 10 haneli Vergi No (VKN): 6 yıldız + 4 hane = 10 karakter
    vkn_10 = "1234567890"
    masked_vkn = mask_tax_id(vkn_10)
    assert masked_vkn == "******7890"
    assert len(masked_vkn) == 10
    assert masked_vkn.count("*") == 6

    # 11 haneli TC Kimlik No (TCKN): 7 yıldız + 4 hane = 11 karakter
    tckn_11 = "12345678901"
    masked_tckn = mask_tax_id(tckn_11)
    assert masked_tckn == "*******8901"
    assert len(masked_tckn) == 11
    assert masked_tckn.count("*") == 7

    # Kısa numara veya boş durumlar
    assert mask_tax_id("1234") == "1234"
    assert mask_tax_id(None) is None

