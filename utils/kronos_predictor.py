"""
Kronos价格预测模块
集成到量化策略系统v5.1

功能：
- 加载Kronos-small金融K线预测模型
- 预测股票/加密货币未来价格走势
- 生成交易信号（buy/sell/hold）
- 与现有量化系统（康波周期、社保基金）集成

作者：量化策略系统v5.1
日期：2026-06-25
"""
import sys
import os
import json
import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, Dict, Optional

# Kronos路径
_KRONOS_BASE = os.path.join(os.path.dirname(__file__), '..', 'Kronos')
if _KRONOS_BASE not in sys.path:
    sys.path.insert(0, _KRONOS_BASE)


class KronosPredictor:
    """Kronos金融K线预测器"""
    
    def __init__(self, device: str = "cpu", verbose: bool = True):
        """
        初始化预测器
        
        Args:
            device: 运行设备 ('cpu' 或 'cuda:0')
            verbose: 是否打印详细信息
        """
        self.device = device
        self.verbose = verbose
        self.model = None
        self.tokenizer = None
        self.predictor_obj = None
        
        if self.verbose:
            print("=" * 60)
            print("Kronos价格预测模块 v1.0")
            print("=" * 60)
        
        self._load_model()
    
    def _load_model(self):
        """加载Kronos模型和Tokenizer - 从HuggingFace加载"""
        if self.verbose:
            print("\n[1/3] 加载KronosTokenizer...")
        
        try:
            from model import Kronos, KronosTokenizer, KronosPredictor as KP
        except ImportError:
            if self.verbose:
                print("[ERROR] 无法导入Kronos模块，请确认已克隆Kronos项目到正确位置")
                print(f"  期望路径: {_KRONOS_BASE}")
            return
        
        try:
            # 从HuggingFace加载tokenizer
            self.tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
            if self.verbose:
                print(f"  [OK] Tokenizer加载成功")
        except Exception as e:
            if self.verbose:
                print(f"  [ERROR] Tokenizer加载失败: {e}")
            return
        
        if self.verbose:
            print("\n[2/3] 加载Kronos-small模型...")
        
        try:
            # 从HuggingFace加载模型
            self.model = Kronos.from_pretrained("NeoQuasar/Kronos-small")
            if self.verbose:
                print("  [OK] 模型加载成功")
                print(f"  参数量: 24.7M")
                print(f"  上下文长度: 512")
        except Exception as e:
            if self.verbose:
                print(f"  [ERROR] 模型加载失败: {e}")
            return
        
        if self.verbose:
            print("\n[3/3] 初始化预测器...")
        
        try:
            self.predictor_obj = KP(self.model, self.tokenizer, device=self.device, max_context=512)
            if self.verbose:
                print(f"  [OK] 预测器初始化完成 (device={self.device})")
                print("=" * 60)
        except Exception as e:
            if self.verbose:
                print(f"\n  [ERROR] 预测器初始化失败: {e}")
    
    def predict_prices(
        self, 
        df: pd.DataFrame, 
        pred_len: int = 24,
        column_names: Optional[list] = None
    ) -> pd.DataFrame:
        """
        预测未来价格走势
        
        Args:
            df: 历史OHLCV数据，必须包含 timestamp, open, high, low, close, volume
            pred_len: 预测步长（默认24小时）
            column_names: 列名列表，默认为None使用默认值
            
        Returns:
            预测结果DataFrame
        """
        if self.predictor_obj is None:
            raise RuntimeError("Kronos预测器未初始化，请检查模型加载是否成功")
        
        if column_names is None:
            column_names = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        
        # 确保有amount列（Kronos需要）
        if 'amount' not in df.columns:
            df = df.copy()
            df['amount'] = df['volume'] * df['close']
        
        # 准备输入数据
        input_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
        x_df = df[input_cols].reset_index(drop=True)
        
        # 如果有timestamp列，使用它
        if 'timestamp' in df.columns:
            x_timestamp = df['timestamp'].reset_index(drop=True)
            # 生成未来日期
            last_date = x_timestamp.iloc[-1]
            future_dates = []
            current_date = last_date + timedelta(days=1)
            while len(future_dates) < pred_len:
                if current_date.weekday() < 5:  # 工作日
                    future_dates.append(current_date)
                current_date += timedelta(days=1)
            y_timestamp = pd.Series(future_dates)
        else:
            x_timestamp = None
            y_timestamp = None
        
        # 执行预测
        forecast = self.predictor_obj.predict(
            df=x_df,
            x_timestamp=x_timestamp,
            y_timestamp=y_timestamp,
            pred_len=pred_len,
            T=1.0,
            top_p=0.9,
            sample_count=1,
            verbose=False
        )
        
        return forecast
    
    def get_signal(
        self, 
        df: pd.DataFrame, 
        pred_len: int = 24,
        threshold: float = 0.02
    ) -> Tuple[str, float]:
        """
        生成交易信号
        
        Args:
            df: 历史数据
            pred_len: 预测步长
            threshold: 信号阈值（默认2%）
            
        Returns:
            (信号, 预期收益率)
            信号: 'buy', 'sell', 或 'hold'
        """
        forecast = self.predict_prices(df, pred_len)
        
        # 获取预测的收盘价
        predicted_close = forecast['close'].iloc[-1]
        current_close = df['close'].iloc[-1]
        
        # 计算预期收益率
        return_pct = (predicted_close - current_close) / current_close
        
        # 生成信号
        if return_pct > threshold:
            signal = 'buy'
        elif return_pct < -threshold:
            signal = 'sell'
        else:
            signal = 'hold'
        
        return signal, return_pct
    
    def analyze_stock(
        self, 
        code: str, 
        name: str, 
        df: pd.DataFrame,
        pred_len: int = 24
    ) -> Dict:
        """
        分析单只股票
        
        Args:
            code: 股票代码
            name: 股票名称
            df: OHLCV数据
            pred_len: 预测步长
            
        Returns:
            分析结果字典
        """
        signal, return_pct = self.get_signal(df, pred_len)
        
        current_price = df['close'].iloc[-1]
        predicted_price = current_price * (1 + return_pct)
        
        result = {
            'code': code,
            'name': name,
            'current_price': current_price,
            'predicted_price': predicted_price,
            'return_pct': return_pct,
            'signal': signal,
            'pred_len': pred_len,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if self.verbose:
            self._print_analysis(result)
        
        return result
    
    def _print_analysis(self, result: Dict):
        """打印分析结果"""
        signal_icon = {
            'buy': '🟢',
            'sell': '🔴',
            'hold': '🟡'
        }.get(result['signal'], '⚪')
        
        print(f"\n{signal_icon} {result['name']} ({result['code']})")
        print(f"  当前价格: {result['current_price']:.2f}")
        print(f"  预测价格: {result['predicted_price']:.2f}")
        print(f"  预期收益: {result['return_pct']*100:+.2f}%")
        print(f"  交易信号: {result['signal'].upper()}")
        print(f"  预测时长: {result['pred_len']}小时")


def fetch_a_stock_data(
    code: str, 
    days: int = 100,
    verbose: bool = True
) -> pd.DataFrame:
    """
    获取A股数据 - 多数据源优先级：Wind MCP > iFinD MCP > 腾讯财经 > 新浪财经 > 同花顺 > 本地缓存
    
    Args:
        code: 股票代码 (如 '000001')
        days: 获取天数
        verbose: 是否打印详细信息
        
    Returns:
        OHLCV DataFrame
    """
    # 尝试1: Wind MCP (如果可用)
    if verbose:
        print(f"  [1/6] 尝试Wind MCP...")
    try:
        df = _fetch_from_wind(code, days)
        if df is not None and not df.empty:
            if verbose:
                print(f"  [OK] Wind MCP获取 {code} ({len(df)}条)")
            return df
    except Exception as e:
        if verbose:
            print(f"  [SKIP] Wind MCP不可用: {str(e)[:50]}")
    
    # 尝试2: 腾讯财经
    if verbose:
        print(f"  [2/6] 尝试腾讯财经...")
    try:
        df = _fetch_from_tencent(code, days)
        if df is not None and not df.empty:
            if verbose:
                print(f"  [OK] 腾讯财经获取 {code} ({len(df)}条)")
            return df
    except Exception as e:
        if verbose:
            print(f"  [SKIP] 腾讯财经失败: {str(e)[:50]}")
    
    # 尝试3: 新浪财经
    if verbose:
        print(f"  [3/6] 尝试新浪财经...")
    try:
        df = _fetch_from_sina(code, days)
        if df is not None and not df.empty:
            if verbose:
                print(f"  [OK] 新浪财经获取 {code} ({len(df)}条)")
            return df
    except Exception as e:
        if verbose:
            print(f"  [SKIP] 新浪财经失败: {str(e)[:50]}")
    
    # 尝试4: 东方财富 (同花顺API难解析，改用东财)
    if verbose:
        print(f"  [4/6] 尝试东方财富...")
    try:
        df = _fetch_from_10jqka(code, days)
        if df is not None and not df.empty:
            if verbose:
                print(f"  [OK] 东方财富获取 {code} ({len(df)}条)")
            return df
    except Exception as e:
        if verbose:
            print(f"  [SKIP] 东方财富失败: {str(e)[:50]}")
    
    # 尝试5: 本地parquet缓存
    if verbose:
        print(f"  [5/6] 尝试本地缓存...")
    df = _fetch_from_local_cache(code, days, verbose)
    if df is not None and not df.empty:
        return df
    
    # 尝试6: akshare作为最后备用
    if verbose:
        print(f"  [6/6] 尝试akshare...")
    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        
        # 重命名列
        df = df.rename(columns={
            '日期': 'timestamp',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume'
        })
        
        # 只保留最近days条
        df = df.tail(days).reset_index(drop=True)
        
        # 转换时间戳
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        if verbose:
            print(f"  [OK] akshare获取 {code} ({len(df)}条)")
        return df
    except ImportError:
        pass
    except Exception as e:
        if verbose:
            print(f"  [ERROR] akshare失败: {str(e)[:80]}")
    
    raise RuntimeError(f"所有数据源都无法获取股票{code}数据")


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """标准化列名"""
    # 列名映射
    col_map = {
        'date': 'timestamp', 'dates': 'timestamp', '日期': 'timestamp',
        'open': 'open', 'open_price': 'open', '开盘': 'open', '开盘价': 'open',
        'high': 'high', 'high_price': 'high', '最高': 'high', '最高价': 'high',
        'low': 'low', 'low_price': 'low', '最低': 'low', '最低价': 'low',
        'close': 'close', 'close_price': 'close', '收盘': 'close', '收盘价': 'close',
        'volume': 'volume', '成交量': 'volume',
        'amount': 'amount', '成交额': 'amount',
        'turnover': 'turnover', '换手率': 'turnover'
    }
    
    # 重命名
    df = df.rename(columns={col: new_col for col, new_col in col_map.items() if col in df.columns})
    
    # 确保必要列存在
    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"缺少必要列: {col}")
    
    # 转换时间戳
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
    
    # 添加amount列（如果没有）
    if 'amount' not in df.columns:
        df['amount'] = df['volume'] * df['close']
    
    return df


