
import pandas as pd
import numpy as np
import itertools
from scipy.stats import norm

def parse_chinese_grade(grade_str):
    """Convert '二十四档' to 24."""
    if pd.isna(grade_str): return 0
    grade_str = str(grade_str).replace('档', '').strip()
    cn_nums = {'一':1, '二':2, '三':3, '四':4, '五':5, '六':6, '七':7, '八':8, '九':9, '十':10}
    if grade_str in cn_nums: return cn_nums[grade_str]
    if grade_str.startswith('十') and len(grade_str) > 1: return 10 + cn_nums.get(grade_str[1], 0)
    if grade_str == '二十': return 20
    if grade_str.startswith('二十') and len(grade_str) > 2: return 20 + cn_nums.get(grade_str[2], 0)
    if grade_str == '三十': return 30
    try: return int(grade_str)
    except: return 0

def num_to_cn(n):
    n = int(n)
    cn_map = {1:'一', 2:'二', 3:'三', 4:'四', 5:'五', 6:'六', 7:'七', 8:'八', 9:'九', 10:'十'}
    if n <= 10: return cn_map[n] + '档'
    if n < 20: return '十' + cn_map[n-10] + '档'
    if n == 20: return '二十档'
    if n < 30: return '二十' + cn_map[n-20] + '档'
    if n == 30: return '三十档'
    return str(n)

def calculate_metrics(df):
    """Calculate all required scoring columns."""
    df = df.copy()
    
    # 1. Purchase Amount Rank (Higher value = Rank 1)
    df['卷烟购进金额指标排名'] = df['卷烟购进金额指标值'].rank(ascending=False, method='min')
    
    # 2. Purchase Amount Score
    total_customers = len(df)
    df['卷烟购进金额得分'] = (2 - df['卷烟购进金额指标排名'] / total_customers) * 40
    
    # 3. Credit Score
    def get_credit_score(grade):
        if pd.isna(grade): return 0
        grade = str(grade).strip().upper()
        if grade in ['AAA', 'AA', 'A']: return 6
        elif grade == 'B': return 4
        elif grade == 'C': return 2
        elif grade == 'D': return 0
        return 0
    df['信用等级指标得分'] = df['信用等级指标值'].apply(get_credit_score)
    
    # 4. Trade Data Score
    def get_trade_score(val):
        if pd.isna(val): return 0
        if 98 <= val < 101: return 5
        if 95 <= val < 98: return 4
        if 90 <= val < 95: return 3
        if 85 <= val < 90: return 2
        if 60 <= val < 85: return 1
        if 0 <= val < 60: return 1
        if val >= 101: return 5
        return 0
    df['交易数据指标得分'] = df['交易数据指标值'].apply(get_trade_score)
    
    # 5. Non-Purchase Score
    non_purchase_cols = [
        '信用等级指标得分', '专柜陈列得分', '摆放规则得分', '破损褪色得分', 
        '主题陈列得分', '明码标价得分', '交易数据指标得分', '消费环境得分'
    ]
    for col in non_purchase_cols:
        if col not in df.columns: df[col] = 0
        df[col] = df[col].fillna(0)
    df['卷烟非购进金额得分'] = df[non_purchase_cols].sum(axis=1)
    
    # 6. Total Score & 7. Rank
    df['总分'] = df['卷烟购进金额得分'] + df['卷烟非购进金额得分']
    df['总分排名'] = df['总分'].rank(ascending=False, method='min')
    
    # 8. District
    df['所属区县'] = df['营销线路'].astype(str).str[:2]
    
    # Pre-calculate old grade num
    df['原档位_Num'] = df['原档位'].apply(parse_chinese_grade)
    
    return df

