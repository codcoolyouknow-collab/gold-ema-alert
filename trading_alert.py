import time
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime
import sys

# ⚙️ ตั้งค่า Telegram
TELEGRAM_TOKEN = "8817068302:AAHs7pl86xyzlVbfda164-_cmjz-46CTAH0"
CHAT_ID = "8640948132"

# ⚙️ เลือกแหล่งราคาทอง
#   "GC=F"   = Gold Futures (ค่าใกล้ XAUUSD แต่ไม่เท่ากันเป๊ะ)
#   "XAUUSD=X" = ทองสปอต (ใกล้ TradingView มากกว่า) — ลองตัวนี้ถ้าอยากตรง TradingView
SYMBOL = "GC=F"

# 📊 เก็บเวลาแท่งเทียนที่เคยเตือนไปแล้ว เพื่อไม่ให้เตือนซ้ำแท่งเดิม
last_alert_time = {"30m": None, "15m": None}


def send_telegram(message: str):
    """ส่งข้อความไป Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(
            url,
            json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"},
            timeout=10,
        )
        print(f"✅ ส่ง Telegram: HTTP {resp.status_code} | {resp.text[:80]}", flush=True)
    except Exception as e:
        print(f"❌ Telegram Error: {e}", flush=True)


def check_ema_signal_tf(interval: str, tf_name: str):
    """ตรวจสัญญาณ EMA12 ตัด EMA26 โดยใช้แท่งเทียนที่ 'ปิดแล้ว' เท่านั้น"""
    try:
        data = yf.download(SYMBOL, interval=interval, period="5d", progress=False)

        if data is None or len(data) < 30:
            print(f"⚠️ [{tf_name}] ข้อมูลไม่พอ", flush=True)
            return

        # yfinance เวอร์ชันใหม่คืนคอลัมน์แบบ MultiIndex → ทำให้เหลือชั้นเดียว
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # คำนวณ EMA
        data["EMA12"] = data["Close"].ewm(span=12, adjust=False).mean()
        data["EMA26"] = data["Close"].ewm(span=26, adjust=False).mean()

        # ใช้แท่งที่ปิดแล้ว: -2 = แท่งล่าสุดที่ปิด, -3 = แท่งก่อนหน้า
        # (-1 คือแท่งที่กำลังก่อตัว ค่ายังแกว่ง จึงไม่ใช้)
        ema12_now = float(data["EMA12"].iloc[-2])
        ema26_now = float(data["EMA26"].iloc[-2])
        ema12_prev = float(data["EMA12"].iloc[-3])
        ema26_prev = float(data["EMA26"].iloc[-3])
        price = float(data["Close"].iloc[-2])
        candle_time = str(data.index[-2])

        diff = ema12_now - ema26_now
        pos = "EMA12 เหนือ EMA26" if diff > 0 else "EMA12 ใต้ EMA26"
        print(
            f"⏳ [{tf_name}] {pos} | EMA12: ${ema12_now:.2f} | EMA26: ${ema26_now:.2f} | ห่าง: {diff:+.2f}",
            flush=True,
        )

        crossed_up = ema12_prev <= ema26_prev and ema12_now > ema26_now
        crossed_down = ema12_prev >= ema26_prev and ema12_now < ema26_now

        # กันเตือนซ้ำแท่งเดิม
        if (crossed_up or crossed_down) and last_alert_time[interval] == candle_time:
            return

        if crossed_up:
            emoji = "🟢" if interval == "30m" else "🟩"
            msg = (
                f"{emoji} *GOLD BUY SIGNAL* {emoji}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 *Signal:* EMA12 ตัดขึ้น EMA26\n"
                f"💰 *Price:* ${price:.2f}\n"
                f"📈 *EMA12:* ${ema12_now:.2f}\n"
                f"📉 *EMA26:* ${ema26_now:.2f}\n"
                f"⏱ *Timeframe:* {tf_name}\n"
                f"🕐 *เวลา:* {datetime.now().strftime('%H:%M:%S')}\n"
                f"━━━━━━━━━━━━━━━━━━"
            )
            send_telegram(msg)
            print(f"🟢 [{tf_name}] BUY SIGNAL!", flush=True)
            last_alert_time[interval] = candle_time

        elif crossed_down:
            emoji = "🔴" if interval == "30m" else "🟥"
            msg = (
                f"{emoji} *GOLD SELL SIGNAL* {emoji}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 *Signal:* EMA12 ตัดลง EMA26\n"
                f"💰 *Price:* ${price:.2f}\n"
                f"📈 *EMA12:* ${ema12_now:.2f}\n"
                f"📉 *EMA26:* ${ema26_now:.2f}\n"
                f"⏱ *Timeframe:* {tf_name}\n"
                f"🕐 *เวลา:* {datetime.now().strftime('%H:%M:%S')}\n"
                f"━━━━━━━━━━━━━━━━━━"
            )
            send_telegram(msg)
            print(f"🔴 [{tf_name}] SELL SIGNAL!", flush=True)
            last_alert_time[interval] = candle_time

    except Exception as e:
        print(f"❌ [{tf_name}] Error: {e}", flush=True)


def check_ema_signal():
    print(f"⏰ ตรวจสัญญาณ... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    check_ema_signal_tf("30m", "30 นาที")
    check_ema_signal_tf("15m", "15 นาที")


if __name__ == "__main__":
    print("🚀 Gold EMA12/26 Monitor Started!", flush=True)
    print(f"⏳ ตรวจทุก 1 นาที | แหล่งราคา: {SYMBOL}", flush=True)

    # ✅ ส่งข้อความยืนยันตอนเริ่ม เพื่อพิสูจน์ว่า Telegram ต่อติด
    send_telegram(
        f"✅ *Gold EMA Bot เริ่มทำงานแล้ว*\n"
        f"📡 แหล่งราคา: {SYMBOL}\n"
        f"⏱ TF: 15 นาที + 30 นาที\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    while True:
        try:
            check_ema_signal()
            time.sleep(60)
        except KeyboardInterrupt:
            print("\n⛔ หยุดการทำงาน", flush=True)
            break
        except Exception as e:
            print(f"❌ Error: {e}", flush=True)
            time.sleep(60)
