import traceback
import sys


def test_fetch():
    print("=== Testing Derivatives Data Sources ===")

    # --- Test 1: vnstock with VCI (Current) ---
    try:
        from vnstock import Vnstock

        print("\n--- Testing vnstock (Source: VCI) ---")
        stock = Vnstock().stock(symbol="VN30F1M", source="VCI")
        hist = stock.quote.history(start="2025-01-20", end="2025-01-25", interval="1D")
        if hist is None or hist.empty:
            print("VCI: No data returned.")
        else:
            print(f"VCI: Data found! Latest:\n{hist.tail(2)}")
    except Exception as e:
        print(f"VCI Test Failed: {e}")

    # --- Test 2: vnstock with TCBS ---
    try:
        print("\n--- Testing vnstock (Source: TCBS) ---")
        # TCBS often handles derivatives better in some versions
        stock_tcbs = Vnstock().stock(symbol="VN30F1M", source="TCBS")
        hist_tcbs = stock_tcbs.quote.history(start="2025-01-20", end="2025-01-25", interval="1D")
        if hist_tcbs is None or hist_tcbs.empty:
            print("TCBS: No data returned.")
        else:
            print(f"TCBS: Data found! Latest:\n{hist_tcbs.tail(2)}")
    except Exception as e:
        print(f"TCBS Test Failed: {e}")

    # --- Test 3: vietfin (Alternative) ---
    try:
        print("\n--- Testing vietfin ---")
        import vietfin
        from vietfin import vf

        print(f"vietfin imported (version: {getattr(vietfin, '__version__', 'unknown')})")

        # Search for futures to confirm connectivity
        print("Searching for futures...")
        futures = vf.derivatives.futures.search()
        print(f"Futures contracts found: {len(futures) if futures else 0}")
        if futures:
            print(futures[:5])  # Show first 5

    except ImportError:
        print("vietfin not installed. Install with `pip install vietfin` to test.")
    except Exception as e:
        print(f"vietfin Test Failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    test_fetch()