def assign_grades_by_percentiles(df, shifts, skew=False):
    """
    Assign grades 1-30 based on Total Score and boundary shifts.
    Uses Normal Distribution (centered at 15) to distribute counts within blocks if skew=True.
    """
    df = df.sort_values(by=['总分', '卷烟购进金额指标值'], ascending=[False, False]).copy()
    total = len(df)
    
    base_cuts = {'A': 0.09, 'B': 0.27, 'C': 0.50, 'D': 0.73}
    
    cut_A = base_cuts['A'] + shifts.get('A', 0)
    cut_B = base_cuts['B'] + shifts.get('B', 0)
    cut_C = base_cuts['C'] + shifts.get('C', 0)
    cut_D = base_cuts['D'] + shifts.get('D', 0)
    
    idx_A = int(round(total * cut_A))
    idx_B = int(round(total * cut_B))
    idx_C = int(round(total * cut_C))
    idx_D = int(round(total * cut_D))
    
    idx_B = max(idx_A, idx_B)
    idx_C = max(idx_B, idx_C)
    idx_D = max(idx_C, idx_D)
    
    grades = np.zeros(total, dtype=int)
    
    # Pre-calculate normal weights for grades 1-30
    # Mean = 15.5, Std Dev approx 7 (covers range 1-30 nicely within +/- 2ish sigma)
    # We want peak at 15.
    x = np.arange(1, 31)
    # Using mean=15 to satisfy "15档的人数最多"
    pdf = norm.pdf(x, loc=15, scale=7)
    pdf_weights = dict(zip(x, pdf))

    def distribute_grades(start_idx, end_idx, start_grade, end_grade):
        count = end_idx - start_idx
        if count <= 0: return
        num_grades = start_grade - end_grade + 1
        
        # Determine grades in this block
        block_grades = list(range(end_grade, start_grade + 1))[::-1] # e.g. [30, 29, 28, 27, 26]
        
        if not skew:
            # Uniform distribution
            base = count // num_grades
            remainder = count % num_grades
            current_idx = start_idx
            for i, g in enumerate(block_grades):
                n = base + (1 if i < remainder else 0)
                grades[current_idx : current_idx + n] = g
                current_idx += n
        else:
            # Normal Distribution Weighted
            # Get weights for grades in this block
            weights = np.array([pdf_weights[g] for g in block_grades])
            weights = weights / weights.sum() # Normalize
            
            # Calculate counts
            counts = np.floor(weights * count).astype(int)
            
            # Ensure every grade gets at least 1 if possible
            if count >= num_grades:
                # Find indices where count is 0
                zero_indices = np.where(counts == 0)[0]
                # We need to take from somewhere to give to these
                # Actually, simpler: just use remainder distribution logic to fill holes first?
                # No, floor might be 0 if weight is small.
                pass 
                # Let's trust the remainder logic below to fill up holes if remainder is large enough
                # Or force it:
                # If we have enough count, ensure min=1
            
            # Distribute remainder
            current_sum = counts.sum()
            remainder = count - current_sum
            
            # Add remainder to grades with highest decimal part (largest error)
            # Or just add to the highest weights
            # Simple approach: add 1 to the first 'remainder' grades sorted by weight desc
            if remainder > 0:
                # Add to the ones with highest original weight to maintain shape
                # indices = np.argsort(weights)[::-1]
                # Better: Add to the middle of the block?
                # Let's add to the indices that have the highest fractional part if we calculated floats
                exact_counts = weights * count
                diffs = exact_counts - counts
                indices = np.argsort(diffs)[::-1]
                for i in range(remainder):
                    counts[indices[i]] += 1
            
            # Assign
            current_idx = start_idx
            for i, g in enumerate(block_grades):
                n = counts[i]
                if n > 0:
                    grades[current_idx : current_idx + n] = g
                    current_idx += n
            
    distribute_grades(0, idx_A, 30, 26)
    distribute_grades(idx_A, idx_B, 25, 21)
    distribute_grades(idx_B, idx_C, 20, 16)
    distribute_grades(idx_C, idx_D, 15, 11)
    distribute_grades(idx_D, total, 10, 1)
    
    df['新档位_Num'] = grades
    
    # Add Chinese Grade Name
    df['新档位'] = df['新档位_Num'].apply(num_to_cn)
    
    return df

def assign_grades_by_thresholds(df, thresholds):
    """
    Assign grades based on manual score thresholds.
    thresholds: dict {grade: min_score}
    e.g. {30: 98.5, 29: 97.0 ...}
    """
    df = df.copy()
    grades = np.zeros(len(df), dtype=int)
    
    # Set default 1
    grades[:] = 1
    
    # Ensure keys are int
    safe_thresh = {int(k): float(v) for k, v in thresholds.items()}
    
    # For each grade from 2 to 30, update if score >= thresh
    for g in range(2, 31):
        if g in safe_thresh:
            mask = df['总分'] >= safe_thresh[g]
            grades[mask] = g
            
    df['新档位_Num'] = grades
    df['新档位'] = df['新档位_Num'].apply(num_to_cn)
    return df

