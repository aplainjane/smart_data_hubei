from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime
import csv
import re

app = Flask(__name__, static_folder='static')
CORS(app)  # 启用跨域支持

# 尝试导入 pandas，如果不可用则使用 csv 回退实现
try:
    import pandas as pd
except Exception:
    pd = None


def _parse_bysj_to_ym(s):
    """把 '2023年1月' 样式转换为 '2023-01'，失败则返回原始字符串。"""
    if not s:
        return s
    m = re.search(r"(\d{4})年\s*(\d{1,2})月", str(s))
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    return str(s)


def load_air_monthly_summary(csv_filename='data/空气污染物平均浓度情况表(0-512).csv'):
    """读取 CSV，返回按月聚合的 chart_data、overview、table_header、table_data。

    实现细节：优先使用 pandas 读取与聚合；如果没有 pandas，则用 csv.DictReader 手动聚合。
    返回的 labels 为 ['1月','2月',...]（按所选时间段顺序），datasets 与之前接口兼容。
    """
    csv_path = os.path.join(os.path.dirname(__file__), csv_filename)

    rows = []
    if pd is not None:
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
        except Exception:
            # 兼容没有指定编码或有 BOM 的情况
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
        # 清理列名
        df.columns = [c.strip() for c in df.columns]
        # 只保留站点行（排除均值行），避免重复计算
        station_rows = df[df['xsq'].astype(str).str.strip() != '均值'].copy()
        if station_rows.empty:
            station_rows = df.copy()
        # month 列
        station_rows['month'] = station_rows['bysj'].apply(_parse_bysj_to_ym)
        # 强制转数字
        for col in ['pm25', 'pm10', 'o3']:
            if col in station_rows.columns:
                station_rows[col] = pd.to_numeric(station_rows[col], errors='coerce')
            else:
                station_rows[col] = pd.NA
        # 按月聚合均值
        grouped = station_rows.groupby('month', sort=True).agg({
            'pm25': 'mean',
            'pm10': 'mean',
            'o3': 'mean'
        })
        grouped = grouped.sort_index()

        # 计算每月最高 PM2.5 的站点
        top_stations = {}
        for month, g in station_rows.groupby('month'):
            g2 = g.copy()
            g2['pm25'] = pd.to_numeric(g2['pm25'], errors='coerce')
            if not g2['pm25'].dropna().empty:
                idx = g2['pm25'].idxmax()
                top_stations[month] = str(g2.loc[idx, 'xsq'])
            else:
                top_stations[month] = ''

        months = grouped.index.tolist()
        labels = [f"{int(m.split('-')[1])}月" if isinstance(m, str) and '-' in m else str(m) for m in months]
        pm25 = grouped['pm25'].round().fillna(0).astype(int).tolist()
        o3 = grouped['o3'].round().fillna(0).astype(int).tolist()
        pm10 = grouped['pm10'].round().fillna(0).astype(int).tolist()

    else:
        # fallback: 使用 csv.DictReader 手动聚合
        if not os.path.exists(csv_path):
            return {}, {}, [], []
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
        # 过滤掉 xsq == '均值'
        rows = [r for r in rows if r.get('xsq', '').strip() != '均值'] or rows
        monthly = {}
        top_stations = {}
        for r in rows:
            month = _parse_bysj_to_ym(r.get('bysj', ''))
            try:
                pm25_v = float(r.get('pm25') or 0)
            except Exception:
                pm25_v = 0
            try:
                pm10_v = float(r.get('pm10') or 0)
            except Exception:
                pm10_v = 0
            try:
                o3_v = float(r.get('o3') or 0)
            except Exception:
                o3_v = 0
            if month not in monthly:
                monthly[month] = {'pm25_sum': 0.0, 'pm10_sum': 0.0, 'o3_sum': 0.0, 'count': 0}
            monthly[month]['pm25_sum'] += pm25_v
            monthly[month]['pm10_sum'] += pm10_v
            monthly[month]['o3_sum'] += o3_v
            monthly[month]['count'] += 1
            # top station
            cur_top = top_stations.get(month)
            if cur_top is None:
                top_stations[month] = (r.get('xsq', ''), pm25_v)
            else:
                if pm25_v > cur_top[1]:
                    top_stations[month] = (r.get('xsq', ''), pm25_v)
        months = sorted(monthly.keys())
        labels = [f"{int(m.split('-')[1])}月" if isinstance(m, str) and '-' in m else str(m) for m in months]
        pm25 = [int(round(monthly[m]['pm25_sum'] / monthly[m]['count'])) if monthly[m]['count'] else 0 for m in months]
        pm10 = [int(round(monthly[m]['pm10_sum'] / monthly[m]['count'])) if monthly[m]['count'] else 0 for m in months]
        o3 = [int(round(monthly[m]['o3_sum'] / monthly[m]['count'])) if monthly[m]['count'] else 0 for m in months]
        # convert top_stations values to names
        top_stations = {m: top_stations[m][0] if isinstance(top_stations[m], tuple) else '' for m in months}

    # 计算累计值（按月份顺序）
    cum_pm25 = []
    cum_o3 = []
    cum_pm10 = []
    s_pm25 = s_o3 = s_pm10 = 0
    for a, b, c in zip(pm25, o3, pm10):
        s_pm25 += a
        s_o3 += b
        s_pm10 += c
        cum_pm25.append(s_pm25)
        cum_o3.append(s_o3)
        cum_pm10.append(s_pm10)

    # 简单的空气质量描述：根据 PM2.5 年平均
    overall_pm25_avg = int(round(sum(pm25) / len(pm25))) if pm25 else 0
    if overall_pm25_avg <= 35:
        quality_label = '良好'
    elif overall_pm25_avg <= 75:
        quality_label = '轻度污染'
    else:
        quality_label = '污染'

    overview = {
        'recordCount': None,  # 记录数视文件而定；在 pandas 分支我们可以更精确
        'stationCount': None,
        'timeSpan': '',
        'avgQuality': quality_label,
        'pm25Avg': f"{overall_pm25_avg} μg/m³",
        'o3Avg': f"{int(round(sum(o3) / len(o3))) if o3 else 0} μg/m³",
        'pm10Avg': f"{int(round(sum(pm10) / len(pm10))) if pm10 else 0} μg/m³"
    }

    # 尝试用 pandas 时填充更精确的 recordCount 与 stationCount 与 timeSpan
    if pd is not None:
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
        except Exception:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
        df.columns = [c.strip() for c in df.columns]
        station_rows = df[df['xsq'].astype(str).str.strip() != '均值']
        overview['recordCount'] = int(len(station_rows))
        overview['stationCount'] = int(station_rows['xsq'].nunique())
        months_full = sorted(list({_parse_bysj_to_ym(x) for x in station_rows['bysj'].tolist()}))
        overview['timeSpan'] = f"{months_full[0]} 至 {months_full[-1]}" if months_full else ''
    else:
        # 在 csv 回退分支中用 rows 填充
        if rows:
            overview['recordCount'] = len(rows)
            overview['stationCount'] = len(set(r.get('xsq','') for r in rows))
            months_full = sorted(list({_parse_bysj_to_ym(r.get('bysj','')) for r in rows}))
            overview['timeSpan'] = f"{months_full[0]} 至 {months_full[-1]}" if months_full else ''

    # 构造 chart_data 与 table
    chart_data = {
        'labels': labels,
        'datasets': [
            {
                'label': '累计细颗粒物(PM2.5) μg/m³',
                'data': pm25,
                'borderColor': '#00F0FF',
                'backgroundColor': 'rgba(0, 240, 255, 0.1)',
                'borderWidth': 2,
                'tension': 0.4,
                'fill': True
            },
            {
                'label': '累计臭氧(O₃) μg/m³',
                'data': o3,
                'borderColor': '#FF0080',
                'backgroundColor': 'rgba(255, 0, 128, 0.1)',
                'borderWidth': 2,
                'tension': 0.4,
                'fill': True
            },
            {
                'label': '累计可吸入物(PM10) μg/m³',
                'data': pm10,
                'borderColor': '#39FF14',
                'backgroundColor': 'rgba(57, 255, 20, 0.1)',
                'borderWidth': 2,
                'tension': 0.4,
                'fill': True
            }
        ]
    }

    table_header = ["时间", "每月PM2.5平均(μg/m³)", "每月臭氧平均(μg/m³)", "每月可吸入物平均(μg/m³)",
                    "累计PM2.5", "累计臭氧", "累计可吸入物", "监测站点"]

    table_data = []
    for m, lab, a, b, c, cp, co, ck in zip(months, labels, pm25, o3, pm10, cum_pm25, cum_o3, cum_pm10):
        table_data.append([m, str(a), str(b), str(c), str(cp), str(co), str(ck), top_stations.get(m, '')])

    return chart_data, overview, table_header, table_data


