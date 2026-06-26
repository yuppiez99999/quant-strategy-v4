"""
LSEG Financial Data Connector for Quantitative Strategy System v5.0

Provides access to LSEG financial data through MCP (Model Context Protocol) server.
Supports: equity research, bond pricing, FX rates, options volatility, macro indicators.

Priority Level: 3 (after Wind MCP and iFinD MCP)
"""

import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class LSEGMCPConnector:
    """
    LSEG Financial Analytics MCP Connector
    
    Connects to LSEG MCP Server to access:
    - Equity Research (IBES consensus, fundamentals, prices)
    - Bond Pricing & Yield Curves
    - FX Spot & Forward Rates
    - Options Volatility Surfaces
    - Macro Economic Indicators
    - Historical Time Series
    """
    
    def __init__(self, base_url: str = "https://api.analytics.lseg.com/lfa/mcp", 
                 api_key: Optional[str] = None):
        """
        Initialize LSEG MCP Connector
        
        Args:
            base_url: LSEG MCP Server URL
            api_key: LSEG API authentication key
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or self._load_api_key()
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
        
        logger.info(f"LSEG MCP Connector initialized: {base_url}")
    
    def _load_api_key(self) -> Optional[str]:
        """Load API key from environment or config"""
        import os
        return os.environ.get('LSEG_API_KEY')
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make HTTP request to LSEG MCP Server"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"LSEG API request failed: {e}")
            return None
    
    # ==================== Equity Research ====================
    
    def get_equity_research(self, ticker: str, exchange: str = "US") -> Optional[Dict]:
        """
        Get equity research snapshot with consensus estimates and fundamentals
        
        Args:
            ticker: Stock ticker symbol (e.g., "AAPL", "MSFT")
            exchange: Exchange code (default: "US")
            
        Returns:
            Dict containing:
            - consensus_estimates: IBES analyst consensus
            - fundamentals: Company financial metrics
            - price_performance: Recent price movements
            - valuation_metrics: P/E, P/B, EV/EBITDA etc.
        """
        logger.info(f"Fetching equity research for {ticker}.{exchange}")
        
        result = self._make_request("equity/research", {
            'ticker': ticker,
            'exchange': exchange
        })
        
        if result:
            logger.info(f"✓ Equity research retrieved for {ticker}")
            return result
        else:
            logger.warning(f"✗ Failed to fetch equity research for {ticker}")
            return None
    
    def get_company_fundamentals(self, ticker: str) -> Optional[Dict]:
        """
        Get company fundamental data
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dict with revenue, earnings, cash flow, balance sheet metrics
        """
        logger.info(f"Fetching fundamentals for {ticker}")
        
        result = self._make_request("equity/fundamentals", {
            'ticker': ticker
        })
        
        if result:
            logger.info(f"✓ Fundamentals retrieved for {ticker}")
            return result
        return None
    
    def get_consensus_estimates(self, ticker: str) -> Optional[Dict]:
        """
        Get IBES consensus analyst estimates
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dict with EPS estimates, revenue forecasts, recommendation trends
        """
        logger.info(f"Fetching consensus estimates for {ticker}")
        
        result = self._make_request("equity/consensus", {
            'ticker': ticker
        })
        
        if result:
            logger.info(f"✓ Consensus estimates retrieved for {ticker}")
            return result
        return None
    
    # ==================== Bond Analysis ====================
    
    def get_bond_pricing(self, isin: str) -> Optional[Dict]:
        """
        Get bond pricing and yield data
        
        Args:
            isin: International Securities Identification Number
            
        Returns:
            Dict with price, yield, duration, spread metrics
        """
        logger.info(f"Fetching bond pricing for ISIN: {isin}")
        
        result = self._make_request("bonds/pricing", {
            'isin': isin
        })
        
        if result:
            logger.info(f"✓ Bond pricing retrieved for {isin}")
            return result
        return None
    
    def get_yield_curve(self, currency: str = "USD", tenor: str = "10Y") -> Optional[Dict]:
        """
        Get yield curve data
        
        Args:
            currency: Currency code (USD, EUR, GBP, etc.)
            tenor: Maturity tenor (2Y, 5Y, 10Y, 30Y)
            
        Returns:
            Dict with government bond yields, swap rates, spread curves
        """
        logger.info(f"Fetching {currency} yield curve ({tenor})")
        
        result = self._make_request("rates/yield-curve", {
            'currency': currency,
            'tenor': tenor
        })
        
        if result:
            logger.info(f"✓ Yield curve retrieved for {currency} {tenor}")
            return result
        return None
    
    # ==================== FX Analysis ====================
    
    def get_fx_rates(self, pair: str) -> Optional[Dict]:
        """
        Get FX spot and forward rates
        
        Args:
            pair: Currency pair (e.g., "EURUSD", "GBPJPY")
            
        Returns:
            Dict with spot rate, forward points, swap rates
        """
        logger.info(f"Fetching FX rates for {pair}")
        
        result = self._make_request("fx/rates", {
            'pair': pair
        })
        
        if result:
            logger.info(f"✓ FX rates retrieved for {pair}")
            return result
        return None
    
    def get_fx_carry_analysis(self, pair: str) -> Optional[Dict]:
        """
        Analyze FX carry trade opportunities
        
        Args:
            pair: Currency pair
            
        Returns:
            Dict with carry-to-vol ratio, historical context, trade signals
        """
        logger.info(f"Analyzing FX carry for {pair}")
        
        result = self._make_request("fx/carry-analysis", {
            'pair': pair
        })
        
        if result:
            logger.info(f"✓ FX carry analysis completed for {pair}")
            return result
        return None
    
    # ==================== Options Analysis ====================
    
    def get_option_volatility(self, underlying: str, expiry: str = None) -> Optional[Dict]:
        """
        Get option volatility surface and Greeks
        
        Args:
            underlying: Underlying asset ticker
            expiry: Option expiry date (YYYY-MM-DD)
            
        Returns:
            Dict with implied vol surface, Greeks, SABR parameters
        """
        logger.info(f"Fetching option vol for {underlying}")
        
        params = {'underlying': underlying}
        if expiry:
            params['expiry'] = expiry
        
        result = self._make_request("options/volatility", params)
        
        if result:
            logger.info(f"✓ Option volatility retrieved for {underlying}")
            return result
        return None
    
    # ==================== Macro Indicators ====================
    
    def get_macro_dashboard(self, country: str = "US") -> Optional[Dict]:
        """
        Build macro and rates dashboard
        
        Args:
            country: Country code (US, CN, EU, JP, etc.)
            
        Returns:
            Dict with GDP, inflation, unemployment, policy rates, yield curves
        """
        logger.info(f"Fetching macro dashboard for {country}")
        
        result = self._make_request("macro/dashboard", {
            'country': country
        })
        
        if result:
            logger.info(f"✓ Macro dashboard retrieved for {country}")
            return result
        return None
    
    def get_economic_indicators(self, indicator: str, country: str = "US") -> Optional[Dict]:
        """
        Get specific economic indicator time series
        
        Args:
            indicator: Indicator name (GDP, CPI, UNEMPLOYMENT, etc.)
            country: Country code
            
        Returns:
            Dict with historical time series data
        """
        logger.info(f"Fetching {indicator} for {country}")
        
        result = self._make_request("macro/indicators", {
            'indicator': indicator,
            'country': country
        })
        
        if result:
            logger.info(f"✓ {indicator} data retrieved for {country}")
            return result
        return None
    
    # ==================== Time Series ====================
    
    def get_historical_prices(self, ticker: str, start_date: str = None, 
                             end_date: str = None, frequency: str = "daily") -> Optional[Dict]:
        """
        Get historical price time series
        
        Args:
            ticker: Asset ticker
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            frequency: Data frequency (daily, weekly, monthly)
            
        Returns:
            Dict with OHLCV time series
        """
        logger.info(f"Fetching historical prices for {ticker}")
        
        params = {
            'ticker': ticker,
            'frequency': frequency
        }
        
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        
        result = self._make_request("timeseries/prices", params)
        
        if result:
            logger.info(f"✓ Historical prices retrieved for {ticker}")
            return result
        return None
    
    # ==================== Portfolio Analysis ====================
    
    def analyze_fixed_income_portfolio(self, holdings: List[Dict]) -> Optional[Dict]:
        """
        Review fixed income portfolio with pricing and scenario analysis
        
        Args:
            holdings: List of bond holdings with ISIN and quantity
            
        Returns:
            Dict with portfolio analytics, key rate duration, scenario tests
        """
        logger.info(f"Analyzing FI portfolio with {len(holdings)} holdings")
        
        result = self._make_request("portfolio/fi-analysis", {
            'holdings': holdings
        })
        
        if result:
            logger.info(f"✓ FI portfolio analysis completed")
            return result
        return None
    
    # ==================== Utility Methods ====================
    
    def test_connection(self) -> bool:
        """Test LSEG MCP Server connection"""
        try:
            result = self._make_request("health")
            if result:
                logger.info("✓ LSEG MCP Server connection successful")
                return True
            else:
                logger.warning("✗ LSEG MCP Server health check failed")
                return False
        except Exception as e:
            logger.error(f"✗ LSEG MCP Server connection error: {e}")
            return False
    
    def get_available_endpoints(self) -> List[str]:
        """Get list of available API endpoints"""
        try:
            result = self._make_request("endpoints")
            if result and 'endpoints' in result:
                return result['endpoints']
            return []
        except Exception as e:
            logger.error(f"Failed to get endpoints: {e}")
            return []


# ==================== Integration Helper ====================

def create_lseg_connector(api_key: str = None) -> LSEGMCPConnector:
    """
    Factory function to create LSEG connector
    
    Args:
        api_key: Optional LSEG API key
        
    Returns:
        Configured LSEGMCPConnector instance
    """
    return LSEGMCPConnector(api_key=api_key)


if __name__ == "__main__":
    # Test the connector
    import os
    
    # Set your LSEG API key here or in environment variable
    api_key = os.environ.get('LSEG_API_KEY', '')
    
    connector = create_lseg_connector(api_key)
    
    # Test connection
    if connector.test_connection():
        print("\n✅ LSEG MCP Server connected successfully!")
        
        # Test equity research
        equity_data = connector.get_equity_research("AAPL")
        if equity_data:
            print(f"\n📊 AAPL Equity Research:")
            print(json.dumps(equity_data, indent=2))
        
        # Test macro dashboard
        macro_data = connector.get_macro_dashboard("US")
        if macro_data:
            print(f"\n🌍 US Macro Dashboard:")
            print(json.dumps(macro_data, indent=2))
    else:
        print("\n❌ Failed to connect to LSEG MCP Server")
        print("Please check your API key and network connection")
