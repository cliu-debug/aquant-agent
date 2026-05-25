"""
AStockAgents Web界面

基于FastAPI + Vue.js的交互式分析界面
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import json
import os

# 创建FastAPI应用
app = FastAPI(
    title="AStockAgents",
    description="多智能体协同股票分析系统",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 数据模型 ====================

class AnalysisRequest(BaseModel):
    """分析请求"""
    stock_code: str
    stock_name: Optional[str] = None
    days: Optional[int] = 120


class AnalysisResponse(BaseModel):
    """分析响应"""
    stock_code: str
    stock_name: str
    technical_analysis: Dict[str, Any]
    fundamental_analysis: Dict[str, Any]
    sentiment_analysis: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    final_decision: Dict[str, Any]
    timestamp: str


# ==================== 模拟数据生成 ====================

def generate_mock_data(stock_code: str, stock_name: str, days: int = 120):
    """生成模拟股票数据"""
    import numpy as np
    np.random.seed(hash(stock_code) % 2**32)
    
    # 基础价格设置
    if "茅台" in stock_name:
        base_price, volatility = 1800.0, 30.0
    elif "五粮液" in stock_name:
        base_price, volatility = 150.0, 5.0
    elif "银行" in stock_name:
        base_price, volatility = 10.0, 0.5
    else:
        base_price, volatility = 50.0, 3.0
    
    prices = []
    trend_factor = np.random.choice([-1, 1]) * np.random.uniform(0.1, 0.3)
    
    for i in range(days):
        trend = i * trend_factor
        cycle = np.sin(i * 0.1) * volatility
        noise = np.random.normal(0, volatility * 0.3)
        close = base_price + trend + cycle + noise
        
        prices.append({
            "date": (datetime(2024, 1, 1) + __import__('datetime').timedelta(days=i)).strftime('%Y-%m-%d'),
            "open": round(close + np.random.normal(0, volatility * 0.1), 2),
            "high": round(close + abs(np.random.normal(0, volatility * 0.2)), 2),
            "low": round(close - abs(np.random.normal(0, volatility * 0.2)), 2),
            "close": round(close, 2),
            "volume": int(1000000 + np.random.exponential(500000))
        })
    
    return prices


def analyze_stock(stock_code: str, stock_name: str, days: int = 120) -> Dict[str, Any]:
    """执行股票分析"""
    from datetime import datetime, timedelta
    import numpy as np
    
    # 生成价格数据
    prices = generate_mock_data(stock_code, stock_name, days)
    
    # 计算技术指标
    closes = [p['close'] for p in prices]
    volumes = [p['volume'] for p in prices]
    
    # 简单移动平均
    ma5 = sum(closes[-5:]) / 5
    ma10 = sum(closes[-10:]) / 10
    ma20 = sum(closes[-20:]) / 20
    
    # RSI (简化)
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas[-14:]]
    losses = [-d if d < 0 else 0 for d in deltas[-14:]]
    avg_gain = sum(gains) / 14
    avg_loss = sum(losses) / 14
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    
    # MACD (简化)
    ema12 = sum(closes[-12:]) / 12
    ema26 = sum(closes[-26:]) / 26
    dif = ema12 - ema26
    
    # 趋势判断
    if ma5 > ma10 > ma20:
        trend = "上升趋势"
        trend_strength = 70
    elif ma5 < ma10 < ma20:
        trend = "下降趋势"
        trend_strength = 30
    else:
        trend = "震荡整理"
        trend_strength = 50
    
    # 信号生成
    score = 50
    if rsi < 30:
        score += 15
    elif rsi > 70:
        score -= 15
    
    if dif > 0:
        score += 10
    else:
        score -= 10
    
    if trend == "上升趋势":
        score += 10
    elif trend == "下降趋势":
        score -= 10
    
    # 确定信号
    if score >= 65:
        signal = "强烈买入"
        action = "STRONG_BUY"
    elif score >= 55:
        signal = "买入"
        action = "BUY"
    elif score >= 45:
        signal = "持有"
        action = "HOLD"
    elif score >= 35:
        signal = "卖出"
        action = "SELL"
    else:
        signal = "强烈卖出"
        action = "STRONG_SELL"
    
    # 构建结果
    current_price = closes[-1]
    prev_price = closes[-2]
    change_pct = (current_price - prev_price) / prev_price * 100
    
    return {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "current_price": round(current_price, 2),
        "change_pct": round(change_pct, 2),
        "technical_analysis": {
            "trend": trend,
            "trend_strength": trend_strength,
            "signal": signal,
            "confidence": abs(score - 50) * 2,
            "indicators": {
                "ma5": round(ma5, 2),
                "ma10": round(ma10, 2),
                "ma20": round(ma20, 2),
                "rsi": round(rsi, 2),
                "macd_dif": round(dif, 3)
            },
            "patterns": ["均线多头排列"] if ma5 > ma10 > ma20 else ["均线空头排列"] if ma5 < ma10 < ma20 else []
        },
        "fundamental_analysis": {
            "valuation": "合理",
            "profitability": "良好",
            "growth": "稳定",
            "pe_ttm": 35.0 if "茅台" in stock_name else 8.0,
            "pb": 10.0 if "茅台" in stock_name else 0.6
        },
        "sentiment_analysis": {
            "score": 55,
            "state": "偏乐观",
            "hot_topics": ["白酒板块", "消费复苏"]
        },
        "risk_assessment": {
            "overall_risk": "中等",
            "market_risk": "中等",
            "liquidity_risk": "低",
            "suggestions": ["建议分批建仓", "设置止损位"]
        },
        "final_decision": {
            "score": round(score, 1),
            "signal": signal,
            "action": action,
            "recommendation": f"建议{signal}" if signal != "持有" else "建议观望"
        },
        "price_data": prices[-60:],  # 最近60天数据
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


# ==================== API路由 ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    """返回主页"""
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>AStockAgents</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>AStockAgents Web界面</h1>
            <p>请访问 <a href="/api/docs">/api/docs</a> 查看API文档</p>
            <p>或使用 <a href="/analyze?stock_code=600519.SH&stock_name=贵州茅台">/analyze</a> 进行分析</p>
        </body>
        </html>
        """


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/analyze")
async def analyze_get(stock_code: str, stock_name: Optional[str] = None, days: int = 120):
    """GET方式分析股票"""
    if not stock_name:
        stock_name = stock_code
    
    try:
        result = analyze_stock(stock_code, stock_name, days)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def analyze_post(request: AnalysisRequest):
    """POST方式分析股票"""
    stock_name = request.stock_name or request.stock_code
    
    try:
        result = analyze_stock(request.stock_code, stock_name, request.days)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/popular")
