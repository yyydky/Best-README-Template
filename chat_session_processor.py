#!/usr/bin/env python3
"""Clean and restructure chatbot chat-history logs into session-level conversations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


PLACEHOLDER_ANSWER = "[NO ANSWER CAPTURED]"


def clean_text(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    text = " ".join(text.split())
    return text if text else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean and restructure chatbot chat-history logs into session-level conversations."
    )
    parser.add_argument("input_path", type=Path, help="Path to input CSV or XLSX file.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Directory to write output files.",
    )
    parser.add_argument(
        "--sheet-name",
        type=str,
        default=None,
        help="Excel sheet name (only used for XLSX inputs).",
    )
    return parser.parse_args()


def load_input(path: Path, sheet_name: str | None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name=sheet_name or 0)
    return pd.read_csv(path)


def build_turns(df: pd.DataFrame) -> pd.DataFrame:
    df_sorted = df.sort_values(
        by=["session_id", "timestamp", "row_index"],
        ascending=[True, True, True],
        na_position="last",
    ).reset_index(drop=True)

    df_sorted["row_order"] = df_sorted.groupby("session_id").cumcount()

    user_turns = pd.DataFrame(
        {
            "session_id": df_sorted["session_id"],
            "turn_index": df_sorted["row_order"] * 2 + 1,
            "role": "user",
            "timestamp": df_sorted["timestamp"],
            "text": df_sorted["question_clean"],
        }
    )

    assistant_timestamp = df_sorted["timestamp"] + pd.to_timedelta(1, unit="ms")

    assistant_turns = pd.DataFrame(
        {
            "session_id": df_sorted["session_id"],
            "turn_index": df_sorted["row_order"] * 2 + 2,
            "role": "assistant",
            "timestamp": assistant_timestamp,
            "text": df_sorted["answer_filled"],
        }
    )

    turns = pd.concat([user_turns, assistant_turns], ignore_index=True)
    turns = turns.sort_values(
        by=["session_id", "turn_index"], ascending=[True, True]
    ).reset_index(drop=True)
    return turns


def build_sessions(df: pd.DataFrame, turns: pd.DataFrame) -> pd.DataFrame:
    df_sorted = df.sort_values(
        by=["session_id", "timestamp", "row_index"],
        ascending=[True, True, True],
        na_position="last",
    )

    session_groups = df_sorted.groupby("session_id", sort=False)

    start_time = session_groups["timestamp"].min()
    end_time = session_groups["timestamp"].max()

    duration_sec = (end_time - start_time).dt.total_seconds().fillna(0)

    row_count = session_groups.size()
    has_missing_answer = session_groups["answer_missing"].any()

    question_repeat = session_groups["question_clean"].apply(
        lambda series: (
            series.notna()
            & series.shift().notna()
            & series.eq(series.shift())
        ).sum()
    )

    answer_repeat = session_groups["answer_filled"].apply(
        lambda series: series.eq(series.shift()).sum()
    )

    def session_transcript_text(session_id: str) -> str:
        session_turns = turns[turns["session_id"] == session_id].sort_values(
            by="turn_index"
        )
        lines = [
            f"{row.role.title()}: {row.text}" for row in session_turns.itertuples()
        ]
        return "\n".join(lines) + ("\n" if lines else "")

    def session_transcript_json(session_id: str) -> str:
        session_turns = turns[turns["session_id"] == session_id].sort_values(
            by="turn_index"
        )
        payload = [
            {
                "role": row.role,
                "timestamp": None
                if pd.isna(row.timestamp)
                else row.timestamp.isoformat(),
                "text": row.text,
            }
            for row in session_turns.itertuples()
        ]
        return json.dumps(payload, ensure_ascii=False)

    sessions = pd.DataFrame(
        {
            "session_id": row_count.index,
            "start_time": start_time.values,
            "end_time": end_time.values,
            "duration_sec": duration_sec.values,
            "row_count": row_count.values,
            "turn_count": (row_count * 2).values,
            "has_missing_answer": has_missing_answer.values,
            "user_repeat_count": question_repeat.values,
            "bot_repeat_count": answer_repeat.values,
        }
    )

    sessions["transcript_text"] = sessions["session_id"].apply(
        session_transcript_text
    )
    sessions["transcript_turns_json"] = sessions["session_id"].apply(
        session_transcript_json
    )

    return sessions


def write_outputs(
    output_dir: Path,
    turns: pd.DataFrame,
    sessions: pd.DataFrame,
    sorted_rows: pd.DataFrame,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    turns_csv = output_dir / "turns.csv"
    turns_parquet = output_dir / "turns.parquet"
    sessions_csv = output_dir / "sessions.csv"
    sessions_parquet = output_dir / "sessions.parquet"
    sorted_rows_csv = output_dir / "sorted_rows.csv"

    turns.to_csv(turns_csv, index=False)
    sessions.to_csv(sessions_csv, index=False)
    sorted_rows.to_csv(sorted_rows_csv, index=False)

    turns.to_parquet(turns_parquet, index=False)
    sessions.to_parquet(sessions_parquet, index=False)


def print_summary(df: pd.DataFrame, sessions: pd.DataFrame) -> None:
    total_rows = len(df)
    missing_answers_pct = df["answer_missing"].mean() * 100 if total_rows else 0

    top_sessions = sessions.sort_values(
        by="row_count", ascending=False
    ).head(10)

    print("Summary")
    print("-------")
    print(f"Input rows: {total_rows}")
    print(f"Sessions: {len(sessions)}")
    print(f"% rows with missing answers: {missing_answers_pct:.2f}%")
    print("Top 10 sessions by row_count:")
    if top_sessions.empty:
        print("  (none)")
    else:
        for row in top_sessions.itertuples():
            print(f"  {row.session_id}: {row.row_count}")


def main() -> None:
    args = parse_args()
    df = load_input(args.input_path, args.sheet_name)

    required_columns = {"date", "session_id", "question", "answer"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        missing_list = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required columns: {missing_list}")

    df = df.reset_index(drop=False).rename(columns={"index": "row_index"})

    df["session_id"] = df["session_id"].astype("string").str.strip()
    df = df[df["session_id"].notna() & (df["session_id"] != "")].copy()

    df["timestamp"] = pd.to_datetime(df["date"], errors="coerce", utc=False)

    df["question_clean"] = df["question"].apply(clean_text)
    df["answer_clean"] = df["answer"].apply(clean_text)
    df["answer_missing"] = df["answer_clean"].isna()
    df["answer_filled"] = df["answer_clean"].fillna(PLACEHOLDER_ANSWER)

    sorted_rows = df.sort_values(
        by=["session_id", "timestamp", "row_index"],
        ascending=[True, True, True],
        na_position="last",
    )[
        [
            "session_id",
            "timestamp",
            "date",
            "question",
            "answer",
            "row_index",
        ]
    ].reset_index(drop=True)

    turns = build_turns(df)
    sessions = build_sessions(df, turns)

    write_outputs(args.output_dir, turns, sessions, sorted_rows)
    print_summary(df, sessions)


if __name__ == "__main__":
    main()
