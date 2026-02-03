import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime, pytz

# --- Configuration & Hyperparameters ---
SYMBOL = "EURJPY"
TIMEFRAME = mt5.TIMEFRAME_H1
MAGIC_NUMBER = 123456  
LOOKBACK = 100       
ENTRY_Z = 2.2        
EXIT_Z = 0.2         
STOP_Z = 4.0         
RISK_PER_TRADE = 0.01  
MAX_TRADE_DURATION_HOURS = 8
LOG_FILE = "live_trade_audit.csv"

# --- Initialization ---
if not mt5.initialize():
    print("❌ MT5 Initialization Failed")
    quit()

# --- 1. Robust State Recovery (The Filtered Truth) ---
def check_existing_position():
    """Strictly recovers state using Magic Number filtering."""
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions:
        # Aletheia Fix: Filter specifically for THIS bot's trades
        bot_positions = [p for p in positions if p.magic == MAGIC_NUMBER]
        if bot_positions:
            pos = bot_positions[0]
            direction = "LONG" if pos.type == mt5.POSITION_TYPE_BUY else "SHORT"
            print(f"🔄 Recovered: Existing {direction} at {pos.price_open}")
            return direction, pos.price_open, datetime.fromtimestamp(pos.time, tz=pytz.utc), pos.volume
    return None, None, None, 0.0

# --- 2. Precise Risk Calculation (The Mathematical Truth) ---
def get_lot_size(risk_amount, stop_pips):
    """Calculates lot size; skips trades if risk profile is violated."""
    symbol_info = mt5.symbol_info(SYMBOL)
    tick_value = symbol_info.trade_tick_value
    stop_pips = max(stop_pips, 10.0)
    
    lot = risk_amount / (stop_pips * tick_value * 100) 
    
    # Aletheia Fix: Prevent risk-skew on small accounts
    if lot < 0.01:
        print(f"⚠️ Risk too low for min lot size (Calc: {lot:.4f}). Skipping.")
        return 0.0
    
    return round(min(lot, 10.0), 2)

# --- 3. Persistent Auditing (The Historical Truth) ---
def log_trade(action, status, price, lots, pnl=0.0, reason=""):
    """Ensures every event is recorded in a permanent audit trail."""
    file_exists = os.path.isfile(LOG_FILE)
    log_entry = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Action": action, 
        "Status": status, 
        "Price": round(price, 3),
        "Lots": lots,
        "PnL_JPY": round(pnl, 2), # Aletheia Fix: Clarified Currency
        "Reason": reason
    }
    pd.DataFrame([log_entry]).to_csv(LOG_FILE, mode='a', index=False, header=not file_exists)
    print(f"📝 Logged: {action} {status} @ {price} | Reason: {reason}")

# --- Execution Engine ---
def send_market_order(action, lot, comment):
    tick = mt5.symbol_info_tick(SYMBOL)
    order_type = mt5.ORDER_TYPE_BUY if action == "LONG" else mt5.ORDER_TYPE_SELL
    price = tick.ask if action == "LONG" else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": float(lot),
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": comment,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    return result

def close_position(action, lot, comment):
    tick = mt5.symbol_info_tick(SYMBOL)
    order_type = mt5.ORDER_TYPE_SELL if action == "LONG" else mt5.ORDER_TYPE_BUY
    price = tick.bid if action == "LONG" else tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": float(lot),
        "type": order_type,
        "price": price,
        "magic": MAGIC_NUMBER,
        "comment": comment,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    return result

# --- Data Fetching ---
def get_indicators():
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 200)
    if rates is None: return None
    df = pd.DataFrame(rates)
    
    close_series = df['close'].tail(LOOKBACK)
    z_score = (df['close'].iloc[-1] - close_series.mean()) / close_series.std()
    
    df['tr'] = np.maximum(df['high'] - df['low'], 
                np.maximum(abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift())))
    atr = df['tr'].rolling(14).mean().iloc[-1]
    
    ma200 = df['close'].rolling(200).mean().iloc[-1]
    is_trending = abs(df['close'].iloc[-1] - ma200) / ma200 > 0.03
    
    return z_score, df['close'].iloc[-1], atr, is_trending

# --- Main Logic Loop ---
active_position, entry_price, trade_entry_time, trade_lots = check_existing_position()

print(f"🚀 Production System Online. Monitoring {SYMBOL}...")

try:
    while True:
        # Connection Stability Check
        if not mt5.terminal_info().connected:
            print("🔌 Connection lost. Reconnecting...")
            mt5.shutdown()
            time.sleep(5)
            mt5.initialize()
            continue

        data = get_indicators()
        if data is None: continue
        z, price, atr, is_trending = data
        
        # ENTRY
        if active_position is None:
            if abs(z) > ENTRY_Z and not is_trending:
                account = mt5.account_info()
                risk_cash = account.equity * RISK_PER_TRADE
                stop_pips = atr * 200 
                trade_lots = get_lot_size(risk_cash, stop_pips)
                
                if trade_lots >= 0.01:
                    direction = "SHORT" if z > 0 else "LONG"
                    res = send_market_order(direction, trade_lots, "Z-Entry")
                    if res.retcode == mt5.TRADE_RETCODE_DONE:
                        active_position, entry_price = direction, price
                        trade_entry_time = datetime.now(pytz.utc)
                        log_trade("ENTRY", active_position, price, trade_lots, reason=f"Z:{z:.2f}")

        # EXIT
        elif active_position:
            duration = (datetime.now(pytz.utc) - trade_entry_time).total_seconds() / 3600
            
            # Aletheia Fix: Exit when Z returns to Neutral Zone (-0.2 to +0.2)
            hit_target = abs(z) <= EXIT_Z
            
            hit_stop = abs(z) >= STOP_Z
            time_exit = duration > MAX_TRADE_DURATION_HOURS
            
            # Aletheia Fix: Prevent holding over the weekend gap
            current_time = datetime.now(pytz.utc)
            is_weekend_close = (current_time.weekday() == 4 and current_time.hour >= 20)

            if hit_target or hit_stop or time_exit or is_weekend_close:
                reason = "Target" if hit_target else ("Z-Stop" if hit_stop else ("Time" if time_exit else "Weekend"))
                res = close_position(active_position, trade_lots, reason)
                
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    # Calculate PnL (in JPY)
                    pnl = (entry_price - price if active_position == "SHORT" else price - entry_price) * trade_lots * 100000
                    log_trade("EXIT", active_position, price, trade_lots, pnl=pnl, reason=reason)
                    active_position = None

        time.sleep(60)

except KeyboardInterrupt:
    print("Stopping...")
finally:
    mt5.shutdown()
