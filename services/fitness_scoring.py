"""体质健康评分：内置《国家学生体质健康标准》大学组评分。

说明：当前为演示用简化评分表（大学组，男/女各一套，关键分值点 + 线性插值），
可后续替换为官方完整数据或改为从 fitness_standards 表读取。"""

# 各项目权重（%）
WEIGHTS = {'bmi': 15, 'vital': 15, 'run50': 20, 'sitreach': 10,
           'jump': 10, 'strength': 10, 'endurance': 20}

# 评分表：item -> gender -> 大学组 -> {score: value}
# 时间型项目（50米/耐力跑）数值越小越好；其余数值越大越好（由插值方向自动处理）。
STANDARDS = {
    'vital': {  # 肺活量 ml
        '男': {'大学组': {100: 5040, 90: 4800, 80: 4550, 70: 4300, 60: 4000, 50: 3700, 40: 3400, 30: 3100, 20: 2800, 10: 2500, 0: 2300}},
        '女': {'大学组': {100: 3400, 90: 3200, 80: 3000, 70: 2800, 60: 2600, 50: 2400, 40: 2200, 30: 2000, 20: 1800, 10: 1600, 0: 1500}},
    },
    'run50': {  # 50米 秒
        '男': {'大学组': {100: 6.7, 90: 6.9, 80: 7.1, 70: 7.3, 60: 7.5, 50: 7.7, 40: 7.9, 30: 8.1, 20: 8.3, 10: 8.5, 0: 8.7}},
        '女': {'大学组': {100: 7.5, 90: 7.7, 80: 7.9, 70: 8.1, 60: 8.3, 50: 8.5, 40: 8.7, 30: 8.9, 20: 9.1, 10: 9.3, 0: 9.5}},
    },
    'sitreach': {  # 坐位体前屈 cm
        '男': {'大学组': {100: 24.9, 90: 22, 80: 19, 70: 16, 60: 12, 50: 8, 40: 4, 30: 0, 20: -4, 10: -8, 0: -10}},
        '女': {'大学组': {100: 25.8, 90: 23, 80: 20, 70: 17, 60: 13, 50: 9, 40: 5, 30: 1, 20: -3, 10: -7, 0: -9}},
    },
    'jump': {  # 立定跳远 cm
        '男': {'大学组': {100: 273, 90: 263, 80: 253, 70: 243, 60: 233, 50: 223, 40: 213, 30: 203, 20: 193, 10: 183, 0: 173}},
        '女': {'大学组': {100: 207, 90: 199, 80: 191, 70: 183, 60: 175, 50: 167, 40: 159, 30: 151, 20: 143, 10: 135, 0: 127}},
    },
    'strength': {  # 引体向上（男）/ 仰卧起坐（女）个
        '男': {'大学组': {100: 20, 90: 17, 80: 15, 70: 13, 60: 11, 50: 9, 40: 7, 30: 5, 20: 4, 10: 3, 0: 2}},
        '女': {'大学组': {100: 56, 90: 52, 80: 48, 70: 44, 60: 40, 50: 36, 40: 32, 30: 28, 20: 24, 10: 20, 0: 16}},
    },
    'endurance': {  # 1000米（男）/ 800米（女）秒
        '男': {'大学组': {100: 197, 90: 207, 80: 217, 70: 227, 60: 240, 50: 253, 40: 266, 30: 279, 20: 292, 10: 305, 0: 318}},
        '女': {'大学组': {100: 198, 90: 208, 80: 218, 70: 228, 60: 240, 50: 252, 40: 264, 30: 276, 20: 288, 10: 300, 0: 312}},
    },
}


def bmi_value(height_cm, weight_kg):
    """计算 BMI，保留一位小数；缺身高/体重返回 None。"""
    if not height_cm or not weight_kg:
        return None
    return round(weight_kg / ((height_cm / 100.0) ** 2), 1)


def bmi_score(bmi):
    """体重指数单项分。正常 100，低体重/超重 80，肥胖 60。"""
    if bmi is None:
        return 0.0
    if 17.9 <= bmi <= 23.9:
        return 100.0
    if bmi <= 17.8 or (24.0 <= bmi <= 27.9):
        return 80.0
    return 60.0


def _interp_score(table, value):
    """按 value 在评分表相邻两点间线性插值；越界钳制。"""
    if value is None:
        return 0.0
    pts = sorted(table.items(), key=lambda kv: kv[1])  # 按 value 升序
    values = [p[1] for p in pts]
    scores = [p[0] for p in pts]
    if value <= values[0]:
        return float(scores[0])
    if value >= values[-1]:
        return float(scores[-1])
    for i in range(len(pts) - 1):
        v0, s0 = values[i], scores[i]
        v1, s1 = values[i + 1], scores[i + 1]
        if v0 <= value <= v1:
            if v1 == v0:
                return float(s0)
            return s0 + (value - v0) / (v1 - v0) * (s1 - s0)
    return float(scores[-1])


def calculate(gender, measurements):
    """根据性别与原始测量值计算各项标准分、总分与等级。

    measurements 键：height_cm, weight_kg, bmi（可直接传 BMI）, vital_capacity,
    run_50m, sit_and_reach, standing_long_jump, pull_up, sit_up, run_1000m, run_800m。
    返回 dict：bmi, bmi_score, vital_score, run50_score, sitreach_score,
    jump_score, strength_score, endurance_score, total_score, grade。
    """
    bmi = measurements.get('bmi')
    if bmi is None:
        bmi = bmi_value(measurements.get('height_cm'), measurements.get('weight_kg'))
    bmi_s = bmi_score(bmi)

    t = STANDARDS
    vital_s = _interp_score(t['vital'][gender]['大学组'], measurements.get('vital_capacity'))
    run50_s = _interp_score(t['run50'][gender]['大学组'], measurements.get('run_50m'))
    sitreach_s = _interp_score(t['sitreach'][gender]['大学组'], measurements.get('sit_and_reach'))
    jump_s = _interp_score(t['jump'][gender]['大学组'], measurements.get('standing_long_jump'))
    strength_raw = measurements.get('pull_up') if gender == '男' else measurements.get('sit_up')
    strength_s = _interp_score(t['strength'][gender]['大学组'], strength_raw)
    endurance_raw = measurements.get('run_1000m') if gender == '男' else measurements.get('run_800m')
    endurance_s = _interp_score(t['endurance'][gender]['大学组'], endurance_raw)

    total = (bmi_s * 15 + vital_s * 15 + run50_s * 20 + sitreach_s * 10 +
             jump_s * 10 + strength_s * 10 + endurance_s * 20) / 100.0
    total = round(total, 1)
    grade = '优秀' if total >= 90 else ('良好' if total >= 80 else ('及格' if total >= 60 else '不及格'))

    return {
        'bmi': bmi, 'bmi_score': bmi_s, 'vital_score': vital_s, 'run50_score': run50_s,
        'sitreach_score': sitreach_s, 'jump_score': jump_s, 'strength_score': strength_s,
        'endurance_score': endurance_s, 'total_score': total, 'grade': grade,
    }
