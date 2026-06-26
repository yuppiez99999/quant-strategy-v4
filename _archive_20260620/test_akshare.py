import akshare as ak, os, time
for k in ['http_proxy','https_proxy','HTTP_PROXY','HTTPS_PROXY','all_proxy']:
    os.environ.pop(k, None)

for code in ['688981','300750','300124','002475','603259']:
    print(f'{code}...', end=' ', flush=True)
    ok = False
    for attempt in range(3):
        try:
            df = ak.stock_zh_a_hist(symbol=code, period='daily',
                start_date='20210101', end_date='20260606', adjust='qfq')
            if df is not None and len(df) > 100:
                print(f'OK {len(df)}')
                ok = True
                break
            print(f'R{attempt}', end=' ', flush=True)
        except Exception as e:
            print(f'E{attempt}', end=' ', flush=True)
        time.sleep(3)
    if not ok:
        print('FAILED')
    time.sleep(2)