def _fetch_from_wind(code: str, days: int) -> pd.DataFrame:
    """从Wind MCP获取K线数据 (P0 — 最高优先级, 直接HTTPS + SSE解析)"""
    import urllib.request
    import ssl
    import json
    
    # API Key 读取：环境变量 > .env文件 > 全局配置
    api_key = os.environ.get('WIND_API_KEY', '')
    if not api_key:
        # 尝试从 .env 读取
        for env_dir in [os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))]:
            env_path = os.path.join(env_dir, '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('#') or '=' not in line:
                            continue
                        k, v = line.split('=', 1)
                        if k.strip() == 'WIND_API_KEY':
                            api_key = v.strip().strip('"').strip("'")
                            break
            if api_key:
                break
    if not api_key:
        # 尝试从全局配置文件读取
        global_config = os.path.expanduser(r'~\.wind-aifinmarket\config')
        if os.path.exists(global_config):
            with open(global_config, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'WIND_API_KEY=' in line:
                        api_key = line.split('=', 1)[1].strip()
                        break
    if not api_key or len(api_key) < 10:
        raise ValueError("WIND_API_KEY 未配置或无效")
    
    # 构造windcode
    if code.startswith('6') or code.startswith('5'):
        windcode = f"{code}.SH"
    else:
        windcode = f"{code}.SZ"
    
    # 计算日期范围
    end_date = datetime.now().strftime('%Y%m%d')
    begin_date = (datetime.now() - timedelta(days=days + 30)).strftime('%Y%m%d')
    
    endpoint = "https://mcp.wind.com.cn/vserver_stock_data/mcp/"
    
    # ---- 第一步: MCP Initialize ----
    init_body = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "kronos-predictor", "version": "1.0"}
        }
    }).encode('utf-8')
    
    ctx = ssl.create_default_context()
    
    def _wind_mcp_request(payload: bytes) -> dict:
        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Accept': 'application/json, text/event-stream',
                'Content-Type': 'application/json',
            },
            method='POST'
        )
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            raw = resp.read().decode('utf-8')
        # SSE 解析: 查找 "data: " 行后 JSON
        for line in raw.split('\n'):
            line = line.strip()
            if line.startswith('data: '):
                return json.loads(line[6:])
        # Fallback: 纯 JSON
        return json.loads(raw)
    
    try:
        # 初始化
        init_data = _wind_mcp_request(init_body)
        if init_data.get('error'):
            msg = init_data['error'].get('message', str(init_data['error']))
            raise ValueError(f"Init error: {msg[:100]}")
    except Exception as e:
        raise RuntimeError(f"Wind MCP 初始化失败: {str(e)[:100]}")
    
    # ---- 第二步: tools/call ----
    call_body = json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_stock_kline",
            "arguments": {
                "windcode": windcode,
                "begin_date": begin_date,
                "end_date": end_date
            },
            "_meta": {"clientVersion": "1.9.2"}
        }
    }).encode('utf-8')
    
    try:
        call_data = _wind_mcp_request(call_body)
    except Exception as e:
        raise RuntimeError(f"Wind MCP 请求失败: {str(e)[:100]}")
    
    if call_data.get('error'):
        msg = call_data['error'].get('message', str(call_data['error']))
        raise ValueError(f"Wind error: {msg[:100]}")
    
    # 提取 content[0].text
    result = call_data.get('result', {})
    content = result.get('content', [])
    if not content:
        raise ValueError("Wind返回空content")
    
    inner_text = content[0].get('text', '{}')
    inner = json.loads(inner_text)
    
    if inner.get('error'):
        raise ValueError(f"Wind业务错误: {str(inner['error'])[:100]}")
    
    data_block = inner.get('data')
    if not data_block:
        raise ValueError("Wind data为空")
    
    columns = [c["name"] for c in data_block.get("columns", [])]
    rows = data_block.get("rows", [])
    if not rows:
        raise ValueError("Wind返回0条记录")
    
    df = pd.DataFrame(rows, columns=columns)
    
    # 列名映射 — Wind K线列: TIME/OPEN/MATCH(收盘)/HIGH/LOW/TURNOVER/VOLUME/CHANGEHANDRATE/AVPRICE/_DATE
    col_map = {}
    for c in columns:
        if c == 'TIME': col_map[c] = 'timestamp'
        elif c == 'OPEN': col_map[c] = 'open'
        elif c == 'MATCH': col_map[c] = 'close'
        elif c == 'HIGH': col_map[c] = 'high'
        elif c == 'LOW': col_map[c] = 'low'
        elif c == 'VOLUME': col_map[c] = 'volume'
    df = df.rename(columns=col_map)
    
    for c in ["open", "close", "high", "low", "volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    
    df = df[df["close"] > 0].copy()
    df = df.dropna(subset=["open", "close", "high", "low"]).tail(days).reset_index(drop=True)
    
    return _normalize_columns(df)


def _fetch_from_tencent(code: str, days: int) -> pd.DataFrame:
    """从腾讯财经获取日K线数据 (P1备份)"""
    import requests
    
    # 确定腾讯财经前缀 (使用sh/sz而非1./0.)
    if code.startswith('6') or code.startswith('5'):
        prefix = f"sh{code}"  # 沪市
    elif code.startswith('0') or code.startswith('3'):
        prefix = f"sz{code}"  # 深市
    else:
        prefix = f"sh{code}"
    
    # 腾讯财经日K线接口（前复权）
    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix},day,,,{days},qfq"
    
    response = requests.get(url, timeout=10, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://gu.qq.com/'
    })
    
    if response.status_code != 200:
        raise ValueError(f"腾讯财经HTTP {response.status_code}")
    
    try:
        data = response.json()
    except:
        raise ValueError("腾讯财经返回非JSON")
    
    # 解析嵌套JSON — key使用 sh/sz 前缀格式
    stock_data = data.get('data', {}).get(prefix, {})
    if not stock_data:
        raise ValueError("腾讯财经数据为空(prefix)")
    
    # 优先取复权数据(qfqday)，fallback到day
    day_data = stock_data.get('qfqday', None) or stock_data.get('day', [])
    
    if not day_data or len(day_data) == 0:
        raise ValueError("腾讯财经K线数据为空")
    
    records = []
    for item in day_data:
        if len(item) >= 5:
            try:
                records.append({
                    'timestamp': str(item[0]),
                    'open': float(item[1]),
                    'close': float(item[2]),
                    'high': float(item[3]),
                    'low': float(item[4]),
                    'volume': float(item[5]) if len(item) > 5 and item[5] else 0
                })
            except (ValueError, TypeError):
                continue
    
    if not records:
        raise ValueError("腾讯财经数据解析失败")
    
    df = pd.DataFrame(records)
    df = _normalize_columns(df)
    df = df.tail(days).reset_index(drop=True)
    return df


