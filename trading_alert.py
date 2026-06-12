import time
import requests
import yfinance as yf
from datetime import datetime
import sys

# Force flush stdout
sys.stdout = sys.stdout

# ⚙️ ตั้งค่า Telegram
TELEGRAM_TOKEN = "8817068302:AAHs7pl86xyzlVbfda164-_cmjz-46CTAH0"
CHAT_ID = "8640948132"

# 📊 ตัวแปรเก็บสถานะเพื่อไม่ให้เตือนซ้ำ
last_signal_30m = None
last_signal_15m = None

def send_telegram(message: str):
    """ส่งข้อความไป Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
        print(f"✅ ส่งข้อความแล้ว: {resp.status_code}", flush=True)
    except Exception as e:
        print(f"❌ Telegram Error: {e}", flush=True)

def check_ema_signal_tf(interval: str, tf_name: str):
    """ตรวจสัญญาณ EMA12 ตัด EMA26"""
    global last_signal_30m, last_signal_15m

    try:
        # ดึงข้อมูลทองคำ (GC=F = XAUUSD Futures)
        data = yf.download("GC=F", interval=interval, period="5d", progress=False)

        if len(data) < 26:
            print(f"⚠️ [{tf_name}] ข้อมูลไม่พอ")
            return

        # คำนวณ EMA
        data['EMA12'] = data['Close'].ewm(span=12, adjust=False).mean()
        data['EMA26'] = data['Close'].ewm(span=26, adjust=False).mean()

        # ค่าปัจจุบันและค่าก่อนหน้า
        current_ema12 = data['EMA12'].iloc[-1]
        current_ema26 = data['EMA26'].iloc[-1]
        prev_ema12 = data['EMA12'].iloc[-2]
        prev_ema26 = data['EMA26'].iloc[-2]
        price = data['Close'].iloc[-1]

        # 🟢 EMA12 ตัดขึ้น EMA26 (สัญญาณซื้อ)
        if prev_ema12 <= prev_ema26 and current_ema12 > current_ema26:
            current_signal = "BUY" if interval == "30m" else last_signal_15m
            if (interval == "30m" and last_signal_30m != "BUY") or (interval == "15m" and last_signal_15m != "BUY"):
                emoji = "🟢" if interval == "30m" else "🟩"
                msg = f"""
{emoji} *GOLD BUY SIGNAL* {emoji}
━━━━━━━━━━━━━━━━━━
📊 *Signal:* EMA12 ตัดขึ้น EMA26
💰 *Price:* ${price:.2f}
📈 *EMA12:* ${current_ema12:.2f}
📉 *EMA26:* ${current_ema26:.2f}
⏱ *Timeframe:* {tf_name}
🕐 *เวลา:* {datetime.now().strftime('%H:%M:%S')}
━━━━━━━━━━━━━━━━━━
"""
                send_telegram(msg)
                print(f"✅ [{tf_name}] BUY SIGNAL ส่งแล้ว", flush=True)
                if interval == "30m":
                    last_signal_30m = "BUY"
                else:
                    last_signal_15m = "BUY"

        # 🔴 EMA12 ตัดลง EMA26 (สัญญาณขาย)
        elif prev_ema12 >= prev_ema26 and current_ema12 < current_ema26:
            if (interval == "30m" and last_signal_30m != "SELL") or (interval == "15m" and last_signal_15m != "SELL"):
                emoji = "🔴" if interval == "30m" else "🟥"
                msg = f"""
{emoji} *GOLD SELL SIGNAL* {emoji}
━━━━━━━━━━━━━━━━━━
📊 *Signal:* EMA12 ตัดลง EMA26
💰 *Price:* ${price:.2f}
📈 *EMA12:* ${current_ema12:.2f}
📉 *EMA26:* ${current_ema26:.2f}
⏱ *Timeframe:* {tf_name}
🕐 *เวลา:* {datetime.now().strftime('%H:%M:%S')}
━━━━━━━━━━━━━━━━━━
"""
                send_telegram(msg)
                print(f"✅ [{tf_name}] SELL SIGNAL ส่งแล้ว", flush=True)
                if interval == "30m":
                    last_signal_30m = "SELL"
                else:
                    last_signal_15m = "SELL"

        else:
            print(f"⏳ [{tf_name}] ยังไม่มีสัญญาณ | EMA12: ${current_ema12:.2f} | EMA26: ${current_ema26:.2f}")

    except Exception as e:
        print(f"❌ [{tf_name}] Error: {e}")

def check_ema_signal():
    """ตรวจสัญญาณ TF 30m และ 15m"""
    print(f"⏰ ตรวจสัญญาณ... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    check_ema_signal_tf("30m", "30 นาที")
    check_ema_signal_tf("15m", "15 นาที")

if __name__ == "__main__":
    print("🚀 Gold EMA12/26 Monitor Started!", flush=True)
    print("⏳ ตรวจสัญญาณทุก 1 นาที...", flush=True)

    while True:
        try:
            check_ema_signal()
            sys.stdout.flush()
            time.sleep(60)
        except KeyboardInterrupt:
            print("\n⛔ หยุดการทำงาน", flush=True)
            break
        except Exception as e:
            print(f"❌ Error: {e}", flush=True)
            time.sleep(60)
