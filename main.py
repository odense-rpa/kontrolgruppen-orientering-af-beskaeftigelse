import asyncio
import logging
import sys

from automation_server_client import (
    AutomationServer,
    Workqueue,
    WorkItemError,
    Credential,
    WorkItemStatus,
)
from momentum_client.manager import MomentumClientManager
from odk_tools.tracking import Tracker
from sbsys.manager import SbsysClientManager

tracker: Tracker
momentum: MomentumClientManager
sbsys: SbsysClientManager
proces_navn = "Kontrolgruppen - Orientering af beskæftigelse"


async def populate_queue(workqueue: Workqueue):
    logger = logging.getLogger(__name__)

    logger.info("Populating queue...")

    async with sbsys:
        skabeloner = await sbsys.sagsskabeloner.hent_sagsskabeloner()
        skabelon = next((s for s in skabeloner if s["SagsTitel"].lower() == "Adresse - Kontrolgruppen".lower()), None)
        
        test = await sbsys.sager.søg_sager(
            {
                "Titel": "Adresse - Kontrolgruppen"
            }
        )
    print("hej")
    


async def process_workqueue(workqueue: Workqueue):
    logger = logging.getLogger(__name__)

    logger.info("Processing workqueue!")

    for item in workqueue:
        with item:
            data = item.data  # Item data deserialized from json as dict

            try:
                # Process the item here
                pass
            except WorkItemError as e:
                logger.error(f"Error processing item: {data}. Error: {e}")
                item.fail(str(e))


if __name__ == "__main__":
    ats = AutomationServer.from_environment()

    workqueue = ats.workqueue()

    # Initialize external systems for automation here..
    tracking_credential = Credential.get_credential("Odense SQL Server")
    tracker = Tracker(
        username=tracking_credential.username, password=tracking_credential.password
    )
    momentum_credential = Credential.get_credential("Momentum - produktion")
    momentum = MomentumClientManager(
        base_url=momentum_credential.data["base_url"],
        client_id=momentum_credential.username,
        client_secret=momentum_credential.password,
        api_key=momentum_credential.data["api_key"],
        resource=momentum_credential.data["resource"],
    )
    sbsys_credential = Credential.get_credential("SBSYS - produktion")
    sbsys = SbsysClientManager(
        sbsys_credential.data["base_url"],
        sbsys_credential.data["token_url"],
        sbsys_credential.data["client_id"],
        sbsys_credential.data["client_secret"],
        sbsys_credential.username,
        sbsys_credential.password,
    )

    # Queue management
    if "--queue" in sys.argv:
        workqueue.clear_workqueue(WorkItemStatus.NEW)
        asyncio.run(populate_queue(workqueue))
        exit(0)

    # Process workqueue
    asyncio.run(process_workqueue(workqueue))
