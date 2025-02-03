import requests
import pandas as pd
import ta
import time

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = "Your Telegram Token"  # Replace with your bot's token
TELEGRAM_CHAT_ID = "Telegram ID"  # Replace with your Telegram ID

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
    params = {"vs_currency": "usd", "days": "7"}
    
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
    df['rsi'] = ta.momentum.RSIIndicator(df['price'], window=14).rsi()
    df['ema9'] = ta.trend.EMAIndicator(df['price'], window=9).ema_indicator()
    df['ema21'] = ta.trend.EMAIndicator(df['price'], window=21).ema_indicator()
    
    macd = ta.trend.MACD(df['price'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()

    return df

# Function to generate buy/sell signals using RSI < 30 for buy, RSI > 70 for sell
def trading_signal(df):
    df['signal'] = None

    df.loc[(df['rsi'] < 30) & (df['macd'] > df['macd_signal']), 'signal'] = 'buy'  # Buy when RSI < 30 and MACD crosses above Signal
    df.loc[(df['rsi'] > 70) & (df['macd'] < df['macd_signal']), 'signal'] = 'sell'  # Sell when RSI > 70 and MACD crosses below Signal

    return df

# Main loop to report every 5 minutes
last_signal = None  # Track last signal to avoid duplicate alerts

while True:
    df = get_doge_historical()
    if df.empty:
        continue
    
    df = calculate_indicators(df)
    df = trading_signal(df)

    latest = df.iloc[-1]  # Get the latest row
    current_signal = latest['signal']

    # Format timestamp to display date and time in message
    timestamp = latest['timestamp'].strftime('%Y-%m-%d %H:%M:%S')  # Format timestamp as 'YYYY-MM-DD HH:MM:SS'

    print(f"Checked price: ${latest['price']:.4f} | RSI: {latest['rsi']:.2f} | MACD: {latest['macd']:.4f} | Signal: {current_signal}")  # More detailed logging

    # Send price update every 5 minutes
    price_message = f"💰 Dogecoin Update:\n📅 {timestamp}\n💲 Price: ${latest['price']:.4f}\n📈 RSI: {latest['rsi']:.2f}\n📊 MACD: {latest['macd']:.4f}"
    send_telegram_message(price_message)
    
    # Send signal alert if new buy/sell signal appears
    if current_signal and current_signal != last_signal:
        signal_message = f"🚀 DogeBot Alert: {current_signal.capitalize()} Signal!\n📅 {timestamp}\n💲 Price: ${latest['price']:.4f}\n📉 RSI: {latest['rsi']:.2f}\n📊 MACD: {latest['macd']:.4f}"
        send_telegram_message(signal_message)
        last_signal = current_signal  # Update last signal

    time.sleep(300)  # Wait 5 minutes before checking again

