import pytest
from datetime import date
from decimal import Decimal

from app.schemas.indicator_matrix import IndicatorMatrixResponse, MatrixCell


class TestIndicatorMatrixResponse:
    def test_matrix_cell_schema(self):
        cell = MatrixCell(value=Decimal("120.5"), status="normal", indicator_id="1")
        assert cell.value == Decimal("120.5")
        assert cell.status == "normal"
        assert cell.indicator_id == "1"

    def test_matrix_response_schema(self):
        data = {
            "dates": ["2026-06-01", "2026-06-02"],
            "indicator_keys": ["systolic_bp"],
            "indicator_names": {"systolic_bp": "收缩压"},
            "units": {"systolic_bp": "mmHg"},
            "cells": {
                "2026-06-01": {"systolic_bp": {"value": Decimal("120"), "status": "normal", "indicator_id": "1"}},
                "2026-06-02": {"systolic_bp": None},
            },
        }
        resp = IndicatorMatrixResponse(**data)
        assert len(resp.dates) == 2
        assert resp.cells["2026-06-02"]["systolic_bp"] is None
