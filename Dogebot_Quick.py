
"""

    This bot is a clone of Dogebot.py, but uses 7 day RSI window instead of a 14 day window. 
    Also reduces MACD fast period to 5 instead of 12 and MACD slow period to 13 instead of 26.

    This is because I wanted a bot that is more sensitive to market movement and to focus on quick trades. 


"""


import requests
import pandas as pd
import ta
import time

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Replace with your bot's token
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"  # Replace with your Telegram ID

# Function to send Telegram messages
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.get(url, params=params)

# Function to get current DOGE price
def get_doge_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=dogecoin&vs_currencies=usd"
    response = requests.get(url)
    data = response.json()
    
    if 'dogecoin' in data:
        return float(data['dogecoin']['usd'])
    else:
        print("Error: 'dogecoin' not found in the API response")
        return None

# Function to get historical DOGE data
def get_doge_historical():
    url = "https://api.coingecko.com/api/v3/coins/dogecoin/market_chart"
    params = {"vs_currency": "usd", "days": "1", "interval": "minute"}  # Fetching minute data for faster movements
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return pd.DataFrame()
    
    data = response.json()
    
    if "prices" not in data:
        print("Unexpected response:", data)
        return pd.DataFrame()
    
    prices = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    prices["timestamp"] = pd.to_datetime(prices["timestamp"], unit="ms")
    
    return prices

# Function to calculate technical indicators
def calculate_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['price'], window=7).rsi()  # Faster RSI
    df['ema9'] = ta.trend.EMAIndicator(df['price'], window=5).ema_indicator()  # Faster EMA
    df['ema21'] = ta.trend.EMAIndicator(df['price'], window=10).ema_indicator()  # Adjusted EMA
    
    macd = ta.trend.MACD(df['price'], window_slow=13, window_fast=5)  # Faster MACD settings
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()

    return df

# Function to generate buy/sell signals for smaller price movements
def trading_signal(df):
    df['signal'] = None

    # Buy if RSI < 40 and MACD crosses above Signal
    df.loc[(df['rsi'] < 40) & (df['macd'] > df['macd_signal']), 'signal'] = 'buy'
    
    # Sell if RSI > 60 and MACD crosses below Signal
    df.loc[(df['rsi'] > 60) & (df['macd'] < df['macd_signal']), 'signal'] = 'sell'

    return df

# Monitor price changes
last_price = None  # Store last price
price_change_threshold = 0.005  # 0.5% price movement alert

last_signal = None  # Track last signal to avoid duplicate alerts

while True:
    df = get_doge_historical()
    if df.empty:
        continue
    
    df = calculate_indicators(df)
    df = trading_signal(df)

    latest = df.iloc[-1]  # Get the latest row
    current_signal = latest['signal']
    current_price = latest['price']

    # Format timestamp to display date and time in message
    timestamp = latest['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

    print(f"Checked price: ${latest['price']:.4f} | RSI: {latest['rsi']:.2f} | MACD: {latest['macd']:.4f} | Signal: {current_signal}")

    # Send price update if there is a movement greater than the threshold
    if last_price and abs((current_price - last_price) / last_price) >= price_change_threshold:
        price_message = f"📉 Price Movement Alert:\n📅 {timestamp}\n💲 New Price: ${current_price:.4f}\n📊 Change: {((current_price - last_price) / last_price) * 100:.2f}%"
        send_telegram_message(price_message)

    last_price = current_price  # Update last known price
    
    # Send signal alert if new buy/sell signal appears
    if current_signal and current_signal != last_signal:
        signal_message = f"🚀 DogeBot Alert: {current_signal.capitalize()} Signal!\n📅 {timestamp}\n💲 Price: ${latest['price']:.4f}\n📉 RSI: {latest['rsi']:.2f}\n📊 MACD: {latest['macd']:.4f}"
        send_telegram_message(signal_message)
        last_signal = current_signal  # Update last signal

    time.sleep(60)  # Check every 1 minute