def _parse_numeric_from_str(s):
    """从字符串中提取数值或区间并返回平均值（float）。"""
    if s is None:
        return None
    s = str(s)
    # 去掉百分号等非数字符号（保留 . 和 -）
    # 提取所有浮点数
    nums = re.findall(r"[-+]?\d*\.?\d+", s)
    nums = [float(n) for n in nums] if nums else []
    if not nums:
        return None
    if len(nums) == 1:
        return nums[0]
    # 若是区间取平均
    return sum(nums) / len(nums)


def load_water_monthly_summary(csv_filename='data/宜昌市水质自动站监测情况(0-421).csv'):
    """读取水质监测 CSV 并按月聚合 pH、溶解氧、氨氮 等指标。

    返回 (chart_data, overview, table_header, table_data)
    chart_data.datasets 使用浮点数（保留一位小数），labels 为 ['1月', ...]
    """
    csv_path = os.path.join(os.path.dirname(__file__), csv_filename)
    rows = []
    monthly = {}

    if pd is not None:
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
        except Exception:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
        df.columns = [c.strip() for c in df.columns]
        # 需要的列： bysj (月份), bycbxm(被测参数名), cbznd(值或范围), zdzmc(站点), szxz(水质类别)
        for _, r in df.iterrows():
            month = _parse_bysj_to_ym(r.get('bysj', ''))
            item = str(r.get('bycbxm', '')).strip()
            value = r.get('cbznd', '')
            station = str(r.get('zdzmc', '')).strip() if 'zdzmc' in r.index else str(r.get('stmc', '')).strip()
            sz = str(r.get('szxz', '')).strip() if 'szxz' in r.index else ''
            if not month:
                continue
            if month not in monthly:
                monthly[month] = {'ph': [], 'do': [], 'ammonia': [], 'stations': set(), 'sz_list': []}
            monthly[month]['stations'].add(station)
            if sz:
                monthly[month]['sz_list'].append(sz)
            # 优先用 cbznd 列解析，如果为空则尝试从 bycbxm 中解析括号里的数值
            val = None
            if value and str(value).strip() and str(value).strip() != '--':
                val = _parse_numeric_from_str(value)
            else:
                # 尝试从 bycbxm 中寻找数字
                val = _parse_numeric_from_str(item)
            # 根据参数名分配
            low_item = item.lower()
            if 'ph' in low_item or 'pH' in item or '酸碱' in low_item:
                if val is not None:
                    monthly[month]['ph'].append(val)
            elif '溶解氧' in item or '溶解氧' in low_item or 'do' in low_item:
                if val is not None:
                    monthly[month]['do'].append(val)
            elif '氨氮' in item or 'ammonia' in low_item:
                if val is not None:
                    monthly[month]['ammonia'].append(val)
            else:
                # 其他参数忽略
                pass

    else:
        # fallback csv
        if not os.path.exists(csv_path):
            return {}, {}, [], []
        with open(csv_path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for r in reader:
                month = _parse_bysj_to_ym(r.get('bysj', ''))
                item = str(r.get('bycbxm', '')).strip()
                value = r.get('cbznd', '')
                station = str(r.get('zdzmc', '')).strip() or str(r.get('stmc', '')).strip()
                sz = str(r.get('szxz', '')).strip()
                if not month:
                    continue
                if month not in monthly:
                    monthly[month] = {'ph': [], 'do': [], 'ammonia': [], 'stations': set(), 'sz_list': []}
                monthly[month]['stations'].add(station)
                if sz:
                    monthly[month]['sz_list'].append(sz)
                val = None
                if value and str(value).strip() and str(value).strip() != '--':
                    val = _parse_numeric_from_str(value)
                else:
                    val = _parse_numeric_from_str(item)
                low_item = item.lower()
                if 'ph' in low_item or 'pH' in item or '酸碱' in low_item:
                    if val is not None:
                        monthly[month]['ph'].append(val)
                elif '溶解氧' in item or '溶解氧' in low_item or 'do' in low_item:
                    if val is not None:
                        monthly[month]['do'].append(val)
                elif '氨氮' in item or 'ammonia' in low_item:
                    if val is not None:
                        monthly[month]['ammonia'].append(val)

    # 组织按时间排序的结果
    months = sorted(monthly.keys())
    labels = [f"{int(m.split('-')[1])}月" if '-' in m else m for m in months]
    ph_list = []
    do_list = []
    ammonia_list = []
    stations_list = []
    sz_overview = []
    for m in months:
        rec = monthly[m]
        ph_avg = round(sum(rec['ph']) / len(rec['ph']), 2) if rec['ph'] else None
        do_avg = round(sum(rec['do']) / len(rec['do']), 2) if rec['do'] else None
        am_avg = round(sum(rec['ammonia']) / len(rec['ammonia']), 3) if rec['ammonia'] else None
        ph_list.append(ph_avg if ph_avg is not None else 0)
        do_list.append(do_avg if do_avg is not None else 0)
        ammonia_list.append(am_avg if am_avg is not None else 0)
        stations_list.append(','.join(list(rec['stations'])[:1]))
        # 使用最常见的水质类别
        if rec['sz_list']:
            from collections import Counter
            sz_overview.append(Counter(rec['sz_list']).most_common(1)[0][0])
        else:
            sz_overview.append('')

    # 简单概览
    total_records = sum(len(monthly[m]['stations']) for m in months) if months else 0
    def _avg_nonzero(lst):
        vals = [x for x in lst if x is not None and x != 0]
        return round(sum(vals) / len(vals), 3) if vals else ''

    overview = {
        'recordCount': total_records,
        'monitorPoint': len({s for m in months for s in monthly[m]['stations']}) if months else 0,
        'timeSpan': f"{months[0]} 至 {months[-1]}" if months else '',
        'qualifiedRate': '',
        'avgPh': _avg_nonzero(ph_list),
        'avgDo': _avg_nonzero(do_list),
        'avgAmmonia': _avg_nonzero(ammonia_list)
    }

    chart_data = {
        'labels': labels,
        'datasets': [
            {'label': 'pH值', 'data': ph_list, 'borderColor': '#00F0FF', 'fill': True},
            {'label': '溶解氧(mg/L)', 'data': do_list, 'borderColor': '#39FF14', 'fill': True},
            {'label': '氨氮(mg/L)', 'data': ammonia_list, 'borderColor': '#FF0080', 'fill': True}
        ]
    }

    table_header = ["时间", "pH值", "溶解氧(mg/L)", "氨氮(mg/L)", "水质类别", "监测点"]
    table_data = []
    for m, lab, p, d, a, sz, st in zip(months, labels, ph_list, do_list, ammonia_list, sz_overview, stations_list):
        table_data.append([m, str(p), str(d), str(a), sz or '—', st or '—'])

    return chart_data, overview, table_header, table_data


# === 1️⃣ 静态文件：返回前端页面 ===
@app.route('/home')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/data_center')
def data_center():
    return send_from_directory(app.static_folder, 'data_center.html')

@app.route('/about')
def about():
    return send_from_directory(app.static_folder, 'about.html')

# === 2️⃣ 核心预测指标接口（GDP、失业率、新能源汽车、PM2.5）===
@app.route('/api/core-indicators', methods=['GET'])
def get_core_indicators():
    """返回核心预测指标数据（含趋势图数据）"""
    # 实际项目中可替换为数据库查询/模型计算逻辑
    return jsonify({
        "gdp": {
            "value": 5.8,
            "change": "+0.3%",
            "desc": "高于全国平均水平",
            "labels": ['2020', '2021', '2022', '2023', '2024'],
            "data": [3.8, 4.5, 5.2, 5.5, 5.8]
        },
        "unemployment": {
            "value": 4.2,
            "change": "+0.1%",
            "desc": "较上季度略有上升",
            "labels": ['2020', '2021', '2022', '2023', '2024'],
            "data": [5.1, 4.8, 4.5, 4.1, 4.2]
        },
        "ev": {
            "value": 12.0,
            "change": "+2.3%",
            "desc": "受新产能释放推动",
            "labels": ['2020', '2021', '2022', '2023', '2024'],
            "data": [5.2, 7.8, 8.5, 9.7, 12.0]
        },
        "pm25": {
            "value": 45,
            "change": "-8%",
            "desc": "空气质量持续改善",
            "labels": ['2020', '2021', '2022', '2023', '2024'],
            "data": [68, 62, 55, 49, 45]
        },
        "update_time": datetime.now().strftime("%Y年%m月%d日")
    })


# === 3️⃣ 市州GDP预测接口 ===
@app.route('/api/city-gdp', methods=['GET'])
def get_city_gdp():
    """返回各市州GDP增速预测数据"""
    return jsonify({
        "cities": ['武汉', '襄阳', '宜昌', '荆州', '黄冈', '孝感', '荆门'],
        "actual2023": [6.1, 5.8, 5.5, 5.2, 4.9, 5.0, 5.3],
        "pred2024": [6.5, 6.2, 5.9, 5.6, 5.3, 5.4, 5.7]
    })


# === 4️⃣ 重点产业产值预测接口 ===
@app.route('/api/industries', methods=['GET'])
def get_industries():
    """返回重点产业产值预测数据"""
    return jsonify([
        {"name": "汽车产业", "growth": "+7.2%", "color": "primary", "percent": 72},
        {"name": "光电子产业", "growth": "+15.8%", "color": "secondary", "percent": 85},
        {"name": "生物医药产业", "growth": "+9.5%", "color": "accent", "percent": 68},
        {"name": "装备制造产业", "growth": "+6.3%", "color": "success", "percent": 63}
    ])


# === 5️⃣ 民生商品价格预测接口 ===
@app.route('/api/commodity-prices', methods=['GET'])
def get_commodity_prices():
    """返回主要民生商品价格波动预测数据"""
    months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    return jsonify({
        "months": months,
        "pork": [28, 29, 27, 26, 25, 24, 23, 24, 25, 26, 28, 30],
        "rice": [4.2, 4.2, 4.3, 4.3, 4.4, 4.4, 4.5, 4.5, 4.4, 4.4, 4.3, 4.3],
        "oil": [15.8, 15.9, 16.0, 16.2, 16.3, 16.2, 16.1, 16.0, 15.9, 15.8, 15.8, 15.9]
    })


# === 6️⃣ 教育医疗资源预测接口 ===
@app.route('/api/edu-med-resources', methods=['GET'])
def get_edu_med_resources():
    """返回教育医疗资源供需预测数据"""
    return jsonify({
        "edu_gap": [
            {"city": "武汉市", "gap": "+12,500", "color": "danger", "percent": 75},
            {"city": "襄阳市", "gap": "+3,200", "color": "warning", "percent": 40},
            {"city": "宜昌市", "gap": "-1,800", "color": "success", "percent": 20}
        ],
        "medical_peak": [
            {"name": "冬季呼吸道疾病", "period": "12月-1月", "color": "primary", "percent": 85},
            {"name": "儿童疫苗接种", "period": "9月-10月", "color": "secondary", "percent": 65},
            {"name": "体检高峰期", "period": "3月-4月", "color": "accent", "percent": 50}
        ]
    })


# === 7️⃣ 自定义预测接口（支持参数调整）===
@app.route('/api/custom-prediction', methods=['POST'])
def custom_prediction():
    """
    自定义预测接口：根据前端传入的参数（指标、时间范围、政策补贴）生成预测结果
    请求体格式：{"indicator": "新能源汽车产量", "period": "未来1年", "subsidy": 50}
    """
    params = request.get_json()
    indicator = params.get("indicator", "新能源汽车产量")
    period = params.get("period", "未来1年")
    subsidy = params.get("subsidy", 50)  # 0-100，政策补贴力度

    # 模拟：根据补贴力度调整预测增速（补贴越高，增速越高）
    base_growth = [5.2, 7.8, 8.5, 9.7, 11.2]  # 历史数据
    if period == "未来1年":
        pred_growth = 11.2 + (subsidy - 50) * 0.04  # 补贴每变化10，增速变化0.4%
    elif period == "未来2年":
        pred_growth = 11.2 + (subsidy - 50) * 0.06
    else:  # 未来3年
        pred_growth = 11.2 + (subsidy - 50) * 0.08

    # 生成预测数据
    # 安全地从 `period` 中派生最后一个标签，避免因为没有空格而导致的 IndexError
    import re
    match = re.search(r"\b(20\d{2})\b", period)
    if match:
        final_label = match.group(1)
    else:
        parts = period.split()
        final_label = parts[1] if len(parts) > 1 else period

    labels = ['2020', '2021', '2022', '2023', '2024', final_label]
    history_data = base_growth + [None]
    pred_data = [None, None, None, None] + [11.2, round(pred_growth, 1)]

    return jsonify({
        "indicator": indicator,
        "period": period,
        "subsidy": subsidy,
        "labels": labels,
        "history_data": history_data,
        "pred_data": pred_data,
        "analysis": f"在当前政策补贴力度下，预计{period}{indicator}将保持{round(pred_growth-0.3,1)}-{round(pred_growth+0.3,1)}%的增长速度"
    })


# === 8️⃣ 模型准确率接口 ===
@app.route('/api/model-accuracy', methods=['GET'])
def get_model_accuracy():
    """返回模型历史准确率数据"""
    return jsonify({
        "indicators": ['GDP增速', '失业率', '汽车产业', '光电子产业', '民生商品价格', '空气质量'],
        "accuracy": [92, 88, 90, 95, 85, 89]
    })


# === 9️⃣ 模型说明接口 ===
@app.route('/api/model-info', methods=['GET'])
def get_model_info():
    """返回模型原理、数据源等说明信息"""
    return jsonify({
        "principle": "本预测系统采用融合ARIMA时间序列模型与机器学习梯度提升树的混合建模方法，结合宏观经济指标、政策因素和产业数据，构建多维度预测模型。平均预测误差控制在±3%以内，核心经济指标预测准确率可达90%以上。",
        "data_sources": [
            "湖北省统计局官方发布数据",
            "行业协会及重点企业直报数据",
            "宏观经济与政策数据库",
            "环境监测与城市运行数据"
        ],
        "note": "预测结果基于历史数据和当前可获得的信息，仅供参考。实际发展可能受突发政策变化、自然灾害等不可预见因素影响，使用者应结合多方面信息综合决策。"
    })


# === 历史真实数据接口（最终完整版）===
@app.route('/api/history-data', methods=['POST'])
def get_history_data():
    """
    提供历史真实数据：支持4类数据+3个时间范围
    数据类型：air(空气污染物)、water(水质检测)、river(河流基础)、basin(流域基础)
    时间范围：year2023(2023全年)、half2023(2023下半年)、q42023(2023Q4)
    """
    # 获取前端参数
    params = request.get_json()
    data_type = params.get('dataType', 'air')
    time_range = params.get('timeRange', 'year2023')

    # 初始化输出变量，防止在未匹配任何分支时发生未定义引用（静态默认值）
    chart_data = {}
    overview = {}
    table_header = []
    table_data = []

    # --------------------------
    # 1. 空气污染物数据（累计+每月平均）
    # --------------------------
    if data_type == 'air':
        # 从 CSV 动态加载并聚合
        chart_data_all, overview_all, table_header_all, table_data_all = load_air_monthly_summary()

        # 根据 time_range 筛选 2023 全年 / 下半年 / Q4
        # CSV 中的月份格式为 '2023-01' 等
        def _filter_by_range(idx_list):
            if time_range == 'year2023':
                return [i for i in idx_list if str(i).startswith('2023-')]
            elif time_range == 'half2023':
                return [i for i in idx_list if str(i).startswith('2023-') and int(str(i).split('-')[1]) >= 7]
            else:  # q42023
                return [i for i in idx_list if str(i).startswith('2023-') and int(str(i).split('-')[1]) >= 10]

        # note: chart_data_all keys: 'labels'是像['1月',...], datasets里是月均值
        all_labels = chart_data_all.get('labels', [])
        all_month_keys = []
        # reconstruct month keys from labels assuming year2023; fallback to index strings
        # We have table_data with month key in first column (YYYY-MM), so use that if available
        month_keys = [row[0] for row in table_data_all]
        if not month_keys:
            # fallback: assume 1-12
            month_keys = [f'2023-{i:02d}' for i in range(1, 13)]

        # select indices to keep
        selected_months = _filter_by_range(month_keys)
        # build filtered lists in the same order as month_keys
        sel_indices = [month_keys.index(m) for m in selected_months if m in month_keys]

        def pick(lst):
            return [lst[i] for i in sel_indices] if lst and sel_indices else lst

        # if table_data_all empty -> keep defaults
        if table_data_all:
            # chart datasets were pm25,o3,pm10 in that order
            # map source lists
            # Extract numeric lists from table_data_all
            months = [r[0] for r in table_data_all]
            pm25_list = [int(r[1]) for r in table_data_all]
            o3_list = [int(r[2]) for r in table_data_all]
            pm10_list = [int(r[3]) for r in table_data_all]
            cum_pm25 = [int(r[4]) for r in table_data_all]
            cum_o3 = [int(r[5]) for r in table_data_all]
            cum_pm10 = [int(r[6]) for r in table_data_all]
            stations = [r[7] for r in table_data_all]

            labels = [f"{int(m.split('-')[1])}月" for m in months]
            # apply selection
            labels = [labels[i] for i in sel_indices] if sel_indices else labels
            pm25_list = [pm25_list[i] for i in sel_indices] if sel_indices else pm25_list
            o3_list = [o3_list[i] for i in sel_indices] if sel_indices else o3_list
            pm10_list = [pm10_list[i] for i in sel_indices] if sel_indices else pm10_list
            cum_pm25 = [cum_pm25[i] for i in sel_indices] if sel_indices else cum_pm25
            cum_o3 = [cum_o3[i] for i in sel_indices] if sel_indices else cum_o3
            cum_pm10 = [cum_pm10[i] for i in sel_indices] if sel_indices else cum_pm10
            stations = [stations[i] for i in sel_indices] if sel_indices else stations

            chart_data = {
                "labels": labels,
                "datasets": [
                    {"label": "累计细颗粒物(PM2.5) μg/m³", "data": pm25_list, "borderColor": "#00F0FF",
                     "backgroundColor": "rgba(0, 240, 255, 0.1)", "borderWidth": 2, "tension": 0.4, "fill": True},
                    {"label": "累计臭氧(O₃) μg/m³", "data": o3_list, "borderColor": "#FF0080",
                     "backgroundColor": "rgba(255, 0, 128, 0.1)", "borderWidth": 2, "tension": 0.4, "fill": True},
                    {"label": "累计可吸入物(PM10) μg/m³", "data": pm10_list, "borderColor": "#39FF14",
                     "backgroundColor": "rgba(57, 255, 20, 0.1)", "borderWidth": 2, "tension": 0.4, "fill": True}
                ]
            }

            overview = overview_all or {}
            table_header = table_header_all
            table_data = []
            for m, a, b, c, cp, co, ck, st in zip(months, pm25_list, o3_list, pm10_list, cum_pm25, cum_o3, cum_pm10, stations):
                table_data.append([m, str(a), str(b), str(c), str(cp), str(co), str(ck), st])

        else:
            # 没有表格数据时回退为 CSV 聚合的 chart_data_all
            chart_data = chart_data_all
            overview = overview_all
            table_header = table_header_all
            table_data = table_data_all

    # --------------------------
    # 2. 水质自动检测数据
    # --------------------------
    elif data_type == 'water':
        # 从 CSV 动态加载并按 time_range 过滤
        chart_data_all, overview_all, table_header_all, table_data_all = load_water_monthly_summary()

        def _filter_by_range_months(idx_list):
            # 支持请求中带年份（例如 'year2024'），否则使用数据中第一个可用年份
            m = re.search(r"(20\d{2})", time_range)
            if m:
                target_year = m.group(1)
            else:
                # 从 idx_list 中推断年（以第一个 YYYY-MM 为准）
                if idx_list:
                    first = str(idx_list[0])
                    target_year = first.split('-')[0] if '-' in first else first
                else:
                    target_year = '2023'

            if time_range.startswith('year'):
                return [i for i in idx_list if str(i).startswith(f'{target_year}-')]
            elif time_range.startswith('half'):
                return [i for i in idx_list if str(i).startswith(f'{target_year}-') and int(str(i).split('-')[1]) >= 7]
            else:  # q4
                return [i for i in idx_list if str(i).startswith(f'{target_year}-') and int(str(i).split('-')[1]) >= 10]

        month_keys = [row[0] for row in table_data_all]
        if not month_keys:
            month_keys = sorted([m for m in chart_data_all.get('labels', [])])

        selected_months = _filter_by_range_months(month_keys)
        sel_indices = [month_keys.index(m) for m in selected_months if m in month_keys]

        if table_data_all:
            months = [r[0] for r in table_data_all]
            ph_list = [float(r[1]) for r in table_data_all]
            do_list = [float(r[2]) for r in table_data_all]
            am_list = [float(r[3]) for r in table_data_all]
            sz_list = [r[4] for r in table_data_all]
            stations = [r[5] for r in table_data_all]

            labels = [f"{int(m.split('-')[1])}月" for m in months]
            labels = [labels[i] for i in sel_indices] if sel_indices else labels
            ph_list = [ph_list[i] for i in sel_indices] if sel_indices else ph_list
            do_list = [do_list[i] for i in sel_indices] if sel_indices else do_list
            am_list = [am_list[i] for i in sel_indices] if sel_indices else am_list
            sz_list = [sz_list[i] for i in sel_indices] if sel_indices else sz_list
            stations = [stations[i] for i in sel_indices] if sel_indices else stations

            chart_data = {'labels': labels, 'datasets': [
                {'label': 'pH值', 'data': ph_list, 'borderColor': '#00F0FF', 'fill': True},
                {'label': '溶解氧(mg/L)', 'data': do_list, 'borderColor': '#39FF14', 'fill': True},
                {'label': '氨氮(mg/L)', 'data': am_list, 'borderColor': '#FF0080', 'fill': True}
            ]}

            overview = overview_all or {}
            table_header = table_header_all
            table_data = []
            for m, p, d, a, sz, st in zip(months, ph_list, do_list, am_list, sz_list, stations):
                table_data.append([m, str(p), str(d), str(a), sz, st])
        else:
            chart_data = chart_data_all
            overview = overview_all

    # --------------------------
    # 3. 河流基础信息数据（无时间范围差异，固定展示）
    # --------------------------
    elif data_type == 'river':
        # 河流基础信息无时间趋势，图表展示"流域面积/长度/年均流量"对比
        chart_data = {
            "labels": ["长江湖北段", "汉江湖北段", "清江", "沮漳河", "府河"],
            "datasets": [
                {
                    "label": "流域面积(km²)",
                    "data": [185900, 63200, 16700, 7300, 3200],
                    "borderColor": "#00F0FF",
                    "backgroundColor": "rgba(0, 240, 255, 0.3)",
                    "type": "bar"
                },
                {
                    "label": "河长(km)",
                    "data": [1061, 878, 423, 321, 331],
                    "borderColor": "#FF0080",
                    "backgroundColor": "rgba(255, 0, 128, 0.3)",
                    "type": "bar"
                },
                {
                    "label": "年均流量(m³/s)",
                    "data": [29500, 1710, 460, 120, 85],
                    "borderColor": "#39FF14",
                    "backgroundColor": "rgba(57, 255, 20, 0.3)",
                    "type": "bar"
                }
            ]
        }
        overview = {
            "riverCount": 5,  # 统计河流数
            "totalArea": "276300 km²",  # 总流域面积
            "totalLength": "3014 km",  # 总长度
            "maxFlow": "29500 m³/s (长江湖北段)",
            "minFlow": "85 m³/s (府河)"
        }
        table_header = ["河流名称", "流域面积(km²)", "河长(km)", "年均流量(m³/s)", "发源地", "流经地市", "主要支流"]
        table_data = [
            ["长江湖北段", "185900", "1061", "29500", "青藏高原唐古拉山脉", "宜昌、荆州、武汉、鄂州、黄冈",
             "汉江、清江、沮漳河"],
            ["汉江湖北段", "63200", "878", "1710", "陕西省宁强县嶓冢山", "十堰、襄阳、荆门、孝感、武汉", "丹江、唐河、白河"],
            ["清江", "16700", "423", "460", "湖北省利川市齐岳山", "恩施、宜昌", "忠建河、马水河"],
            ["沮漳河", "7300", "321", "120", "湖北省保康县境", "襄阳、荆州", "沮河、漳河"],
            ["府河", "3200", "331", "85", "湖北省随州市大洪山", "随州、孝感、武汉", "滠水、倒水"]
        ]

    # --------------------------
    # 4. 流域基础信息数据（无时间范围差异，固定展示）
    # --------------------------
    elif data_type == 'basin':
        # 流域基础信息图表：展示各流域"面积占比"饼图
        chart_data = {
            "labels": ["长江流域", "汉江流域", "清江流域", "沮漳河流域", "其他流域"],
            "datasets": [
                {
                    "label": "流域面积占比",
                    "data": [67.3, 22.9, 6.1, 2.6, 1.1],
                    "backgroundColor": [
                        "rgba(0, 240, 255, 0.7)",
                        "rgba(255, 0, 128, 0.7)",
                        "rgba(57, 255, 20, 0.7)",
                        "rgba(255, 221, 0, 0.7)",
                        "rgba(121, 40, 202, 0.7)"
                    ],
                    "borderColor": "#0A0E17",
                    "borderWidth": 2,
                    "type": "pie"
                }
            ]
        }
        overview = {
            "basinCount": 5,  # 流域数量
            "totalArea": "276300 km²",  # 湖北总流域面积
            "mainBasin": "长江流域 (67.3%)",  # 主要流域
            "monitorStation": 32,  # 流域监测站数量
            "protectionRate": "85.2%"  # 流域生态保护率
        }
        table_header = ["流域名称", "面积占比(%)", "覆盖地市", "监测站点数", "生态保护等级", "主要保护对象"]
        table_data = [
            ["长江流域", "67.3", "宜昌、荆州、武汉、鄂州、黄冈、黄石", "16", "一级", "中华鲟、江豚、湿地生态系统"],
            ["汉江流域", "22.9", "十堰、襄阳、荆门、孝感、武汉", "8", "一级", "丹江口水库水质、鸟类栖息地"],
            ["清江流域", "6.1", "恩施、宜昌", "4", "二级", "土家族文化、喀斯特地貌、特有鱼类"],
            ["沮漳河流域", "2.6", "襄阳、荆州", "2", "二级", "湿地植被、农田灌溉水源保护"],
            ["其他流域", "1.1", "随州、咸宁、黄冈", "2", "三级", "区域水资源平衡、农田生态"]
        ]

    # --------------------------
    # 返回统一格式数据给前端
    # --------------------------
    return jsonify({
        "success": True,
        "overview": overview,  # 数据概览
        "chartData": chart_data,  # 图表数据
        "tableHeader": table_header,  # 表格表头
        "tableData": table_data  # 表格内容
    })

if __name__ == '__main__':
    # 确保static目录存在（存放前端index.html）
    if not os.path.exists(app.static_folder):
        os.makedirs(app.static_folder)
    app.run(host='0.0.0.0', port=8080, debug=True)