def optimize_grading(df):
    """Run optimization to find best shifts."""
    # Expanded grid search to ensure we find a solution
    options = [-0.001, -0.0009, -0.0005, 0, 0.0005, 0.0009, 0.001]
    
    best_score = -float('inf')
    best_df = None
    best_metrics = {}
    
    for shifts_tuple in itertools.product(options, repeat=4):
        shifts = {'A': shifts_tuple[0], 'B': shifts_tuple[1], 'C': shifts_tuple[2], 'D': shifts_tuple[3]}
        temp_df = assign_grades_by_percentiles(df, shifts, skew=True)
        
        # Fast metric calc
        grade_counts = temp_df['新档位_Num'].value_counts(normalize=True)
        min_pct = grade_counts.min() if not grade_counts.empty else 0
        
        upgrades = temp_df['新档位_Num'] > temp_df['原档位_Num']
        downgrades = temp_df['新档位_Num'] < temp_df['原档位_Num']
        n_up = upgrades.sum()
        n_down = downgrades.sum()
        
        # Check Big Rules
        total_cust = len(temp_df)
        def check_pct(start, end, target):
            c = ((temp_df['新档位_Num'] >= start) & (temp_df['新档位_Num'] <= end)).sum()
            p = c / total_cust
            return (target - 0.001) <= p <= (target + 0.001)
            
        rule_big = (check_pct(26,30,0.09) and check_pct(21,25,0.18) and 
                    check_pct(16,20,0.23) and check_pct(11,15,0.23) and 
                    check_pct(1,10,0.27))
                    
        rule_a_pass = min_pct >= 0.01
        rule_a_hard = grade_counts.min() > 0 if not grade_counts.empty else False
        
        # Small Rule B: Upgrade >= Downgrade (CITY WIDE)
        # Requirement: "升档人数大于等于降档人数必须满足"
        rule_b_pass = n_up >= n_down
        
        # Small Rule C: Variance Minimization (Check & Optimization Goal)
        # User said: "C and D can be ignored". We will keep variance as a very weak tie-breaker.
        total_variance = 0
        for g in range(1, 31):
            g_subset = temp_df[temp_df['新档位_Num'] == g]
            if len(g_subset) > 1:
                var = g_subset['卷烟购进金额指标值'].var()
                total_variance += var
        
        # Small Rule D: Weighted Purchase Index Change
        # User said: "C and D can be ignored".
        weighted_sum_old = (temp_df['原档位_Num'] * temp_df['卷烟购进金额指标值']).sum()
        weighted_sum_new = (temp_df['新档位_Num'] * temp_df['卷烟购进金额指标值']).sum()
        
        if weighted_sum_old != 0:
            change_rate = (weighted_sum_new - weighted_sum_old) / weighted_sum_old
        else:
            change_rate = 0
            
        rule_d_pass = -0.05 <= change_rate <= 0.05
        
        # Small Rule E: Normal Distribution Check (Peak at 15, smooth tails)
        # We can calculate the correlation between actual counts and ideal PDF counts
        actual_counts = temp_df['新档位_Num'].value_counts().sort_index()
        # Ensure all grades 1-30 are present
        actual_vector = np.array([actual_counts.get(i, 0) for i in range(1, 31)])
        
        # Ideal vector (already computed weights)
        x_range = np.arange(1, 31)
        pdf_ideal = norm.pdf(x_range, loc=15, scale=7)
        # Correlation
        if np.std(actual_vector) > 0 and np.std(pdf_ideal) > 0:
            corr = np.corrcoef(actual_vector, pdf_ideal)[0, 1]
        else:
            corr = 0
            
        rule_e_pass = corr > 0.8 # Threshold for "Good" distribution
        
        # Scoring
        score = 0
        
        # 1. Mandatory Rules (Must satisfy)
        # Big Rules (Percentages)
        if rule_big: score += 1000000000
        # Rule B: Up >= Down
        if rule_b_pass: score += 1000000000
        # Rule A Hard: Min count > 0
        if rule_a_hard: score += 1000000000
        
        # 2. Priority Rules (Try to satisfy)
        # Rule A Soft: Min count >= 1%
        if rule_a_pass: score += 5000000
        # Rule E: Normal Distribution
        if rule_e_pass: score += 5000000
        
        # 3. Optimization Objectives
        # Maximize correlation (Rule E fine-tuning)
        score += (corr * 1000000)
        
        # Maximize Upgrade margin (Rule B fine-tuning)
        score += (n_up - n_down)
        
        # Variance: Tie-breaker only (very small weight), or ignored.
        # score -= (total_variance / 1000) 
        
        # Penalize if Mandatory Rules are not met
        if not (rule_big and rule_b_pass and rule_a_hard):
             score -= 10000000000 # Make it impossible to pick
             
        if score > best_score:
            best_score = score
            best_df = temp_df
            best_metrics = {
                'min_pct': min_pct, 'n_up': int(n_up), 'n_down': int(n_down),
                'rule_b_pass': bool(rule_b_pass), 'rule_big': bool(rule_big),
                'rule_d_pass': bool(rule_d_pass),
                'change_rate': change_rate,
                'total_variance': total_variance,
                'corr': corr
            }
            
    return best_df, best_metrics

