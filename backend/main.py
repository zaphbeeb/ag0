from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Annotated
from services.market_data import fetch_historical_data
from services.analysis import optimize_pairs
from datetime import datetime
import pandas as pd
import json

app = FastAPI(title="Momentum Signal API")

# Configure Templates
templates = Jinja2Templates(directory="templates")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BacktestRequest(BaseModel):
    tickers: List[str]
    periods: List[int]
    start_date: str
    end_date: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "now": datetime.now()})

@app.post("/analyze-ui", response_class=HTMLResponse)
async def analyze_ui(
    request: Request,
    tickers: Annotated[str, Form()],
    periods: Annotated[list[int], Form()],
    start_date: Annotated[str, Form()],
    end_date: Annotated[str, Form()]
):
    try:
        # Parse tickers from string
        ticker_list = [t.strip().upper() for t in tickers.split(',')]
        
        # Fetch data
        data_map = fetch_historical_data(ticker_list, start_date, end_date)
        
        results = []
        
        for ticker, df in data_map.items():
            if df.empty:
                continue
                
            # Optimize to find best pair
            best_pair, best_gain, opt_results, df_emas = optimize_pairs(df, periods)
            
            # Prepare chart data
            chart_df = df_emas.reset_index()
            # Handle date serialization - ensure we use the correct column name for date after reset_index
            # yfinance/pandas often puts the date in 'Date' or 'index'
            date_col = 'Date' if 'Date' in chart_df.columns else chart_df.columns[0]
            
            # Convert timestamp to string for JSON serialization in template
            chart_df['Date_Str'] = chart_df[date_col].apply(lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x))
            
            short_p, long_p = best_pair
            chart_cols = ['Date_Str', 'Close', f'EMA_{short_p}', f'EMA_{long_p}']
            
            # Select and rename for consistency in JS
            data_subset = chart_df[chart_cols].rename(columns={'Date_Str': 'Date'})
            chart_data = data_subset.to_dict(orient='records')

            results.append({
                'ticker': ticker,
                'best_pair': {'short': short_p, 'long': long_p},
                'max_gain': best_gain,
                'optimization_results': opt_results,
                'chart_data': chart_data
            })
            
        return templates.TemplateResponse("results.html", {
            "request": request,
            "results": results,
            "now": datetime.now()
        })
        
    except Exception as e:
        return templates.TemplateResponse("base.html", {
            "request": request,
            "content": f"<div class='text-red-500 p-4'>Error: {str(e)}</div>"
        })

@app.post("/analyze")
async def analyze_momentum(request: BacktestRequest):
    try:
        # Fetch data
        data_map = fetch_historical_data(request.tickers, request.start_date, request.end_date)
        
        response_data = []
        
        for ticker, df in data_map.items():
            if df.empty:
                continue
                
            # Optimize to find best pair
            best_pair, best_gain, results, df_emas = optimize_pairs(df, request.periods)
            
            # Prepare chart data (subset for performance, or full)
            chart_df = df_emas.reset_index()
            chart_df['Date'] = chart_df['Date'].dt.strftime('%Y-%m-%d')
            
            short_p, long_p = best_pair
            chart_cols = ['Date', 'Close', f'EMA_{short_p}', f'EMA_{long_p}']
            chart_data = chart_df[chart_cols].to_dict(orient='records')

            response_data.append({
                'ticker': ticker,
                'best_pair': {'short': short_p, 'long': long_p},
                'max_gain': best_gain,
                'optimization_results': results,
                'chart_data': chart_data
            })
            
        return {"results": response_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}
