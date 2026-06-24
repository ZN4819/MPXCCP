from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Engine

from mpxccp.models.shared import CryptoProduct
from mpxccp.repositories.session import readonly_session_scope, session_scope
from mpxccp.repositories.shared_repo import SharedRepository
from mpxccp.services.result import ServiceResult


@dataclass(frozen=True)
class ProductRecord:
    id: int
    project_id: int
    unit_type: str
    related_id: int
    product_name: str
    product_model: str
    certificate_no: str
    product_level: str
    vendor: str
    usage: str
    sort_order: int


class ProductService:
    def __init__(
        self,
        engine: Engine,
        shared_repo: SharedRepository | None = None,
    ) -> None:
        self.engine = engine
        self.shared_repo = shared_repo or SharedRepository()

    def load_products(
        self,
        project_id: int,
        unit_type: str,
        related_id: int,
    ) -> list[ProductRecord]:
        with readonly_session_scope(self.engine) as session:
            return [
                self._record_payload(item)
                for item in self.shared_repo.load_products(
                    session,
                    project_id,
                    unit_type,
                    related_id,
                )
            ]

    def save_products(
        self,
        project_id: int,
        unit_type: str,
        related_id: int,
        products: list[dict[str, Any]],
    ) -> ServiceResult:
        warnings: list[str] = []
        with session_scope(self.engine) as session:
            self.shared_repo.delete_products_for_related(session, project_id, unit_type, related_id)
            created: list[CryptoProduct] = []
            for sort_order, values in enumerate(products):
                cleaned = self._clean_product(values)
                if not cleaned["product_name"]:
                    warnings.append(f"missing_product_name:{sort_order}")
                    continue
                created.append(
                    self.shared_repo.add_product(
                        session,
                        project_id=project_id,
                        unit_type=unit_type,
                        related_id=related_id,
                        sort_order=sort_order,
                        **cleaned,
                    )
                )
            synced = sum(self.shared_repo.sync_same_certificate(session, item) for item in created)
            return ServiceResult(
                success=True,
                message="products saved",
                project_id=project_id,
                warnings=warnings,
                payload={"saved": len(created), "synced": synced},
            )

    def list_reusable_project_products(self, project_id: int) -> list[ProductRecord]:
        with readonly_session_scope(self.engine) as session:
            deduped: dict[tuple[str, str], CryptoProduct] = {}
            for product in self.shared_repo.list_project_products(session, project_id):
                deduped[self._dedupe_key(product)] = product
            return [self._record_payload(item) for item in deduped.values()]

    def sync_same_certificate(
        self,
        project_id: int,
        source_product: ProductRecord,
    ) -> ServiceResult:
        with session_scope(self.engine) as session:
            product = session.get(CryptoProduct, source_product.id)
            if product is None or product.project_id != project_id:
                return ServiceResult(
                    success=False,
                    message="product not found",
                    project_id=project_id,
                    warnings=["product_not_found"],
                )
            synced = self.shared_repo.sync_same_certificate(session, product)
            return ServiceResult(
                success=True,
                message="same certificate products synchronized",
                project_id=project_id,
                payload={"synced": synced},
            )

    def _clean_product(self, values: dict[str, Any]) -> dict[str, str]:
        return {
            "product_name": self._text(values.get("product_name", values.get("name", ""))),
            "product_model": self._text(values.get("product_model", values.get("model", ""))),
            "certificate_no": self._text(values.get("certificate_no", "")),
            "product_level": self._text(values.get("product_level", values.get("level", ""))),
            "vendor": self._text(values.get("vendor", "")),
            "usage": self._text(values.get("usage", "")),
        }

    def _text(self, value: Any) -> str:
        return "" if value is None else str(value).strip()

    def _dedupe_key(self, product: CryptoProduct) -> tuple[str, str]:
        certificate = product.certificate_no.strip()
        if certificate:
            return ("certificate", certificate)
        return ("name", product.product_name.strip())

    def _record_payload(self, product: CryptoProduct) -> ProductRecord:
        return ProductRecord(
            id=product.id,
            project_id=product.project_id,
            unit_type=product.unit_type,
            related_id=product.related_id,
            product_name=product.product_name,
            product_model=product.product_model,
            certificate_no=product.certificate_no,
            product_level=product.product_level or "",
            vendor=product.vendor,
            usage=product.usage,
            sort_order=product.sort_order,
        )