def generate_export_data(df, metrics=None):
    """
    Generate the 3 DataFrames for the requested Excel format:
    1. 明细表
    2. 汇总表
    3. 规则校验
    """
    # --- 1. 明细表 ---
    # Required columns mapping/creation
    # '档位编码' -> assume it is the numeric grade
    df['档位编码'] = df['新档位_Num']
    
    # Ensure all required columns exist, fill with 0/empty if not
    required_cols = [
        '许可证号', '原档位', '新档位', '档位编码', 
        '卷烟购进金额指标值', '卷烟购进金额指标排名', 
        '信用等级指标值', '信用等级指标得分', 
        '专柜陈列得分', '摆放规则得分', '破损褪色得分', 
        '主题陈列得分', '明码标价得分', 
        '交易数据指标值', '交易数据指标得分', 
        '消费环境得分', '营销线路', '所属区县', 
        '卷烟购进金额得分', '卷烟非购进金额得分', 
        '总分', '总分排名'
    ]
    
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0 if '得分' in col or '值' in col or '排名' in col else ''
            
    detail_df = df[required_cols].copy()
    
    # --- 2. 汇总表 ---
    summary_rows = []
    total_cust = len(df)
    
    # Pre-calculate stats for "Old" grades (原档位)
    # Note: '原档位_Num' should be available
    old_stats = {}
    if '原档位_Num' in df.columns:
        for g in range(1, 31):
            subset = df[df['原档位_Num'] == g]
            if not subset.empty:
                old_stats[g] = {
                    'min': subset['总分'].min(),
                    'max': subset['总分'].max(),
                    'count': len(subset),
                    'pct': len(subset) / total_cust
                }
            else:
                old_stats[g] = {'min': 0, 'max': 0, 'count': 0, 'pct': 0}
    
    # Iterate for New Grades (30 down to 1)
    for g in range(30, 0, -1):
        g_cn = num_to_cn(g)
        subset = df[df['新档位_Num'] == g]
        
        count = len(subset)
        pct = count / total_cust if total_cust > 0 else 0
        min_score = subset['总分'].min() if count > 0 else 0
        max_score = subset['总分'].max() if count > 0 else 0
        
        # Upgrade/Downgrade logic
        # Upgrade: New > Old. Since we are looking at specific New Grade g,
        # we want to know how many people in this New Grade g came from a Lower Old Grade.
        # Wait, the requirement asks for "升档人数" (Upgrade Count) per "客户类别" (Grade).
        # This usually means: For customers currently in Grade X (New), how many were upgraded to get here?
        # OR it could mean: For customers who were in Grade X (Old), how many upgraded?
        # Given the table structure "分档后_..." comes before "升档...", it implies the row context is the "New Grade".
        # Let's assume: Rows represent the New Grade buckets.
        
        # Customers in this new grade g
        # Upgraded to here: Old < g
        up_here = subset[subset['原档位_Num'] < g]
        n_up = len(up_here)
        p_up = n_up / count if count > 0 else 0
        
        # Downgraded to here: Old > g
        down_here = subset[subset['原档位_Num'] > g]
        n_down = len(down_here)
        p_down = n_down / count if count > 0 else 0
        
        # Pre-tiering stats for the SAME grade number
        # i.e. Statistics for Old Grade = g
        pre_s = old_stats.get(g, {'min': 0, 'max': 0, 'count': 0, 'pct': 0})
        
        summary_rows.append({
            '客户类别': g_cn,
            '分档线': min_score,
            '分档前_结果最小值': pre_s['min'],
            '分档前_结果最大值': pre_s['max'],
            '分档前_客户数': pre_s['count'],
            '分档前_实际占比': pre_s['pct'],
            '分档后_结果最小值': min_score,
            '分档后_结果最大值': max_score,
            '分档后_客户数': count,
            '分档后_实际占比': pct,
            '升档人数': n_up,
            '升档比例': p_up,
            '降档人数': n_down,
            '降档比例': p_down
        })
        
    summary_df = pd.DataFrame(summary_rows)
    
    # Format percentages
    pct_cols = ['分档前_实际占比', '分档后_实际占比', '升档比例', '降档比例']
    # We will keep them as floats for Excel to format, or string? 
    # Let's keep as float, user can format in Excel, or we can format as string.
    # The requirement example shows "9.10%", so string might be safer if we can't control Excel styles easily.
    for col in pct_cols:
        summary_df[col] = summary_df[col].apply(lambda x: f"{x:.2%}")
        
    # --- 3. 规则校验 ---
    # Use metrics if provided, otherwise re-calculate simple ones
    # If metrics is None, we should try to calculate them or set defaults
    if metrics is None:
        metrics = {}
        # Try to calc simple ones if possible, or just default to 0/False
        # For variance and change rate, we can calc them here if we want
        
        # Recalculate variance for reporting if missing
        total_variance = 0
        for g in range(1, 31):
            g_subset = df[df['新档位_Num'] == g]
            if len(g_subset) > 1:
                var = g_subset['卷烟购进金额指标值'].var()
                total_variance += var
        metrics['total_variance'] = total_variance
        
        # Recalculate change rate
        weighted_sum_old = (df['原档位_Num'] * df['卷烟购进金额指标值']).sum()
        weighted_sum_new = (df['新档位_Num'] * df['卷烟购进金额指标值']).sum()
        if weighted_sum_old != 0:
            change_rate = (weighted_sum_new - weighted_sum_old) / weighted_sum_old
        else:
            change_rate = 0
        metrics['change_rate'] = change_rate
        metrics['rule_d_pass'] = -0.05 <= change_rate <= 0.05
        
        # Calculate correlation for Rule E
        actual_counts = df['新档位_Num'].value_counts().sort_index()
        actual_vector = np.array([actual_counts.get(i, 0) for i in range(1, 31)])
        x_range = np.arange(1, 31)
        pdf_ideal = norm.pdf(x_range, loc=15, scale=7)
        if np.std(actual_vector) > 0 and np.std(pdf_ideal) > 0:
            corr = np.corrcoef(actual_vector, pdf_ideal)[0, 1]
        else:
            corr = 0
        metrics['corr'] = corr

    rules_data = []
    
    # We can reconstruct the rule checks from the df if metrics not fully provided or to be safe
    # But relying on metrics passed from optimize is better if available.
    
    # Re-evaluating rules to ensure accuracy for the report
    grade_counts = df['新档位_Num'].value_counts(normalize=True)
    min_pct = grade_counts.min() if not grade_counts.empty else 0
    
    upgrades = df[df['新档位_Num'] > df['原档位_Num']]
    downgrades = df[df['新档位_Num'] < df['原档位_Num']]
    n_up = len(upgrades)
    n_down = len(downgrades)
    
    def get_pct(start, end):
        c = ((df['新档位_Num'] >= start) & (df['新档位_Num'] <= end)).sum()
        return c / total_cust
        
    p26_30 = get_pct(26, 30)
    p21_25 = get_pct(21, 25)
    p16_20 = get_pct(16, 20)
    p11_15 = get_pct(11, 15)
    p1_10 = get_pct(1, 10)
    
    # Define Rules
    rule_defs = [
        ('大规则A(26-30档)', f'占比 {p26_30:.2%} (目标9%±0.1%)', 0.089 <= p26_30 <= 0.091),
        ('大规则B(21-25档)', f'占比 {p21_25:.2%} (目标18%±0.1%)', 0.179 <= p21_25 <= 0.181),
        ('大规则C(16-20档)', f'占比 {p16_20:.2%} (目标23%±0.1%)', 0.229 <= p16_20 <= 0.231),
        ('大规则D(11-15档)', f'占比 {p11_15:.2%} (目标23%±0.1%)', 0.229 <= p11_15 <= 0.231),
        ('大规则E(1-10档)', f'占比 {p1_10:.2%} (目标27%±0.1%)', 0.269 <= p1_10 <= 0.271),
        ('小规则A(强制)', f'最小档位人数 {df["新档位_Num"].value_counts().min()} (必须>0)', min_pct > 0),
        ('小规则A(优先)', f'最小档位占比 {min_pct:.2%} (建议>=1%)', min_pct >= 0.01),
        ('小规则B(强制)', f'升档{n_up} vs 降档{n_down} (必须 升>=降)', n_up >= n_down),
        ('小规则E(优先)', f'正态分布相关性 {metrics.get("corr", 0):.4f} (目标>0.8, 全局或区间正态)', metrics.get("corr", 0) > 0.8),
        ('小规则C(参考)', f'总方差 {metrics.get("total_variance", 0):.2f} (忽略)', True),
        ('小规则D(参考)', f'指标变化率 {metrics.get("change_rate", 0):.2%} (忽略)', True),
    ]
    
    for name, content, passed in rule_defs:
        rules_data.append({
            '规则': name,
            '内容': content,
            '是否满足': '是' if passed else '否'
        })
        
    rules_df = pd.DataFrame(rules_data)
    
    return detail_df, summary_df, rules_df

