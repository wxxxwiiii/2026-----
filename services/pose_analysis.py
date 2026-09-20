"""人体姿态分析：MediaPipe 33 关键点 + 关节角度 + 力矩估算 + 关键帧选取。

依赖说明：本模块只在「MediaPipe 基础模式」下使用，需要先安装 mediapipe：
    pip install mediapipe
若未安装，MP_AVAILABLE 为 False，调用 analyze_pose 会抛出明确异常，由上层回退到纯文字诊断。
"""
import json
import math

import cv2
import numpy as np

try:
    import mediapipe as mp
    MP_AVAILABLE = True
except Exception:
    MP_AVAILABLE = False

# De Leva 肢体段占身高比例（用于按身高估算肢体段长度与质量）
SEGMENT = {'upper_arm': 0.186, 'forearm': 0.146, 'thigh': 0.245, 'shank': 0.246}

# 关节角度定义：近端、顶点、远端（MediaPipe 关键点索引）
JOINTS = {
    '肩关节': (11, 13, 15),   # 髋→肩→肘
    '肘关节': (13, 15, 17),   # 肩→肘→腕
    '髋关节': (11, 23, 25),   # 肩→髋→膝
    '膝关节': (23, 25, 27),   # 髋→膝→踝
    '踝关节': (25, 27, 29),   # 膝→踝→足跟
}

# 标准角度（教学参考值，用于偏差计算）
STD_ANGLE = {'肩关节': 160, '肘关节': 165, '髋关节': 120, '膝关节': 130, '踝关节': 90}


def joint_angle(a, b, c):
    """三点向量夹角（近端 a、顶点 b、远端 c），返回度数。"""
    ba = np.array(a) - np.array(b)
    bc = np.array(c) - np.array(b)
    denom = np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8
    cos = float(np.clip(np.dot(ba, bc) / denom, -1.0, 1.0))
    return math.degrees(math.acos(cos))


def joint_torque(mass_kg, r_m, alpha, phi):
    """简化单刚体逆动力学：τ = I·α + m·g·r·sin(φ)，I = m·r²。"""
    inertia = mass_kg * r_m ** 2
    return inertia * alpha + mass_kg * 9.81 * r_m * math.sin(phi)


def analyze_pose(video_path, height_m=1.75, weight_kg=70.0, max_frames=30):
    """MediaPipe 基础分析：逐帧提取关键点，计算关节角度/力矩，选取关键帧。

    返回 (pose_data, metrics_data, key_frames)。pose_data 为各帧 33 关键点（归一化坐标）。
    """
    if not MP_AVAILABLE:
        raise RuntimeError('MediaPipe 未安装，无法进行骨骼分析（请先 pip install mediapipe）')

    mp_pose = mp.solutions.pose
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError('视频无法打开')
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        cap.release()
        raise ValueError('视频无帧（编码可能不被支持）')

    n = min(max_frames, total)
    indices = sorted(set(int(total * (i + 0.5) / n) for i in range(n)))

    pose_data = []
    angle_series = {j: [] for j in JOINTS}
    wrist_series = []  # (frame_index, wrist_xy) 用于速度峰值关键帧

    with mp_pose.Pose(static_image_mode=True, model_complexity=1) as pose:
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = pose.process(rgb)
            if not res.pose_landmarks:
                pose_data.append({'frame': idx, 'landmarks': []})
                continue
            lm = res.pose_landmarks.landmark
            pts = [{'x': p.x, 'y': p.y, 'z': p.z, 'v': p.visibility} for p in lm]
            pose_data.append({'frame': idx, 'landmarks': pts})
            wrist_series.append((idx, (lm[15].x, lm[15].y), lm[15].visibility))
            for jname, (a, b, c) in JOINTS.items():
                if all(lm[k].visibility > 0.5 for k in (a, b, c)):
                    ang = joint_angle((lm[a].x, lm[a].y), (lm[b].x, lm[b].y), (lm[c].x, lm[c].y))
                    angle_series[jname].append((idx, ang))
    cap.release()

    if not any(angle_series.values()):
        raise ValueError('未检测到人体关键点')

    key_frames = _select_key_frames(pose_data, angle_series, wrist_series)
    metrics_data = _compute_metrics(angle_series, height_m, weight_kg)
    return pose_data, metrics_data, key_frames


