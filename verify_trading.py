from vnstock import Trading
import traceback
import sys


def check_trading():
    print("Testing Trading.price_board for VN30F1M...")
    try:
        # Try KBS source as indicated in docs for price_board
        trading = Trading(source="KBS")
        print("Fetching price board...")
        df = trading.price_board(["VN30F1M"])

        if df is None:
            print("Result is None")
        elif df.empty:
            print("Result is Empty DataFrame")
        else:
            print("Result DataFrame:")
            print(df)
            print("Columns:", df.columns.tolist())
    except Exception as e:
        print(f"Trading.price_board failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    check_trading()
