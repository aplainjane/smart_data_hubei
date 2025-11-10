from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)  # 启用跨域支持


# === 1️⃣ 静态文件：返回前端页面 ===
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


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
    labels = ['2020', '2021', '2022', '2023', '2024', period.split(' ')[1]]
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

    # --------------------------
    # 1. 空气污染物数据（累计+每月平均）
    # --------------------------
    if data_type == 'air':
        if time_range == 'year2023':
            chart_data = {
                "labels": ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
                "datasets": [
                    {
                        "label": "累计细颗粒物(PM2.5) μg/m³",
                        "data": [42, 38, 35, 32, 28, 25, 22, 24, 27, 30, 33, 36],
                        "borderColor": "#00F0FF",
                        "backgroundColor": "rgba(0, 240, 255, 0.1)",
                        "borderWidth": 2,
                        "tension": 0.4,
                        "fill": True
                    },
                    {
                        "label": "累计臭氧(O₃) μg/m³",
                        "data": [110, 105, 98, 120, 135, 140, 150, 145, 130, 115, 108, 102],
                        "borderColor": "#FF0080",
                        "backgroundColor": "rgba(255, 0, 128, 0.1)",
                        "borderWidth": 2,
                        "tension": 0.4,
                        "fill": True
                    },
                    {
                        "label": "累计可吸入物(PM10) μg/m³",
                        "data": [65, 60, 55, 52, 48, 45, 42, 44, 47, 50, 53, 56],
                        "borderColor": "#39FF14",
                        "backgroundColor": "rgba(57, 255, 20, 0.1)",
                        "borderWidth": 2,
                        "tension": 0.4,
                        "fill": True
                    }
                ]
            }
            overview = {
                "recordCount": 365,
                "stationCount": 24,
                "timeSpan": "2023-01-01 至 2023-12-31",
                "avgQuality": "良好",
                "pm25Avg": "31 μg/m³",
                "o3Avg": "121 μg/m³",
                "pm10Avg": "51 μg/m³"
            }
            table_header = ["时间", "每月PM2.5平均(μg/m³)", "每月臭氧平均(μg/m³)", "每月可吸入物平均(μg/m³)",
                            "累计PM2.5", "累计臭氧", "累计可吸入物", "监测站点"]
            table_data = [
                ["2023-01", "42", "110", "65", "42", "110", "65", "武汉光谷站"],
                ["2023-02", "38", "105", "60", "80", "215", "125", "武汉汉口站"],
                ["2023-03", "35", "98", "55", "115", "313", "180", "武汉武昌站"],
                ["2023-04", "32", "120", "52", "147", "433", "232", "襄阳樊城站"],
                ["2023-05", "28", "135", "48", "175", "568", "280", "宜昌西陵站"],
                ["2023-06", "25", "140", "45", "200", "708", "325", "荆州沙市站"],
                ["2023-07", "22", "150", "42", "222", "858", "367", "黄冈黄州站"],
                ["2023-08", "24", "145", "44", "246", "1003", "411", "孝感孝南站"],
                ["2023-09", "27", "130", "47", "273", "1133", "458", "荆门东宝站"],
                ["2023-10", "30", "115", "50", "303", "1248", "508", "十堰茅箭站"],
                ["2023-11", "33", "108", "53", "336", "1356", "561", "鄂州鄂城站"],
                ["2023-12", "36", "102", "56", "372", "1458", "617", "随州曾都站"]
            ]

        elif time_range == 'half2023':  # 2023下半年
            chart_data = {
                "labels": ["7月", "8月", "9月", "10月", "11月", "12月"],
                "datasets": [
                    {"label": "PM2.5", "data": [22, 24, 27, 30, 33, 36], "borderColor": "#00F0FF", "fill": True},
                    {"label": "臭氧", "data": [150, 145, 130, 115, 108, 102], "borderColor": "#FF0080", "fill": True},
                    {"label": "可吸入物", "data": [42, 44, 47, 50, 53, 56], "borderColor": "#39FF14", "fill": True}
                ]
            }
            overview = {"recordCount": 184, "stationCount": 24, "timeSpan": "2023-07-01至2023-12-31",
                        "avgQuality": "良好"}
            table_header = ["时间", "PM2.5平均", "臭氧平均", "可吸入物平均", "累计值", "监测站点"]
            table_data = [
                ["2023-07", "22", "150", "42", "214", "武汉光谷站"],
                ["2023-08", "24", "145", "44", "213", "武汉汉口站"],
                ["2023-09", "27", "130", "47", "204", "武汉武昌站"],
                ["2023-10", "30", "115", "50", "195", "襄阳樊城站"],
                ["2023-11", "33", "108", "53", "194", "宜昌西陵站"],
                ["2023-12", "36", "102", "56", "190", "荆州沙市站"]
            ]

        else:  # 2023 Q4
            chart_data = {
                "labels": ["10月", "11月", "12月"],
                "datasets": [
                    {"label": "PM2.5", "data": [30, 33, 36], "borderColor": "#00F0FF"},
                    {"label": "臭氧", "data": [115, 108, 102], "borderColor": "#FF0080"},
                    {"label": "可吸入物", "data": [50, 53, 56], "borderColor": "#39FF14"}
                ]
            }
            overview = {"recordCount": 92, "stationCount": 24, "timeSpan": "2023-10-01至2023-12-31",
                        "avgQuality": "良好"}
            table_header = ["时间", "PM2.5", "臭氧", "可吸入物", "站点"]
            table_data = [
                ["2023-10", "30", "115", "50", "武汉光谷站"],
                ["2023-11", "33", "108", "53", "武汉汉口站"],
                ["2023-12", "36", "102", "56", "武汉武昌站"]
            ]

    # --------------------------
    # 2. 水质自动检测数据
    # --------------------------
    elif data_type == 'water':
        if time_range == 'year2023':
            chart_data = {
                "labels": ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
                "datasets": [
                    {"label": "pH值", "data": [7.2, 7.3, 7.4, 7.5, 7.6, 7.5, 7.4, 7.3, 7.2, 7.3, 7.4, 7.3],
                     "borderColor": "#00F0FF", "fill": True},
                    {"label": "溶解氧(mg/L)", "data": [8.2, 8.3, 8.5, 8.7, 8.9, 8.8, 8.6, 8.4, 8.3, 8.5, 8.6, 8.4],
                     "borderColor": "#39FF14", "fill": True},
                    {"label": "氨氮(mg/L)",
                     "data": [0.12, 0.13, 0.11, 0.10, 0.09, 0.08, 0.07, 0.09, 0.10, 0.11, 0.12, 0.11],
                     "borderColor": "#FF0080", "fill": True}
                ]
            }
            overview = {
                "recordCount": 365,
                "monitorPoint": 18,  # 监测点位
                "timeSpan": "2023-01-01至2023-12-31",
                "qualifiedRate": "98.2%",  # 合格率
                "avgPh": "7.35",
                "avgDo": "8.5 mg/L",
                "avgAmmonia": "0.10 mg/L"
            }
            table_header = ["时间", "pH值", "溶解氧(mg/L)", "氨氮(mg/L)", "高锰酸盐指数(mg/L)", "总磷(mg/L)",
                            "水质类别", "监测点位"]
            table_data = [
                ["2023-01", "7.2", "8.2", "0.12", "2.1", "0.08", "Ⅱ类", "长江武汉段"],
                ["2023-02", "7.3", "8.3", "0.13", "2.2", "0.09", "Ⅱ类", "长江宜昌段"],
                ["2023-03", "7.4", "8.5", "0.11", "2.0", "0.07", "Ⅱ类", "汉江襄阳段"],
                ["2023-04", "7.5", "8.7", "0.10", "1.9", "0.06", "Ⅰ类", "东湖武汉段"],
                ["2023-05", "7.6", "8.9", "0.09", "1.8", "0.05", "Ⅰ类", "梁子湖鄂州段"],
                ["2023-06", "7.5", "8.8", "0.08", "1.7", "0.04", "Ⅰ类", "洪湖荆州段"],
                ["2023-07", "7.4", "8.6", "0.07", "1.6", "0.03", "Ⅰ类", "丹江口水库"],
                ["2023-08", "7.3", "8.4", "0.09", "1.7", "0.04", "Ⅱ类", "清江宜昌段"],
                ["2023-09", "7.2", "8.3", "0.10", "1.8", "0.05", "Ⅱ类", "漳河荆门段"],
                ["2023-10", "7.3", "8.5", "0.11", "1.9", "0.06", "Ⅱ类", "白莲河黄冈段"],
                ["2023-11", "7.4", "8.6", "0.12", "2.0", "0.07", "Ⅱ类", "富水咸宁段"],
                ["2023-12", "7.3", "8.4", "0.11", "2.1", "0.08", "Ⅱ类", "陆水赤壁段"]
            ]

        elif time_range == 'half2023':
            chart_data = {
                "labels": ["7月", "8月", "9月", "10月", "11月", "12月"],
                "datasets": [
                    {"label": "pH值", "data": [7.4, 7.3, 7.2, 7.3, 7.4, 7.3], "borderColor": "#00F0FF"},
                    {"label": "溶解氧", "data": [8.6, 8.4, 8.3, 8.5, 8.6, 8.4], "borderColor": "#39FF14"},
                    {"label": "氨氮", "data": [0.07, 0.09, 0.10, 0.11, 0.12, 0.11], "borderColor": "#FF0080"}
                ]
            }
            overview = {"recordCount": 184, "monitorPoint": 18, "qualifiedRate": "99.1%",
                        "timeSpan": "2023-07-01至2023-12-31"}
            table_header = ["时间", "pH值", "溶解氧", "氨氮", "水质类别", "监测点"]
            table_data = [
                ["2023-07", "7.4", "8.6", "0.07", "Ⅰ类", "长江武汉段"],
                ["2023-08", "7.3", "8.4", "0.09", "Ⅱ类", "长江宜昌段"],
                ["2023-09", "7.2", "8.3", "0.10", "Ⅱ类", "汉江襄阳段"],
                ["2023-10", "7.3", "8.5", "0.11", "Ⅱ类", "东湖武汉段"],
                ["2023-11", "7.4", "8.6", "0.12", "Ⅱ类", "梁子湖鄂州段"],
                ["2023-12", "7.3", "8.4", "0.11", "Ⅱ类", "洪湖荆州段"]
            ]

        else:  # Q4
            chart_data = {
                "labels": ["10月", "11月", "12月"],
                "datasets": [
                    {"label": "pH值", "data": [7.3, 7.4, 7.3], "borderColor": "#00F0FF"},
                    {"label": "溶解氧", "data": [8.5, 8.6, 8.4], "borderColor": "#39FF14"},
                    {"label": "氨氮", "data": [0.11, 0.12, 0.11], "borderColor": "#FF0080"}
                ]
            }
            overview = {"recordCount": 92, "monitorPoint": 18, "qualifiedRate": "98.9%",
                        "timeSpan": "2023-10-01至2023-12-31"}
            table_header = ["时间", "pH值", "溶解氧", "氨氮", "水质类别", "监测点"]
            table_data = [
                ["2023-10", "7.3", "8.5", "0.11", "Ⅱ类", "长江武汉段"],
                ["2023-11", "7.4", "8.6", "0.12", "Ⅱ类", "长江宜昌段"],
                ["2023-12", "7.3", "8.4", "0.11", "Ⅱ类", "汉江襄阳段"]
            ]

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
    app.run(host='0.0.0.0', port=5000, debug=True)