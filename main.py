import asyncio
import datetime
import logging
import sys

import httpx

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

    sagstitler = [
        "Adresse - Kontrolgruppen",
        "Kontrolsager fra Udbetaling Danmark - Kontrolgruppen",
        "Samliv - Kontrolgruppen",
        "Sort arbejde - Kontrolgruppen",
        "Udrejse - Kontrolgruppen",
        "Øvrige kontrolsager - Kontrolgruppen",
    ]

    async with sbsys:
        liste_af_skabelons_id = []
        skabeloner = await sbsys.sagsskabeloner.hent_sagsskabeloner()
        for sagstitel in sagstitler:
            skabelon = next(
                (s for s in skabeloner if s["SagsTitel"].lower() == sagstitel.lower()),
                None,
            )
            if skabelon:
                liste_af_skabelons_id.append(skabelon["Id"])
            else:
                logger.warning(f"Skabelon med titel '{sagstitel}' ikke fundet.")

        sager = await sbsys.sager.søg_sager(
            {
                "SagsStatusIds": [6],
                "SagsSkabeloner": liste_af_skabelons_id,
                "Limit": 3000,
            }
        )

        unikke_sager = {}
        for sag in sager:
            # Der er ikke altid CPR - nogle gange CVR - men for nu skipper vi dem bare
            cpr = sag.get("PrimaryPart", {}).get("CPRnummer")
            if cpr and cpr not in unikke_sager:
                unikke_sager[cpr] = sag

        sager = list(unikke_sager.values())
        for sag in sager:
            cpr = sag.get("PrimaryPart", {}).get("CPRnummer")
            if cpr:
                cpr = cpr.replace("-", "")
                workqueue.add_item(data={"cpr": cpr}, reference=cpr)


async def process_workqueue(workqueue: Workqueue):
    logger = logging.getLogger(__name__)

    logger.info("Processing workqueue!")

    for item in workqueue:
        with item:
            data = item.data  # Item data deserialized from json as dict

            try:
                borger = momentum.borgere.hent_borger(data["cpr"])
                borgers_målgrupper = momentum.borgere.hent_målgrupper(borger)
                if any(målgruppe["end"] is None for målgruppe in borgers_målgrupper):
                    borgers_markeringer = momentum.borgere.hent_markeringer(borger)
                    igangværende_kontrolsag = next(
                        (
                            m
                            for m in borgers_markeringer
                            if m["tag"]["title"].lower()
                            == "Igangværende kontrolgruppe sag".lower()
                            and m["end"] is None
                        ),
                        None,
                    )
                    if not igangværende_kontrolsag:
                        markering = momentum.borgere.opret_markering(
                            "Igangværende kontrolgruppe sag",
                            borger,
                            start_dato=datetime.datetime.now().date(),
                        )
                        if not markering:
                            raise WorkItemError(
                                "Kunne ikke oprette markering for borger i Momentum."
                            )
                        tracker.track_task(proces_navn)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(f"Borger med CPR {data['cpr']} ikke fundet i Momentum. Springer over.")
                else:
                    logger.error(f"HTTP error processing item. Error: {e}")
                    item.fail(str(e))
            except WorkItemError as e:
                logger.error(f"Error processing item. Error: {e}")
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
