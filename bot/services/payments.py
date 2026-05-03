from __future__ import annotations

from dataclasses import dataclass

import aiohttp

from bot.config import Settings


@dataclass(frozen=True)
class CryptoInvoice:
    invoice_id: str
    pay_url: str
    status: str


class CryptoBotService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.cryptobot_token)

    async def create_invoice(self, amount: int, description: str, payload: str) -> CryptoInvoice:
        if not self.settings.cryptobot_token:
            raise RuntimeError("CRYPTOBOT_TOKEN is not configured")

        headers = {"Crypto-Pay-API-Token": self.settings.cryptobot_token}
        body = {
            "asset": "USDT",
            "amount": str(amount),
            "description": description[:1024],
            "payload": payload,
            "allow_comments": False,
            "allow_anonymous": False,
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(f"{self.settings.cryptobot_api_url}/createInvoice", json=body) as response:
                response.raise_for_status()
                data = await response.json()

        result = data["result"]
        return CryptoInvoice(
            invoice_id=str(result["invoice_id"]),
            pay_url=result["pay_url"],
            status=result["status"],
        )

    async def get_invoice_status(self, invoice_id: str) -> str:
        if not self.settings.cryptobot_token:
            raise RuntimeError("CRYPTOBOT_TOKEN is not configured")

        headers = {"Crypto-Pay-API-Token": self.settings.cryptobot_token}
        params = {"invoice_ids": invoice_id}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(f"{self.settings.cryptobot_api_url}/getInvoices", params=params) as response:
                response.raise_for_status()
                data = await response.json()

        items = data.get("result", {}).get("items", [])
        return items[0]["status"] if items else "not_found"
