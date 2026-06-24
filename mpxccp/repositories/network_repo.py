from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mpxccp.models.basic_info import Subsystem
from mpxccp.models.technical_network import (
    NetworkAuthDetail,
    NetworkBoundaryIntegrityDetail,
    NetworkChannel,
    NetworkConfidentialityDetail,
    NetworkIntegrityDetail,
    NetworkSubsystem,
)


class NetworkRepository:
    def list_subsystems(self, session: Session, project_id: int) -> list[NetworkSubsystem]:
        return list(
            session.scalars(
                select(NetworkSubsystem)
                .where(NetworkSubsystem.project_id == project_id)
                .order_by(NetworkSubsystem.sort_order, NetworkSubsystem.id)
            )
        )

    def get_subsystem(self, session: Session, subsystem_id: int) -> NetworkSubsystem | None:
        return session.get(NetworkSubsystem, subsystem_id)

    def sync_from_basic_subsystems(
        self,
        session: Session,
        project_id: int,
    ) -> list[NetworkSubsystem]:
        basic_subsystems = list(
            session.scalars(
                select(Subsystem)
                .where(
                    Subsystem.project_id == project_id,
                    Subsystem.is_enabled.is_(True),
                )
                .order_by(Subsystem.sort_order, Subsystem.id)
            )
        )
        by_basic_id = {
            item.basic_subsystem_id: item
            for item in session.scalars(
                select(NetworkSubsystem).where(NetworkSubsystem.project_id == project_id)
            )
            if item.basic_subsystem_id is not None
        }
        by_name = {
            item.name: item
            for item in session.scalars(
                select(NetworkSubsystem).where(NetworkSubsystem.project_id == project_id)
            )
        }
        synced: list[NetworkSubsystem] = []
        for basic in basic_subsystems:
            network = by_basic_id.get(basic.id) or by_name.get(basic.name)
            if network is None:
                network = NetworkSubsystem(
                    project_id=project_id,
                    name=basic.name,
                    description=basic.description,
                )
                session.add(network)
            network.basic_subsystem_id = basic.id
            network.name = basic.name
            network.sort_order = basic.sort_order
            synced.append(network)
        session.flush()
        return synced

    def list_channels(self, session: Session, network_subsystem_id: int) -> list[NetworkChannel]:
        return list(
            session.scalars(
                select(NetworkChannel)
                .where(NetworkChannel.network_subsystem_id == network_subsystem_id)
                .order_by(NetworkChannel.sort_order, NetworkChannel.id)
            )
        )

    def get_channel(self, session: Session, channel_id: int) -> NetworkChannel | None:
        return session.get(NetworkChannel, channel_id)

    def create_channel(
        self,
        session: Session,
        network_subsystem_id: int,
        name: str,
    ) -> NetworkChannel:
        subsystem = self.get_subsystem(session, network_subsystem_id)
        if subsystem is None:
            raise ValueError(f"network subsystem not found: {network_subsystem_id}")
        channel = NetworkChannel(
            project_id=subsystem.project_id,
            network_subsystem_id=subsystem.id,
            name=name,
            sort_order=self._next_channel_sort_order(session, subsystem.id),
        )
        session.add(channel)
        session.flush()
        session.add_all(
            [
                NetworkAuthDetail(
                    project_id=subsystem.project_id,
                    network_channel_id=channel.id,
                    sort_order=0,
                ),
                NetworkIntegrityDetail(
                    project_id=subsystem.project_id,
                    network_channel_id=channel.id,
                    sort_order=1,
                ),
                NetworkConfidentialityDetail(
                    project_id=subsystem.project_id,
                    network_channel_id=channel.id,
                    sort_order=2,
                ),
                NetworkBoundaryIntegrityDetail(
                    project_id=subsystem.project_id,
                    network_channel_id=channel.id,
                    sort_order=3,
                ),
            ]
        )
        session.flush()
        return channel

    def load_auth_detail(self, session: Session, channel_id: int) -> NetworkAuthDetail | None:
        return session.scalar(
            select(NetworkAuthDetail).where(NetworkAuthDetail.network_channel_id == channel_id)
        )

    def load_integrity_detail(
        self,
        session: Session,
        channel_id: int,
    ) -> NetworkIntegrityDetail | None:
        return session.scalar(
            select(NetworkIntegrityDetail).where(
                NetworkIntegrityDetail.network_channel_id == channel_id
            )
        )

    def load_confidentiality_detail(
        self,
        session: Session,
        channel_id: int,
    ) -> NetworkConfidentialityDetail | None:
        return session.scalar(
            select(NetworkConfidentialityDetail).where(
                NetworkConfidentialityDetail.network_channel_id == channel_id
            )
        )

    def load_boundary_detail(
        self,
        session: Session,
        channel_id: int,
    ) -> NetworkBoundaryIntegrityDetail | None:
        return session.scalar(
            select(NetworkBoundaryIntegrityDetail).where(
                NetworkBoundaryIntegrityDetail.network_channel_id == channel_id
            )
        )

    def _next_channel_sort_order(self, session: Session, network_subsystem_id: int) -> int:
        current_max = session.scalar(
            select(func.max(NetworkChannel.sort_order)).where(
                NetworkChannel.network_subsystem_id == network_subsystem_id
            )
        )
        return int(current_max or 0) + 1
