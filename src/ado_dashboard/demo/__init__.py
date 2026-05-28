"""Demo mode package — fictional fixture data for screenshots.

Import :func:`get_demo_ado_client`, :func:`get_demo_triage_client`, and
:func:`get_demo_session_client` to obtain async-compatible clients that return
Tolkien-themed fixture data without touching any real ADO infrastructure.
"""

from ado_dashboard.demo.clients import (
    DemoAdoClient,
    DemoSessionClient,
    DemoTriageClient,
)

__all__ = ["DemoAdoClient", "DemoSessionClient", "DemoTriageClient"]