def generate_summary(df):
    """Generate summary dataframe for visualization (Keep existing for UI charts)."""
    total_cust = len(df)
    summary_rows = []
    
    for g in range(30, 0, -1):
        g_cn = num_to_cn(g)
        subset = df[df['新档位_Num'] == g]
        count = len(subset)
        pct = count / total_cust if total_cust > 0 else 0
        
        up = (subset['原档位_Num'] < g).sum()
        down = (subset['原档位_Num'] > g).sum()
        
        min_score = subset['总分'].min() if count > 0 else 0
        max_score = subset['总分'].max() if count > 0 else 0
        
        # Calculate Old Counts for this grade number
        pre_count = len(df[df['原档位_Num'] == g])
        
        # Calculate Rates (as percentage of the new grade count)
        # Avoid division by zero
        up_rate = up / count if count > 0 else 0
        down_rate = down / count if count > 0 else 0
        
        summary_rows.append({
            'Grade': g,
            'GradeName': g_cn,
            'Count': int(count),
            'PreCount': int(pre_count),
            'Percentage': pct,
            'Upgrades': int(up),
            'Downgrades': int(down),
            'UpgradeRate': float(up_rate),
            'DowngradeRate': float(down_rate),
            'MinScore': float(min_score),
            'MaxScore': float(max_score)
        })
        
    return pd.DataFrame(summary_rows)

