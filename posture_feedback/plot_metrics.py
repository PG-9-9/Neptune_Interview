import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

sns.set(style="whitegrid")

LOG_DIR = "metrics"
PLOT_DIR = "metrics/plots"
os.makedirs(PLOT_DIR, exist_ok=True)

def load_all_logs():
    dfs = []
    for fname in os.listdir(LOG_DIR):
        if fname.endswith(".csv") and "_log_" in fname:
            df = pd.read_csv(os.path.join(LOG_DIR, fname))
            for phase_key in ["baseline", "angle", "smoothing", "shoulder", "final", "session"]:
                if fname.startswith(phase_key):
                    df['phase'] = phase_key
                    break
            else:
                df['phase'] = "unknown"
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

def define_ground_truth_from_spec(df):
    df['ground_truth'] = df['elbow_y'] < df['shoulder_y']  # original problem logic
    return df

def compute_accuracy(df):
    summary = []
    for phase in df['phase'].unique():
        sub = df[df['phase'] == phase].copy()
        acc = (sub['ground_truth'] == sub['smoothed_status']).sum() / len(sub)
        summary.append({"phase": phase, "accuracy": acc})
    return pd.DataFrame(summary)

def plot_accuracy_bar(summary_df):
    plt.figure(figsize=(8, 5))
    order = ["baseline", "angle", "smoothing", "shoulder", "final", "session"]
    summary_df = summary_df.set_index("phase").reindex(order).reset_index()
    sns.barplot(data=summary_df, x='phase', y='accuracy', palette="viridis")
    plt.title("Accuracy vs Spec-Based Ground Truth by Phase")
    plt.ylabel("Accuracy")
    plt.ylim(0, 1)
    plt.xlabel("Approach Phase")

    legend_text = (
        "Ground Truth: elbow_y < shoulder_y (per original interview spec)\n"
        "baseline: raw detection\n"
        "angle: + elbow angle filtering\n"
        "smoothing: + 5-frame buffer\n"
        "shoulder: + shoulder suppression\n"
        "final/session: all enhancements"
    )
    plt.gcf().text(0.01, -0.35, legend_text, fontsize=9, ha='left', va='top', family='monospace')
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "accuracy_vs_spec_groundtruth.png"), bbox_inches='tight')
    plt.close()

def main():
    df_all = load_all_logs()
    if df_all.empty:
        print("No logs found.")
        return

    df_all = define_ground_truth_from_spec(df_all)
    summary_df = compute_accuracy(df_all)
    plot_accuracy_bar(summary_df)
    print(f"Updated plot saved at: {PLOT_DIR}/accuracy_vs_spec_groundtruth.png")

if __name__ == "__main__":
    main()
