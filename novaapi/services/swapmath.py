"""Swap quote math (stdlib only). Rate = price_from / price_to; fee is taken from the received amount."""
from decimal import ROUND_DOWN, Decimal


def compute_quote(price_from: Decimal, price_to: Decimal, amount_in: Decimal, fee_percent: Decimal, precision_out: int) -> dict:
    if price_from <= 0 or price_to <= 0 or amount_in <= 0:
        raise ValueError("invalid input")
    q = Decimal(1).scaleb(-precision_out)
    gross = (amount_in * price_from / price_to).quantize(q, rounding=ROUND_DOWN)
    fee = (gross * fee_percent / 100).quantize(q, rounding=ROUND_DOWN)
    return {"rate": price_from / price_to, "gross": gross, "fee": fee, "out": gross - fee}