async def get_popular_stocks():
    """获取热门股票列表"""
    return {
        "stocks": [
            {"code": "600519.SH", "name": "贵州茅台", "industry": "白酒"},
            {"code": "000858.SZ", "name": "五粮液", "industry": "白酒"},
            {"code": "000001.SZ", "name": "平安银行", "industry": "银行"},
            {"code": "600036.SH", "name": "招商银行", "industry": "银行"},
            {"code": "000333.SZ", "name": "美的集团", "industry": "家电"},
            {"code": "600276.SH", "name": "恒瑞医药", "industry": "医药"},
        ]
    }


@app.get("/api/compare")
async def compare_stocks(stock_codes: str):
    """对比多只股票"""
    codes = stock_codes.split(",")
    results = []
    
    stock_names = {
        "600519.SH": "贵州茅台",
        "000858.SZ": "五粮液",
        "000001.SZ": "平安银行",
        "600036.SH": "招商银行",
    }
    
    for code in codes[:5]:  # 最多5只
        name = stock_names.get(code, code)
        result = analyze_stock(code, name, 60)
        results.append({
            "stock_code": code,
            "stock_name": name,
            "current_price": result["current_price"],
            "change_pct": result["change_pct"],
            "signal": result["final_decision"]["signal"],
            "score": result["final_decision"]["score"]
        })
    
    return {"results": results}


# ==================== 启动函数 ====================

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """启动Web服务器"""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
