# utils/binance_stream_enum.py
from enum import Enum

class BinanceStreamType(Enum):
    TRADE = "trade"
    AGG_TRADE = "aggTrade"
    KLINE = "kline"
    BOOK_TICKER = "bookTicker"
    DEPTH = "depth@100ms"
    MINI_TICKER = "miniTicker"
    TICKER = "ticker"
    OPEN_INTEREST = "openInterest"
    FUNDING_RATE = "fundingRate"
    TAKER_LONG_SHORT_RATIO = "takerLongShortRatio"
    MARK_PRICE = "markPrice@1s"
    LIQUIDATION_ORDER = "forceOrder"