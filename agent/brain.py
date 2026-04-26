import json
import pandas as pd
import numpy as np

class TradingBrain:
    def __init__(self, api_key=None):
        pass

    def generate_hypothesis(self, market_data, context=""):
        try:
            data = json.loads(market_data) if isinstance(market_data, str) else market_data
            price = data['price']
            bias = data.get('bias', 'Neutral')
            features = data['features']
            
            fvg_data = features.get('fvg', {})
            ob_data = features.get('ob', {})
            
            # 1. BULLISH SETUPS
            if bias in ['Bullish', 'Neutral']:
                # Strategy: Enter on ANY recent Bullish ICT level (FVG or OB) within 5% range
                for idx, val in fvg_data.get('FVG', {}).items():
                    if val == 1.0: # Bullish FVG (Even if partially mitigated)
                        top = fvg_data['Top'][idx]
                        bot = fvg_data['Bottom'][idx]
                        if price >= bot * 0.95: # 5% Buffer
                            risk_dist = (top - bot) if (top > bot) else price * 0.005
                            return json.dumps({
                                "side": "Long",
                                "entry_price": price,
                                "stop_loss": bot - risk_dist * 0.05,
                                "take_profit": price + risk_dist * 2.0,
                                "reason": "Hyper-Aggressive Bullish FVG",
                                "confidence": 0.7
                            })

                for idx, val in ob_data.get('OB', {}).items():
                    if val == 1.0: # Bullish OB
                        top = ob_data['Top'][idx]
                        bot = ob_data['Bottom'][idx]
                        if price >= bot * 0.95:
                            risk_dist = (top - bot) if (top > bot) else price * 0.005
                            return json.dumps({
                                "side": "Long",
                                "entry_price": price,
                                "stop_loss": bot - risk_dist * 0.05,
                                "take_profit": price + risk_dist * 2.0,
                                "reason": "Hyper-Aggressive Bullish OB",
                                "confidence": 0.7
                            })

            # 2. BEARISH SETUPS
            if bias in ['Bearish', 'Neutral']:
                for idx, val in fvg_data.get('FVG', {}).items():
                    if val == -1.0: # Bearish FVG
                        top = fvg_data['Top'][idx]
                        bot = fvg_data['Bottom'][idx]
                        if price <= top * 1.05:
                            risk_dist = (top - bot) if (top > bot) else price * 0.005
                            return json.dumps({
                                "side": "Short",
                                "entry_price": price,
                                "stop_loss": top + risk_dist * 0.05,
                                "take_profit": price - risk_dist * 2.0,
                                "reason": "Hyper-Aggressive Bearish FVG",
                                "confidence": 0.7
                            })

                for idx, val in ob_data.get('OB', {}).items():
                    if val == -1.0: # Bearish OB
                        top = ob_data['Top'][idx]
                        bot = ob_data['Bottom'][idx]
                        if price <= top * 1.05:
                            risk_dist = (top - bot) if (top > bot) else price * 0.005
                            return json.dumps({
                                "side": "Short",
                                "entry_price": price,
                                "stop_loss": top + risk_dist * 0.05,
                                "take_profit": price - risk_dist * 2.0,
                                "reason": "Hyper-Aggressive Bearish OB",
                                "confidence": 0.7
                            })

        except Exception as e:
            pass # Keep it silent during high-speed backtest
            
        return json.dumps({"side": "None", "reason": "No setup"})

    def reflect_on_failure(self, trade_details, outcome):
        return f"Fail: {trade_details['id']} - {outcome}"
