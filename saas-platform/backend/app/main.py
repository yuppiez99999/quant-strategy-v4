"""QuantMatrix SaaS - FastAPI Backend Server

Wraps the quantitative strategy modules (康波周期, 十五五规划, 社保基金ETF追踪, AI Hedge Fund)
into a production REST API for the SaaS platform.
"""
import os
import sys
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="QuantMatrix SaaS API",
    description="智能量化策略平台 - REST API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS - allow frontend dev server and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Health Check
# ============================================================
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "QuantMatrix SaaS API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# Auth Endpoints
# ============================================================
@app.post("/api/auth/register")
async def register(user_data: dict):
    """Register a new user (mock implementation)"""
    return {
        "access_token": "mock_token_xxx",
        "token_type": "bearer",
        "user": {
            "id": "1",
            "email": user_data.get("email"),
            "name": user_data.get("name"),
            "company": user_data.get("company"),
            "plan": "free",
        }
    }


@app.post("/api/auth/login")
async def login(credentials: dict):
    """Login user (mock implementation)"""
    return {
        "access_token": "mock_token_xxx",
        "token_type": "bearer",
        "user": {
            "id": "1",
            "email": credentials.get("email"),
            "name": "Demo User",
            "company": "演示公司",
            "plan": "pro",
        }
    }


# ============================================================
# Portfolio Endpoints
# ============================================================
@app.get("/api/portfolio/assets")
async def get_portfolio_assets():
    """Get portfolio holdings"""
    from .. import quant_bridge
    return quant_bridge.get_portfolio_assets()


@app.get("/api/portfolio/summary")
async def get_portfolio_summary():
    """Get portfolio summary metrics"""
    return {
        "total_value": 1017000,
        "total_change": 17000,
        "total_change_percent": 1.70,
        "daily_pl": 12400,
        "total_return": 12.8,
        "sharpe_ratio": 1.86,
        "max_drawdown": -8.2,
        "volatility": 14.5,
    }


@app.get("/api/portfolio/risk")
async def get_risk_metrics():
    """Get risk metrics"""
    return {
        "var95": 2.35,
        "var99": 4.12,
        "cvar": 3.28,
        "beta": 0.92,
        "correlation": 0.85,
        "stop_loss_triggers": 0,
    }


# ============================================================
# Market Analysis Endpoints
# ============================================================
@app.get("/api/analysis/kondratiev")
async def get_kondratiev_signal():
    """Get Konratiev cycle analysis"""
    return {
        "phase": "recovery",
        "phase_label": "复苏期",
        "confidence": 78,
        "description": "第六轮康波周期（AI/算力驱动）处于复苏向繁荣过渡阶段...",
        "sector_allocation": [
            {"sector": "高端制造(含算力)", "recommended_weight": 45, "current_weight": 44.7, "signal": "overweight"},
            {"sector": "顺周期", "recommended_weight": 20, "current_weight": 20.4, "signal": "neutral"},
            {"sector": "资源", "recommended_weight": 20, "current_weight": 19.8, "signal": "neutral"},
            {"sector": "防御", "recommended_weight": 15, "current_weight": 15.8, "signal": "underweight"},
        ],
        "commodity_signal": "bullish",
    }


@app.get("/api/analysis/five-year-plan")
async def get_five_year_plan():
    """Get Five Year Plan alignment analysis"""
    return [
        {"direction": "新质生产力", "weight": 25, "score": 92, "holding_count": 4, "description": "算力基础设施、半导体设备等核心标的..."},
        {"direction": "制造强国", "weight": 20, "score": 85, "holding_count": 3, "description": "高端装备、精密制造龙头..."},
        {"direction": "数字中国", "weight": 15, "score": 88, "holding_count": 3, "description": "AI芯片、数据中心相关标的..."},
        {"direction": "绿色低碳", "weight": 12, "score": 72, "holding_count": 2, "description": "新能源电池龙头..."},
        {"direction": "健康中国", "weight": 10, "score": 78, "holding_count": 3, "description": "创新药、CXO龙头..."},
        {"direction": "安全发展", "weight": 10, "score": 65, "holding_count": 1, "description": "半导体自主可控..."},
        {"direction": "乡村振兴", "weight": 8, "score": 40, "holding_count": 0, "description": "暂无直接匹配标的"},
    ]


@app.get("/api/analysis/macro")
async def get_macro_data():
    """Get macroeconomic indicators"""
    return {
        "pmi": 50.8, "pmi_change": 0.3,
        "cpi": 0.2, "cpi_change": -0.1,
        "gdp": 5.2, "gdp_change": 0.0,
        "m2": 8.3, "m2_change": -0.2,
        "social_finance": 2.06, "social_finance_change": 0.15,
    }


# ============================================================
# ETF Flow Endpoints
# ============================================================
@app.get("/api/etf/flows")
async def get_etf_flows():
    """Get ETF fund flow data"""
    # Returns the same mock data structure as the frontend
    from .. import quant_bridge
    return quant_bridge.get_etf_flow_data()


# ============================================================
# AI Analysis Endpoints
# ============================================================
@app.get("/api/ai/analysis/{ticker}")
async def get_ai_analysis(ticker: str):
    """Get AI Hedge Fund analysis for a specific ticker"""
    return {
        "ticker": ticker,
        "ticker_name": "中际旭创",
        "overall_score": 8.5,
        "signals": [
            {"analyst": "巴菲特", "action": "buy", "confidence": 75, "reasoning": "光模块龙头地位稳固..."},
            {"analyst": "彼得林奇", "action": "buy", "confidence": 85, "reasoning": "PEG比率极具吸引力..."},
            {"analyst": "德鲁肯米勒", "action": "buy", "confidence": 90, "reasoning": "AI基础设施建设周期确定性最强标的..."},
        ],
        "summary": "中际旭创作为光模块赛道绝对龙头...",
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# Reports Endpoints
# ============================================================
@app.get("/api/reports")
async def get_reports(limit: int = 10):
    """Get historical reports"""
    return [
        {"id": "1", "title": "量化策略日报 - 2026年6月28日", "type": "daily", "date": "2026-06-28", "summary": "组合总收益+1.70%", "url": "#"},
        {"id": "2", "title": "量化策略周报 - 第26周", "type": "weekly", "date": "2026-06-27", "summary": "本周组合净值+3.2%", "url": "#"},
        {"id": "3", "title": "月度宏观分析报告", "type": "monthly", "date": "2026-06-25", "summary": "宏观环境整体向好", "url": "#"},
    ]


# ============================================================
# User/Settings Endpoints
# ============================================================
@app.get("/api/user/profile")
async def get_user_profile():
    """Get user profile"""
    return {
        "id": "1",
        "email": "demo@quantmatrix.cn",
        "name": "Demo User",
        "company": "演示公司",
        "plan": "pro",
    }


@app.put("/api/user/profile")
async def update_user_profile(profile: dict):
    """Update user profile"""
    return {"status": "success", "message": "Profile updated"}


# ============================================================
# Error Handlers
# ============================================================
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
