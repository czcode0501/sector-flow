SECTORS = [
    ("XLK",  "Technology",             "科技"),
    ("XLF",  "Financials",             "金融"),
    ("XLV",  "Health Care",            "医疗"),
    ("XLY",  "Consumer Discretionary", "可选消费"),
    ("XLP",  "Consumer Staples",       "必选消费"),
    ("XLE",  "Energy",                 "能源"),
    ("XLI",  "Industrials",            "工业"),
    ("XLB",  "Materials",              "原材料"),
    ("XLU",  "Utilities",              "公用事业"),
    ("XLRE", "Real Estate",            "房地产"),
    ("XLC",  "Communication Services", "通讯"),
]

SECTOR_NAME = {code: (en, cn) for code, en, cn in SECTORS}

# Constituent lists are a manual snapshot. Removed after M&A: MRO (-> COP, 2024),
# HES (-> CVX, 2025), K (Kellanova -> Mars, 2025), IPG (-> OMC, 2025);
# PARA renamed to PSKY (Paramount Skydance, 2025). Re-check periodically — the
# sector page lists any ticker that returns no data.
SECTOR_STOCKS: dict[str, list[str]] = {
    "XLK": [
        "NVDA", "MSFT", "AAPL", "AVGO", "ORCL", "CRM", "CSCO", "IBM", "AMD", "ACN",
        "ADBE", "TXN", "INTU", "QCOM", "PLTR", "NOW", "ANET", "AMAT", "ADI", "MU",
        "LRCX", "KLAC", "INTC", "PANW", "SNPS", "CDNS", "WDAY", "FTNT", "GLW", "ROP",
    ],
    "XLF": [
        "BRK.B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "C",
        "BLK", "SPGI", "PGR", "SCHW", "CB", "MMC", "KKR", "ICE", "BX", "CME",
        "USB", "PNC", "AON", "TFC", "COF", "AIG", "MET", "TRV", "ALL", "AFL",
    ],
    "XLV": [
        "LLY", "JNJ", "ABBV", "MRK", "UNH", "TMO", "ABT", "ISRG", "PFE", "DHR",
        "AMGN", "BSX", "SYK", "GILD", "VRTX", "MDT", "ELV", "CVS", "REGN", "CI",
        "ZTS", "HCA", "BMY", "MCK", "EW", "BDX", "IDXX", "IQV", "HUM", "DXCM",
    ],
    "XLY": [
        "AMZN", "TSLA", "HD", "MCD", "LOW", "BKNG", "TJX", "SBUX", "NKE", "ORLY",
        "CMG", "MAR", "HLT", "ROST", "AZO", "DHI", "LEN", "GM", "F", "YUM",
        "RCL", "CCL", "GRMN", "EBAY", "LULU", "TSCO", "POOL", "DRI", "LKQ", "APTV",
    ],
    "XLP": [
        "COST", "WMT", "PG", "KO", "PM", "PEP", "MO", "MDLZ", "CL", "TGT",
        "KMB", "KDP", "KVUE", "GIS", "KR", "SYY", "STZ", "CHD", "HSY", "MKC",
        "ADM", "BG", "TSN", "CLX", "CAG", "HRL", "SJM", "MNST", "DG", "DLTR",
    ],
    "XLE": [
        "XOM", "CVX", "COP", "EOG", "MPC", "WMB", "PSX", "SLB", "OKE", "VLO",
        "KMI", "TRGP", "FANG", "EXE", "BKR", "OXY", "DVN", "HAL", "EQT", "APA",
        "TPL", "CTRA",
    ],
    "XLI": [
        "GE", "RTX", "HON", "UBER", "CAT", "BA", "UNP", "DE", "ETN", "LMT",
        "ADP", "WM", "EMR", "TT", "PH", "ITW", "GD", "NSC", "MMM", "CSX",
        "FDX", "CTAS", "NOC", "LHX", "PCAR", "JCI", "ODFL", "PAYX", "GWW", "URI",
    ],
    "XLB": [
        "LIN", "SHW", "ECL", "FCX", "APD", "NEM", "NUE", "DOW", "DD", "CTVA",
        "VMC", "MLM", "IFF", "PPG", "LYB", "STLD", "PKG", "BALL", "CF", "IP",
        "EMN", "MOS", "ALB", "AMCR", "AVY", "CE",
    ],
    "XLU": [
        "NEE", "SO", "DUK", "CEG", "VST", "AEP", "D", "EXC", "XEL", "SRE",
        "PCG", "PEG", "ED", "WEC", "EIX", "AWK", "DTE", "ETR", "ES", "PPL",
        "FE", "CMS", "AEE", "ATO", "CNP", "LNT", "NRG", "EVRG", "PNW",
    ],
    "XLRE": [
        "PLD", "AMT", "WELL", "EQIX", "SPG", "DLR", "PSA", "O", "CCI", "CBRE",
        "EXR", "VICI", "AVB", "EQR", "VTR", "IRM", "WY", "MAA", "ESS", "INVH",
        "ARE", "KIM", "HST", "DOC", "UDR", "BXP", "REG", "FRT",
    ],
    "XLC": [
        "META", "GOOGL", "GOOG", "NFLX", "DIS", "T", "VZ", "TMUS", "CMCSA", "CHTR",
        "EA", "TTWO", "WBD", "LYV", "OMC", "TKO", "MTCH", "PSKY", "NWS", "NWSA",
        "PINS", "FOX", "FOXA",
    ],
}
