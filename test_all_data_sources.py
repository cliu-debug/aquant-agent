#!/usr/bin/env python
"""测试所有数据源集成"""

import sys
sys.path.insert(0, '.')

print('=' * 60)
print('测试 AStockAgents 完整数据源集成')
print('=' * 60)
print()

# 测试数据管理器
from astock_agents.data.data_manager import DataManager

manager = DataManager()
print('✅ 数据管理器初始化成功')
print()

# 测试获取完整股票数据
print('测试获取完整股票数据...')
stock = manager.get_stock_data('600519.SH', '贵州茅台')

if stock:
    print(f'✅ 股票数据获取成功:')
    print(f'   代码: {stock.stock_code}')
    print(f'   名称: {stock.stock_name}')
    print(f'   PE(TTM): {stock.pe_ttm}')
    print(f'   PB: {stock.pb}')
    print(f'   市值: {stock.market_cap}亿')
    print(f'   行业: {stock.industry}')
    print(f'   K线数据: {len(stock.prices)}条')
    if stock.prices:
        latest = stock.prices[-1]
        print(f'   最新价格: {latest.close}')
else:
    print('❌ 股票数据获取失败')

print()
print('=' * 60)
print()

# 测试特色数据接口
print('测试特色数据接口...')

# 1. 热点强势股
hot_stocks = manager.get_hot_stocks()
print(f'✅ 热点强势股: {len(hot_stocks)}只')
if hot_stocks:
    print(f'   第一名: {hot_stocks[0]["name"]} ({hot_stocks[0]["code"]})')
    print(f'   题材: {hot_stocks[0].get("reason", "N/A")}')

print()

# 2. 北向资金
north_bound = manager.get_north_bound_flow('sh')
if north_bound:
    print(f'✅ 北向资金 (沪股通):')
    print(f'   净流入: {north_bound.get("net_inflow")}')
else:
    print('⚠️ 北向资金数据获取失败')

print()

# 3. 概念板块
concept = manager.get_concept_blocks('600519.SH')
if concept:
    print(f'✅ 概念板块:')
    print(f'   行业: {concept.get("industry", [])}')
    print(f'   概念: {concept.get("concept", [])[:3]}...')

print()

# 4. 龙虎榜
dragon_tiger = manager.get_dragon_tiger('600519.SH')
print(f'✅ 龙虎榜数据: {len(dragon_tiger)}条')

print()

# 5. 新闻
news = manager.get_stock_news('600519.SH', limit=3)
print(f'✅ 个股新闻: {len(news)}条')
if news:
    print(f'   最新: {news[0].get("title", "")[:50]}...')

print()
print('=' * 60)
print()

print('✅ 所有数据源测试完成!')
print()
print('已集成的数据源:')
print('  1. 腾讯财经 - PE/PB/市值/换手率/涨跌停')
print('  2. 东方财富 - 研报/龙虎榜/资金流向/融资融券')
print('  3. 同花顺 - 热点强势股/北向资金/行业排名')
print('  4. 百度股市通 - K线(带MA)/概念板块')
print('  5. 新闻公告 - 个股新闻/财联社/巨潮公告')
