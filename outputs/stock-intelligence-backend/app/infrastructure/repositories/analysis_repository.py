import json

from sqlalchemy.orm import Session

from app.domain.entities import RecommendationResult
from app.infrastructure.models import AnalysisRunModel, ScoreBreakdownModel


class AnalysisRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save_result(self, stock_id: int, result: RecommendationResult) -> AnalysisRunModel:
        run = AnalysisRunModel(
            stock_id=stock_id,
            recommendation=result.recommendation,
            score=result.score,
            confidence=result.confidence,
        )
        self.db.add(run)
        self.db.flush()

        for item in result.breakdown:
            self.db.add(
                ScoreBreakdownModel(
                    analysis_run_id=run.id,
                    category=item.category,
                    weight=item.weight,
                    score=item.score,
                    weighted_score=item.weighted_score,
                    reasoning=item.reasoning,
                    input_values_json=json.dumps(item.input_values),
                )
            )

        self.db.commit()
        self.db.refresh(run)
        return run
