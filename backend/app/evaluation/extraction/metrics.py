from dataclasses import dataclass

@dataclass
class MetricCount:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0.0

    @property
    def f1(self) -> float:
        p = self.precision
        r = self.recall
        return 2 * (p * r) / (p + r) if (p + r) > 0 else 0.0

    def add(self, tp: int = 0, fp: int = 0, fn: int = 0):
        self.tp += tp
        self.fp += fp
        self.fn += fn

def calculate_accuracy(tp: int, total_count: int) -> float:
    return tp / total_count if total_count > 0 else 0.0
