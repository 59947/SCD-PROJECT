
class StandardGradingStrategy:
    """
    Strategy Pattern:
    Calculates a final grade using the project's standard grading rubric.
    """

    CRITERIA = [
        "problem_definition",
        "methodology",
        "implementation",
        "presentation",
    ]

    def calculate(self, scores):
        total = sum(scores.get(criterion, 0) for criterion in self.CRITERIA)

        if total >= 90:
            grade = "A+"
        elif total >= 80:
            grade = "A"
        elif total >= 70:
            grade = "B"
        elif total >= 60:
            grade = "C"
        elif total >= 50:
            grade = "D"
        else:
            grade = "F"

        result = "Pass" if total >= 50 else "Fail"

        return {
            "total_score": total,
            "grade": grade,
            "result": result,
        }


class GradingCalculator:
    """Context that uses a grading strategy."""

    def __init__(self, strategy=None):
        self.strategy = strategy or StandardGradingStrategy()

    def calculate(self, scores):
        return self.strategy.calculate(scores)


grading_calculator = GradingCalculator()
