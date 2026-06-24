from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from mpxccp.models.shared import CryptoProduct, EvidenceImage, QuantitativeAssessment


class SharedRepository:
    def get_quant(
        self,
        session: Session,
        project_id: int,
        unit_type: str,
        related_id: int,
    ) -> QuantitativeAssessment | None:
        return session.scalar(
            select(QuantitativeAssessment).where(
                QuantitativeAssessment.project_id == project_id,
                QuantitativeAssessment.unit_type == unit_type,
                QuantitativeAssessment.related_id == related_id,
            )
        )

    def list_quant_by_project(
        self,
        session: Session,
        project_id: int,
    ) -> list[QuantitativeAssessment]:
        return list(
            session.scalars(
                select(QuantitativeAssessment)
                .where(QuantitativeAssessment.project_id == project_id)
                .order_by(QuantitativeAssessment.unit_type, QuantitativeAssessment.related_id)
            )
        )

    def add_quant(
        self,
        session: Session,
        *,
        project_id: int,
        unit_type: str,
        related_id: int,
    ) -> QuantitativeAssessment:
        record = QuantitativeAssessment(
            project_id=project_id,
            unit_type=unit_type,
            related_id=related_id,
        )
        session.add(record)
        session.flush()
        return record

    def load_products(
        self,
        session: Session,
        project_id: int,
        unit_type: str,
        related_id: int,
    ) -> list[CryptoProduct]:
        return list(
            session.scalars(
                select(CryptoProduct)
                .where(
                    CryptoProduct.project_id == project_id,
                    CryptoProduct.unit_type == unit_type,
                    CryptoProduct.related_id == related_id,
                )
                .order_by(CryptoProduct.sort_order, CryptoProduct.id)
            )
        )

    def delete_products_for_related(
        self,
        session: Session,
        project_id: int,
        unit_type: str,
        related_id: int,
    ) -> None:
        session.execute(
            delete(CryptoProduct).where(
                CryptoProduct.project_id == project_id,
                CryptoProduct.unit_type == unit_type,
                CryptoProduct.related_id == related_id,
            )
        )

    def list_project_products(self, session: Session, project_id: int) -> list[CryptoProduct]:
        return list(
            session.scalars(
                select(CryptoProduct)
                .where(CryptoProduct.project_id == project_id)
                .order_by(CryptoProduct.id)
            )
        )

    def get_product(self, session: Session, product_id: int) -> CryptoProduct | None:
        return session.get(CryptoProduct, product_id)

    def add_product(
        self,
        session: Session,
        *,
        project_id: int,
        unit_type: str,
        related_id: int,
        product_name: str,
        product_model: str = "",
        certificate_no: str = "",
        product_level: str = "",
        vendor: str = "",
        usage: str = "",
        sort_order: int = 0,
    ) -> CryptoProduct:
        product = CryptoProduct(
            project_id=project_id,
            unit_type=unit_type,
            related_id=related_id,
            product_name=product_name,
            product_model=product_model,
            certificate_no=certificate_no,
            product_level=product_level,
            vendor=vendor,
            usage=usage,
            sort_order=sort_order,
        )
        session.add(product)
        session.flush()
        return product

    def sync_same_certificate(self, session: Session, source: CryptoProduct) -> int:
        if not source.certificate_no.strip():
            return 0
        targets = list(
            session.scalars(
                select(CryptoProduct).where(
                    CryptoProduct.project_id == source.project_id,
                    CryptoProduct.certificate_no == source.certificate_no,
                    CryptoProduct.id != source.id,
                )
            )
        )
        changed = 0
        for target in targets:
            if target.unit_type == source.unit_type and target.related_id == source.related_id:
                continue
            target_values = (
                target.product_name,
                target.product_model,
                target.product_level,
                target.vendor,
                target.usage,
            )
            source_values = (
                source.product_name,
                source.product_model,
                source.product_level,
                source.vendor,
                source.usage,
            )
            if target_values == source_values:
                continue
            target.product_name = source.product_name
            target.product_model = source.product_model
            target.product_level = source.product_level
            target.vendor = source.vendor
            target.usage = source.usage
            changed += 1
        return changed

    def list_evidence(
        self,
        session: Session,
        project_id: int,
        unit_type: str,
        related_id: int,
    ) -> list[EvidenceImage]:
        return list(
            session.scalars(
                select(EvidenceImage)
                .where(
                    EvidenceImage.project_id == project_id,
                    EvidenceImage.unit_type == unit_type,
                    EvidenceImage.related_id == related_id,
                )
                .order_by(EvidenceImage.sort_order, EvidenceImage.id)
            )
        )

    def list_evidence_by_ids(
        self,
        session: Session,
        project_id: int,
        unit_type: str,
        related_id: int,
        record_ids: Iterable[int],
    ) -> list[EvidenceImage]:
        ids = list(record_ids)
        if not ids:
            return []
        return list(
            session.scalars(
                select(EvidenceImage)
                .where(
                    EvidenceImage.project_id == project_id,
                    EvidenceImage.unit_type == unit_type,
                    EvidenceImage.related_id == related_id,
                    EvidenceImage.id.in_(ids),
                )
                .order_by(EvidenceImage.sort_order, EvidenceImage.id)
            )
        )

    def add_evidence(
        self,
        session: Session,
        *,
        project_id: int,
        unit_type: str,
        related_id: int,
        file_name: str,
        original_name: str,
        caption: str,
        checksum: str,
        sort_order: int,
    ) -> EvidenceImage:
        record = EvidenceImage(
            project_id=project_id,
            unit_type=unit_type,
            related_id=related_id,
            file_name=file_name,
            original_name=original_name,
            caption=caption,
            checksum=checksum,
            sort_order=sort_order,
        )
        session.add(record)
        session.flush()
        return record