def _fetch_from_sina(code: str, days: int) -> pd.DataFrame:
    """从新浪财经获取日K线数据 (P2备份)"""
    import requests
    
    # 新浪K线是用前复权数据，symbol格式为sh601088 或 sz002371
    if code.startswith('6') or code.startswith('5'):
        symbol = f"sh{code}"
    elif code.startswith('0') or code.startswith('3'):
        symbol = f"sz{code}"
    else:
        symbol = f"sh{code}"
    
    # 新浪K线API — scale=240表示日线
    url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
    
    response = requests.get(url, params={
        'symbol': symbol,
        'scale': '240',
        'ma': 'no',
        'datalen': days
    }, timeout=15, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://finance.sina.com.cn/',
    })
    
    if response.status_code != 200:
        raise ValueError(f"新浪财经HTTP {response.status_code}")
    
    if not response.text or len(response.text) < 20:
        raise ValueError("新浪财经返回空响应")
    
    try:
        data = response.json()
    except:
        # 有时返回文本格式不对，尝试从var中提取
        text = response.text
        if 'var ' in text:
            # 尝试提取JSON部分
            import re
            match = re.search(r'\((.*?)\)', text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
            else:
                raise ValueError("新浪财经数据解析失败")
        else:
            raise ValueError(f"新浪财经返回非JSON: {text[:100]}")
    
    if not data or not isinstance(data, list) or len(data) == 0:
        raise ValueError("新浪财经K线数据为空")
    
    records = []
    for item in data:
        try:
            records.append({
                'timestamp': item['day'],
                'open': float(item['open']),
                'close': float(item['close']),
                'high': float(item['high']),
                'low': float(item['low']),
                'volume': float(item['volume'])
            })
        except (KeyError, ValueError, TypeError):
            continue
    
    if not records:
        raise ValueError("新浪财经数据记录为空")
    
    df = pd.DataFrame(records)
    df = _normalize_columns(df)
    df = df.tail(days).reset_index(drop=True)
    return df


def _fetch_from_10jqka(code: str, days: int) -> pd.DataFrame:
    """从东方财富API获取日K线数据 (P3备份 — 同花顺难解析，改用东财)"""
    import requests
    
    # 确定市场secid
    if code.startswith('6') or code.startswith('5'):
        secid = f"1.{code}"  # 上交所
    elif code.startswith('0') or code.startswith('3'):
        secid = f"0.{code}"  # 深交所
    else:
        secid = f"0.{code}"
    
    url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
    end_date = datetime.now().strftime('%Y%m%d')
    begin_date = (datetime.now() - timedelta(days=days + 30)).strftime('%Y%m%d')
    
    params = {
        'secid': secid,
        'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'klt': '101',       # 日线
        'fqt': '1',         # 前复权
        'beg': begin_date,
        'end': end_date,
        'lmt': str(days + 30),
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://quote.eastmoney.com/',
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=15)
    
    if response.status_code != 200:
        raise ValueError(f"东方财富HTTP {response.status_code}")
    
    try:
        data = response.json()
    except:
        # JSONP处理
        text = response.text
        import re
        match = re.search(r'\((.*?)\)', text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
        else:
            raise ValueError("东方财富数据解析失败")
    
    klines = data.get('data', {}).get('klines', [])
    if not klines:
        raise ValueError("东方财富K线数据为空")
    
    records = []
    for line in klines:
        parts = line.split(',')
        if len(parts) >= 6:
            try:
                records.append({
                    'timestamp': parts[0],
                    'open': float(parts[1]),
                    'close': float(parts[2]),
                    'high': float(parts[3]),
                    'low': float(parts[4]),
                    'volume': float(parts[5])
                })
            except (ValueError, TypeError):
                continue
    
    if not records:
        raise ValueError("东方财富数据记录为空")
    
    df = pd.DataFrame(records)
    df = _normalize_columns(df)
    df = df.tail(days).reset_index(drop=True)
    return df


def _fetch_from_local_cache(code: str, days: int, verbose: bool = True) -> pd.DataFrame:
    """从本地缓存获取数据"""
    parquet_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'data', 'cache'),
        os.path.join(os.path.dirname(__file__), '..', 'data', 'stock_data'),
        os.path.join(os.path.dirname(__file__), '..', '14.quantitative_trading_system', 'data'),
    ]
    
    for parquet_dir in parquet_paths:
        if os.path.exists(parquet_dir):
            # 查找匹配的股票文件
            for fname in os.listdir(parquet_dir):
                if fname.endswith('.parquet') and (code in fname or fname.replace('.parquet', '') == code):
                    filepath = os.path.join(parquet_dir, fname)
                    try:
                        df = pd.read_parquet(filepath)
                        if 'timestamp' in df.columns and 'close' in df.columns:
                            if verbose:
                                print(f"  [OK] 本地缓存加载 {code} ({len(df)}条)")
                            return _normalize_columns(df).tail(days).reset_index(drop=True)
                    except:
                        pass
    
    return pd.DataFrame()


