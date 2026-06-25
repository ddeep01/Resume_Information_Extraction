from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent

SUMMARY_CSV = (
    ROOT
    / "results"
    / "summary_metrics.csv"
)

PLOTS_DIR = ROOT / "plots"

PLOTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def create_bar_plot(
    df,
    metric,
    title,
    ylabel,
    filename
):

    plt.figure(figsize=(8, 5))

    bars = plt.bar(
        df["tool"],
        df[metric]
    )

    plt.title(title)

    plt.ylabel(ylabel)

    plt.xlabel("PDF Extraction Tool")

    plt.grid(
        axis="y",
        linestyle="--",
        alpha=0.5
    )

    for bar in bars:

        value = bar.get_height()

        plt.text(
            bar.get_x() +
            bar.get_width()/2,
            value,
            f"{value:.4f}",
            ha="center",
            va="bottom"
        )

    plt.tight_layout()

    plt.savefig(
        PLOTS_DIR / filename,
        dpi=300
    )

    plt.close()


def create_ranking_plot(df):

    ranking = (
        df.sort_values(
            by=["f1", "bleu"],
            ascending=False
        )
        .reset_index(drop=True)
    )

    ranking["rank"] = (
        ranking.index + 1
    )

    plt.figure(
        figsize=(8, 5)
    )

    bars = plt.bar(
        ranking["tool"],
        ranking["rank"]
    )

    plt.title(
        "Overall Tool Ranking"
    )

    plt.ylabel(
        "Rank (Lower is Better)"
    )

    plt.xlabel(
        "Tool"
    )

    plt.gca().invert_yaxis()

    for bar, rank in zip(
        bars,
        ranking["rank"]
    ):

        plt.text(
            bar.get_x() +
            bar.get_width()/2,
            rank,
            str(rank),
            ha="center",
            va="bottom"
        )

    plt.tight_layout()

    plt.savefig(
        PLOTS_DIR /
        "overall_ranking.png",
        dpi=300
    )

    plt.close()


def main():

    df = pd.read_csv(
        SUMMARY_CSV
    )

    create_bar_plot(
        df,
        metric="f1",
        title="Average F1 Score Comparison",
        ylabel="F1 Score",
        filename="f1_comparison.png"
    )

    create_bar_plot(
        df,
        metric="cer",
        title="Average Character Error Rate",
        ylabel="CER",
        filename="cer_comparison.png"
    )

    create_bar_plot(
        df,
        metric="bleu",
        title="Average BLEU-4 Score",
        ylabel="BLEU",
        filename="bleu_comparison.png"
    )

    create_bar_plot(
        df,
        metric="ned",
        title="Average Normalized Edit Distance",
        ylabel="NED",
        filename="ned_comparison.png"
    )

    create_ranking_plot(df)

    print(
        "\nGraphs Generated Successfully"
    )

    print(
        f"\nSaved to: {PLOTS_DIR}"
    )


if __name__ == "__main__":
    main()