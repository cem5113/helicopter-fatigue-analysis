# 1. Upload Dataset
from google.colab import files
import pandas as pd

uploaded = files.upload()
excel_file = next((fname for fname in uploaded if fname.endswith(".xlsx")), None)
if excel_file is None:
    raise FileNotFoundError(" No .xlsx file found in uploaded files.")

df = pd.read_excel(excel_file)
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
print("Dataset loaded.")

# 2. Helper
def format_p(p): return f"{p:.4f}" if p >= 0.001 else f"{p:.2e}"

# 3. PVT Pre vs Post
from scipy.stats import ttest_rel, wilcoxon, shapiro

shapiro_pre = shapiro(df["pvt_pre"].dropna())
shapiro_post = shapiro(df["pvt_post"].dropna())
if shapiro_pre.pvalue > 0.05 and shapiro_post.pvalue > 0.05:
    stat, p = ttest_rel(df["pvt_pre"], df["pvt_post"], nan_policy='omit')
    print("Paired t-test used.")
else:
    stat, p = wilcoxon(df["pvt_pre"], df["pvt_post"])
    print("Wilcoxon test used.")
print(f"PVT_pre vs post: p = {format_p(p)}")

# 4. Subjective Fatigue Tests
print("KSS_pre vs KSS_post:", format_p(ttest_rel(df["kss_pre"], df["kss_post"], nan_policy='omit').pvalue))
print("SP_pre  vs SP_post:", format_p(ttest_rel(df["sp_pre"], df["sp_post"], nan_policy='omit').pvalue))

# 5. Correlations
from scipy.stats import pearsonr
r1 = pearsonr(df["pvt_post"], df["kss_post"])[0]
r2 = pearsonr(df["pvt_post"], df["sp_post"])[0]
r3 = pearsonr(df["pvt_post"], df["pvt_avr"])[0]
print(f"PVT_post vs KSS_post: r = {r1:.3f}")
print(f"PVT_post vs SP_post:  r = {r2:.3f}")
print(f"PVT_post vs PVT_avr:  r = {r3:.3f}")

# 6. Regression Model
import statsmodels.api as sm
X = df[["pvt_pre", "pvt_avr", "kss_post", "sp_post", "flight_hours"]].copy()
y = df["pvt_post"]
X = sm.add_constant(X)
model = sm.OLS(y, X, missing='drop').fit()
print(model.summary())

# 7. VIF Analysis
from statsmodels.stats.outliers_influence import variance_inflation_factor
vif_df = pd.DataFrame()
vif_df["Variable"] = X.columns
vif_df["VIF"] = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]
print("\n🔍 VIF (Multicollinearity Check):")
print(vif_df)

# 8. Stepwise Regression
def forward_selection(data, target, threshold_in=0.05):
    import warnings; warnings.simplefilter("ignore")
    initial_features = []
    best_features = list(initial_features)
    while True:
        remaining = list(set(data.columns) - set(best_features))
        new_pval = pd.Series(index=remaining, dtype=float)
        for col in remaining:
            model = sm.OLS(target, sm.add_constant(data[best_features + [col]])).fit()
            new_pval[col] = model.pvalues[col]
        min_p = new_pval.min()
        if min_p < threshold_in:
            best_features.append(new_pval.idxmin())
        else:
            break
    return best_features

selected = forward_selection(X.drop(columns="const"), y)
print(f"\n Selected features via forward selection: {selected}")