def generate_district_summary(df):
    """
    Generate summary statistics grouped by District.
    Returns a list of dicts.
    """
    if '所属区县' not in df.columns:
        return []
        
    districts = df['所属区县'].unique()
    stats = []
    
    for district in districts:
        subset = df[df['所属区县'] == district]
        total = len(subset)
        if total == 0: continue
        
        # Upgrades: New > Old
        up = (subset['新档位_Num'] > subset['原档位_Num']).sum()
        # Downgrades: New < Old
        down = (subset['新档位_Num'] < subset['原档位_Num']).sum()
        
        stats.append({
            'District': str(district),
            'Total': int(total),
            'Upgrades': int(up),
            'Downgrades': int(down),
            'UpgradeRate': float(up / total),
            'DowngradeRate': float(down / total)
        })
    
    # Sort by District name
    stats.sort(key=lambda x: x['District'])
    return stats

def generate_district_grade_detail(df):
    """
    Generate detailed stats: District -> Grade -> {Up, Down, Count}
    """
    if '所属区县' not in df.columns:
        return {}
        
    districts = df['所属区县'].unique()
    detail = {}
    
    for district in districts:
        district_data = []
        d_subset = df[df['所属区县'] == district]
        
        # Iterate grades 1-30
        for g in range(1, 31):
            g_subset = d_subset[d_subset['新档位_Num'] == g]
            count = len(g_subset)
            
            up = (g_subset['原档位_Num'] < g).sum()
            down = (g_subset['原档位_Num'] > g).sum()
            
            district_data.append({
                'Grade': g,
                'Count': int(count),
                'Upgrades': int(up),
                'Downgrades': int(down)
            })
            
        # Sort by Grade
        district_data.sort(key=lambda x: x['Grade'])
        detail[str(district)] = district_data
        
    return detail
