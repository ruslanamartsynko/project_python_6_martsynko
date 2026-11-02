from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass
class DataStorage:
    """Структура даних з двома масивами результатів."""

    experimental: list[float] = field(default_factory=list)
    calculated: list[float] = field(default_factory=list)

    def clear(self) -> None:
        self.experimental.clear()
        self.calculated.clear()

    def load_from_file(self, file_path: str | Path) -> None:
        path = Path(file_path)
        if path.suffix.lower() == ".csv":
            frame = pd.read_csv(path)
        elif path.suffix.lower() in {".xlsx", ".xls"}:
            frame = pd.read_excel(path)
        else:
            raise ValueError("Підтримуються лише CSV, XLSX або XLS файли")

        frame = self._normalize_columns(frame)
        self.experimental = self._clean_numbers(frame["experimental"])
        self.calculated = self._clean_numbers(frame["calculated"])

    def set_from_lists(self, experimental: Iterable[float], calculated: Iterable[float]) -> None:
        self.experimental = self._clean_numbers(experimental)
        self.calculated = self._clean_numbers(calculated)

    def add_pair(self, experimental_value: float, calculated_value: float) -> None:
        self.experimental.append(float(experimental_value))
        self.calculated.append(float(calculated_value))

    def add_many_pairs(self, experimental_values: Iterable[float], calculated_values: Iterable[float]) -> None:
        exp = self._clean_numbers(experimental_values)
        calc = self._clean_numbers(calculated_values)
        if len(exp) != len(calc):
            raise ValueError("Кількість елементів у двох масивах має бути однаковою")
        self.experimental.extend(exp)
        self.calculated.extend(calc)

    def add_normal_random_data(
        self,
        n: int,
        exp_mean: float,
        exp_std: float,
        calc_mean: float,
        calc_std: float,
    ) -> None:
        if n <= 0:
            raise ValueError("n має бути додатним")
        if exp_std <= 0 or calc_std <= 0:
            raise ValueError("Стандартне відхилення має бути додатним")

        experimental_values = np.random.normal(exp_mean, exp_std, n)
        calculated_values = np.random.normal(calc_mean, calc_std, n)
        self.experimental.extend(map(float, experimental_values))
        self.calculated.extend(map(float, calculated_values))

    def to_dataframe(self) -> pd.DataFrame:
        max_len = max(len(self.experimental), len(self.calculated), 0)
        exp = self.experimental + [np.nan] * (max_len - len(self.experimental))
        calc = self.calculated + [np.nan] * (max_len - len(self.calculated))
        return pd.DataFrame({"experimental": exp, "calculated": calc})

    def save_to_csv(self, file_path: str | Path) -> None:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        self.to_dataframe().to_csv(file_path, index=False)

    def statistics(self) -> dict[str, dict[str, float | int | None]]:
        return {
            "experimental": self._statistics_for(self.experimental),
            "calculated": self._statistics_for(self.calculated),
        }

    @staticmethod
    def _statistics_for(values: list[float]) -> dict[str, float | int | None]:
        if not values:
            return {
                "count": 0,
                "mean": None,
                "median": None,
                "variance": None,
                "std": None,
                "min": None,
                "max": None,
            }
        array = np.array(values, dtype=float)
        return {
            "count": int(array.size),
            "mean": float(np.mean(array)),
            "median": float(np.median(array)),
            "variance": float(np.var(array, ddof=1)) if array.size > 1 else 0.0,
            "std": float(np.std(array, ddof=1)) if array.size > 1 else 0.0,
            "min": float(np.min(array)),
            "max": float(np.max(array)),
        }

    @staticmethod
    def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.shape[1] < 2:
            raise ValueError("Файл має містити мінімум два стовпці")

        lower_columns = {str(col).strip().lower(): col for col in frame.columns}
        if "experimental" in lower_columns and "calculated" in lower_columns:
            return frame.rename(
                columns={
                    lower_columns["experimental"]: "experimental",
                    lower_columns["calculated"]: "calculated",
                }
            )[["experimental", "calculated"]]

        result = frame.iloc[:, :2].copy()
        result.columns = ["experimental", "calculated"]
        return result

    @staticmethod
    def _clean_numbers(values: Iterable[float]) -> list[float]:
        result: list[float] = []
        for value in values:
            if pd.isna(value):
                continue
            text = str(value).strip().replace(",", ".")
            if text == "":
                continue
            result.append(float(text))
        return result
