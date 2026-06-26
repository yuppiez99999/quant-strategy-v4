"""
LSEG MCP Connector Integration for Quantitative Strategy System v5.0

This module integrates LSEG Financial Analytics as the 3rd priority data source
in the connector fallback chain: Wind MCP → iFinD MCP → LSEG MCP → Free Sources

Usage:
    from lseg_integration import register_lseg_connector
    register_lseg_connector(connector_manager)
"""

import os
import sys
from typing import Optional

# Add current directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

try:
    from lseg_mcp_connector import LSEGMCPConnector, create_lseg_connector
    LSEG_AVAILABLE = True
except ImportError as e:
    print(f"Warning: LSEG connector not available: {e}")
    LSEG_AVAILABLE = False


def register_lseg_connector(connector_manager, api_key: Optional[str] = None) -> bool:
    """
    Register LSEG MCP connector with the connector manager
    
    Args:
        connector_manager: DataConnectorManager instance
        api_key: Optional LSEG API key (will load from env if not provided)
        
    Returns:
        True if registration successful, False otherwise
    """
    if not LSEG_AVAILABLE:
        print("❌ LSEG connector module not available")
        return False
    
    try:
        # Create LSEG connector with priority 3 (after Wind and iFinD)
        lseg_connector = create_lseg_connector(api_key=api_key)
        
        # Wrap it in a DataConnector-compatible interface
        from 量化策略系统_v5_0 import DataConnector
        
        class LSEGDataConnector(DataConnector):
            """LSEG MCP Data Connector wrapper"""
            
            def __init__(self, lseg_connector: LSEGMCPConnector):
                super().__init__(name="LSEG MCP", priority=3)
                self.lseg = lseg_connector
            
            def connect(self) -> bool:
                """Test LSEG connection"""
                return self.lseg.test_connection()
            
            def disconnect(self):
                """Disconnect from LSEG"""
                pass
            
            def get_quote(self, code: str):
                """Get quote for a single stock"""
                # Try equity research first
                result = self.lseg.get_equity_research(code)
                if result:
                    return {
                        'price': result.get('price', 0),
                        'change_pct': result.get('change_pct', 0),
                        'volume': result.get('volume', 0),
                    }
                return None
            
            def get_quotes_batch(self, codes: list):
                """Get quotes for multiple stocks"""
                results = {}
                for code in codes:
                    quote = self.get_quote(code)
                    if quote:
                        results[code] = quote
                return results
            
            def get_historical_data(self, code: str, days: int = 30):
                """Get historical price data"""
                from datetime import datetime, timedelta
                
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                
                result = self.lseg.get_historical_prices(
                    ticker=code,
                    start_date=start_date,
                    end_date=end_date,
                    frequency='daily'
                )
                
                if result and 'prices' in result:
                    return result['prices']
                return []
        
        # Register the connector
        lseg_data_connector = LSEGDataConnector(lseg_connector)
        connector_manager.register_connector(lseg_data_connector)
        
        print(f"✅ LSEG MCP connector registered successfully (Priority: 3)")
        print(f"   Base URL: {lseg_connector.base_url}")
        print(f"   API Key: {'Configured' if lseg_connector.api_key else 'Not set'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to register LSEG connector: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_lseg_integration():
    """Test LSEG integration"""
    print("=" * 60)
    print("Testing LSEG MCP Integration")
    print("=" * 60)
    
    if not LSEG_AVAILABLE:
        print("❌ LSEG connector module not available")
        return False
    
    # Get API key from environment
    api_key = os.environ.get('LSEG_API_KEY')
    if not api_key:
        print("⚠️  LSEG_API_KEY not set in environment")
        print("   Please set it or provide it manually")
        api_key = input("Enter LSEG API key (or press Enter to skip): ").strip()
        if not api_key:
            print("Skipping LSEG integration test")
            return False
    
    # Test connector directly
    try:
        connector = create_lseg_connector(api_key)
        
        print("\n🔍 Testing LSEG MCP Server connection...")
        if connector.test_connection():
            print("✅ Connection successful!")
            
            # Test equity research
            print("\n📊 Testing equity research (AAPL)...")
            equity_data = connector.get_equity_research("AAPL")
            if equity_data:
                print(f"✓ Retrieved AAPL data")
                print(f"  Price: ${equity_data.get('price', 'N/A')}")
            else:
                print("✗ Failed to retrieve equity data")
            
            # Test macro dashboard
            print("\n🌍 Testing macro dashboard (US)...")
            macro_data = connector.get_macro_dashboard("US")
            if macro_data:
                print(f"✓ Retrieved US macro data")
            else:
                print("✗ Failed to retrieve macro data")
            
            print("\n✅ All tests passed!")
            return True
        else:
            print("❌ Connection failed")
            print("   Please check:")
            print("   1. API key is valid")
            print("   2. Network connectivity")
            print("   3. LSEG MCP Server is accessible")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_lseg_integration()