def _select_key_frames(pose_data, angle_series, wrist_series, max_keys=5):
    """关键帧：手腕速度峰值（击球/发力瞬间）+ 膝屈曲最大（下蹲/起跳）+ 均匀补帧。"""
    picked = {}
    # 手腕速度峰值
    if len(wrist_series) >= 2:
        speeds = []
        for i in range(1, len(wrist_series)):
            f0, p0, v0 = wrist_series[i - 1]
            f1, p1, v1 = wrist_series[i]
            if v0 > 0.5 and v1 > 0.5:
                speeds.append((f1, math.hypot(p1[0] - p0[0], p1[1] - p0[1])))
        if speeds:
            peak = max(speeds, key=lambda x: x[1])
            picked[peak[0]] = '发力/击球瞬间'
    # 膝关节屈曲最大（角度最小）
    if angle_series.get('膝关节'):
        min_knee = min(angle_series['膝关节'], key=lambda x: x[1])
        picked[min_knee[0]] = '下蹲/起跳'
    # 均匀补帧
    all_frames = [p['frame'] for p in pose_data if p['landmarks']]
    if all_frames:
        step = max(1, len(all_frames) // max_keys)
        for f in all_frames[::step][:max_keys]:
            picked.setdefault(f, '补充帧')

    result = []
    for fid, label in list(picked.items())[:max_keys]:
        angles = {j: next((a for f, a in angle_series[j] if f == fid), None) for j in JOINTS}
        result.append({'frame': fid, 'label': label, 'angles': angles})
    return result


def _compute_metrics(angle_series, height_m, weight_kg):
    """关节角度统计 + 力矩估算。"""
    metrics = {}
    for jname, series in angle_series.items():
        angles = [a for _, a in series]
        if not angles:
            continue
        # 滑动平均平滑
        smoothed = _moving_average(angles, 3)
        avg = float(np.mean(smoothed))
        # 角加速度由角度序列二阶差分得到（单位帧）
        alpha = 0.0
        if len(smoothed) >= 3:
            alpha = float(np.mean(np.abs(np.diff(np.diff(smoothed)))))
        # 肢体段长度：上肢用前臂，下肢用大腿
        ratio = SEGMENT['forearm'] if '肘' in jname else SEGMENT['thigh']
        r = height_m * ratio
        mass = weight_kg * 0.05  # 近似肢体段质量
        torque = joint_torque(mass, r, alpha, math.radians(avg))
        metrics[jname] = {
            'avg_angle': round(avg, 1),
            'std_angle': STD_ANGLE.get(jname, 90),
            'dev': round(avg - STD_ANGLE.get(jname, 90), 1),
            'avg_torque': round(torque, 3),
        }
    return metrics


def _moving_average(data, window=3):
    if len(data) < window:
        return data
    return [float(np.mean(data[i:i + window])) for i in range(len(data) - window + 1)]


def summarize_metrics(records):
    """跨记录按关节聚合：平均角度/平均偏差/平均力矩/次数/严重度。"""
    agg = {}
    for r in records:
        metrics = json.loads(r.metrics_data or '{}')
        for jname, m in metrics.items():
            d = agg.setdefault(jname, {'angles': [], 'torques': [], 'count': 0})
            d['angles'].append(m.get('avg_angle', 0))
            d['torques'].append(m.get('avg_torque', 0))
            d['count'] += 1
    summary = []
    for jname, d in agg.items():
        avg = round(np.mean(d['angles']), 1)
        dev = round(avg - STD_ANGLE.get(jname, 90), 1)
        tq = round(np.mean(d['torques']), 3)
        sev = '高' if abs(dev) >= 15 else ('中' if abs(dev) >= 8 else '低')
        summary.append({'joint': jname, 'avg_angle': avg, 'std_angle': STD_ANGLE.get(jname, 90),
                        'avg_dev': dev, 'avg_torque': tq, 'count': d['count'], 'severity': sev})
    return summary
