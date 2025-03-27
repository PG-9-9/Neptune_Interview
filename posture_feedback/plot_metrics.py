import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set a consistent Seaborn plot style
sns.set(style="whitegrid")

# Define directories for metrics and plots
LOG_DIR = "metrics"
PLOT_DIR = os.path.join(LOG_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)


def load_all_logs():
    """
    Load all CSV log files from the metrics directory and assign a phase label 
    based on file naming convention.

    Returns:
        pd.DataFrame: Concatenated DataFrame with a 'phase' column added.
    """
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
    """
    Assign ground truth based on original interview spec logic:
    Elbow is above shoulder ⇒ raised arm.

    Args:
        df (pd.DataFrame): Input metrics DataFrame.

    Returns:
        pd.DataFrame: DataFrame with a new 'ground_truth' column.
    """
    df['ground_truth'] = df['elbow_y'] < df['shoulder_y']
    return df


def compute_accuracy(df):
    """
    Compute accuracy for each approach phase by comparing prediction (`smoothed_status`)
    to the derived `ground_truth`.

    Args:
        df (pd.DataFrame): Full metrics DataFrame.

    Returns:
        pd.DataFrame: Summary table with accuracy values by phase.
    """
    summary = []
    for phase in df['phase'].unique():
        sub = df[df['phase'] == phase].copy()
        acc = (sub['ground_truth'] == sub['smoothed_status']).sum() / len(sub)
        summary.append({"phase": phase, "accuracy": acc})
    return pd.DataFrame(summary)


def plot_accuracy_bar(summary_df):
    """
    Plot a bar chart comparing accuracy of each model enhancement phase 
    against spec-based ground truth.

    Args:
        summary_df (pd.DataFrame): Accuracy table with 'phase' and 'accuracy' columns.
    """
    plt.figure(figsize=(8, 5))
    order = ["baseline", "angle", "smoothing", "shoulder", "final", "session"]
    summary_df = summary_df.set_index("phase").reindex(order).reset_index()

    sns.barplot(data=summary_df, x='phase', y='accuracy', palette="viridis")
    plt.title("Accuracy vs Spec-Based Ground Truth by Phase")
    plt.ylabel("Accuracy")
    plt.ylim(0, 1)
    plt.xlabel("Approach Phase")

    # Add legend explanation as footnote-style annotation
    legend_text = (
        "Ground Truth: elbow_y < shoulder_y (per original interview spec)\n"
        "baseline       : raw detection (no angle, smoothing, or suppression)\n"
        "angle          : + elbow angle filtering for noise reduction\n"
        "smoothing      : + 5-frame temporal buffer for stability\n"
        "shoulder       : + suppression of false raises due to shoulder elevation\n"
        "final/session  : all enhancements + contextual feedback"
    )
    plt.gcf().text(0.01, -0.35, legend_text, fontsize=9, ha='left', va='top', family='monospace')

    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "accuracy_vs_spec_groundtruth.png"), bbox_inches='tight')
    plt.close()


def main():
    """
    Driver function:
    - Loads logs
    - Defines ground truth
    - Computes accuracy for each phase
    - Generates and saves a comparison bar plot
    """
    df_all = load_all_logs()
    if df_all.empty:
        print("No logs found.")
        return

    df_all = define_ground_truth_from_spec(df_all)
    summary_df = compute_accuracy(df_all)
    plot_accuracy_bar(summary_df)

    print(f"✅ Updated plot saved at: {PLOT_DIR}/accuracy_vs_spec_groundtruth.png")


if __name__ == "__main__":
    main()