def run_batch_prediction(
    stocks: list,
    pred_len: int = 24,
    device: str = "cpu",
    verbose: bool = True
) -> list:
    """
    批量预测多只股票
    
    Args:
        stocks: 股票列表，每项为 {'code': '000001', 'name': '平安银行'}
        pred_len: 预测步长
        device: 运行设备
        verbose: 是否打印详细信息
        
    Returns:
        分析结果列表
    """
    # 初始化预测器
    kp = KronosPredictor(device=device, verbose=verbose)
    
    results = []
    
    for stock in stocks:
        code = stock['code']
        name = stock['name']
        
        try:
            # 获取数据
            df = fetch_a_stock_data(code, days=120, verbose=verbose)
            
            # 分析
            result = kp.analyze_stock(code, name, df, pred_len)
            results.append(result)
            
        except Exception as e:
            if verbose:
                print(f"\n[ERROR] {name} ({code}): {e}")
            results.append({
                'code': code,
                'name': name,
                'error': str(e),
                'signal': 'hold'
            })
    
    return results


if __name__ == "__main__":
    # 测试示例
    print("\n" + "=" * 60)
    print("Kronos预测模块 - 独立测试")
    print("=" * 60)
    
    # 定义测试股票列表
    test_stocks = [
        {'code': '000001', 'name': '平安银行'},
        {'code': '600519', 'name': '贵州茅台'},
        {'code': '000858', 'name': '五粮液'},
    ]
    
    # 批量预测
    results = run_batch_prediction(test_stocks, pred_len=24, device="cpu")
    
    # 打印汇总
    print("\n" + "=" * 60)
    print("预测结果汇总")
    print("=" * 60)
    
    buy_signals = [r for r in results if r.get('signal') == 'buy']
    sell_signals = [r for r in results if r.get('signal') == 'sell']
    hold_signals = [r for r in results if r.get('signal') == 'hold']
    
    print(f"\n买入信号: {len(buy_signals)} 只")
    for r in buy_signals:
        print(f"  - {r['name']} ({r['code']}): +{r['return_pct']*100:.2f}%")
    
    print(f"\n卖出信号: {len(sell_signals)} 只")
    for r in sell_signals:
        print(f"  - {r['name']} ({r['code']}): {r['return_pct']*100:.2f}%")
    
    print(f"\n持有信号: {len(hold_signals)} 只")
    for r in hold_signals:
        print(f"  - {r['name']} ({r['code']}): {r['return_pct']*100:+.2f}%")
    
    print("\n" + "=" * 60)
